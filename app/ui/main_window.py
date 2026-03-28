from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.models import ReconciliationResult
from app.services.exporter import export_system_rows
from app.services.history_store import HistoryStore
from app.services.reconciliation import ReconciliationService
from app.services.utils import format_vnd, safe_name
from app.ui.table_models import ActionButtonDelegate, TransactionsFilterProxyModel, TransactionsTableModel
from app.ui.widgets import FrozenTableView, LoadingOverlay


@dataclass
class GridWidgets:
    title: QLabel
    count: QLabel
    search: QLineEdit
    columns: QComboBox
    table: FrozenTableView
    container: QWidget


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, system_path: str, bank_path: str) -> None:
        super().__init__()
        self.system_path = system_path
        self.bank_path = bank_path

    @Slot()
    def run(self) -> None:
        try:
            result = ReconciliationService().run(self.system_path, self.bank_path)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class PairDialog(QDialog):
    def __init__(
        self,
        language: str,
        system_title: str,
        system_headers: list[str],
        system_row,
        bank_title: str,
        bank_headers: list[str],
        bank_row,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(tr(language, "open_pair_title"))
        self.resize(980, 640)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)
        layout.addWidget(self._build_browser(system_title, system_headers, system_row))
        layout.addWidget(self._build_browser(bank_title, bank_headers, bank_row))

    def _build_browser(self, title: str, headers: list[str], row) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        browser = QTextBrowser(panel)
        browser.setOpenExternalLinks(False)
        browser.setHtml(self._build_html(headers, row))
        layout.addWidget(title_label)
        layout.addWidget(browser)
        return panel

    @staticmethod
    def _build_html(headers: list[str], row) -> str:
        if row is None:
            return "<p>Chưa có dữ liệu đối ứng.</p>"
        items = []
        for header, value in zip(headers, row.display_values, strict=False):
            items.append(
                f"<tr><td style='padding:6px 10px;font-weight:600'>{escape(header)}</td>"
                f"<td style='padding:6px 10px'>{escape(value or '')}</td></tr>"
            )
        items.append(
            f"<tr><td style='padding:6px 10px;font-weight:600'>Trạng thái</td>"
            f"<td style='padding:6px 10px'>{escape(row.status)}</td></tr>"
        )
        items.append(
            f"<tr><td style='padding:6px 10px;font-weight:600'>Lý do</td>"
            f"<td style='padding:6px 10px'>{escape(row.match_reason or '')}</td></tr>"
        )
        return (
            "<table width='100%' cellspacing='0' cellpadding='0' "
            "style='border-collapse:collapse'>"
            + "".join(items)
            + "</table>"
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.current_language = "vi"
        self.history_store = HistoryStore("data/history.sqlite")
        self.current_result: ReconciliationResult | None = None
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self.system_model: TransactionsTableModel | None = None
        self.bank_model: TransactionsTableModel | None = None
        self.system_proxy: TransactionsFilterProxyModel | None = None
        self.bank_proxy: TransactionsFilterProxyModel | None = None
        self._system_left = True
        self._build_ui()
        self._apply_styles()
        self._refresh_history()
        self._update_locked_state(True)
        self._apply_language()

    def _build_ui(self) -> None:
        self.setWindowTitle("Tool đối soát sao kê ngân hàng")
        self.resize(1520, 980)

        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(14)
        root.addLayout(top_layout)

        self.file_card = QFrame()
        self.file_card.setObjectName("card")
        file_layout = QGridLayout(self.file_card)
        file_layout.setContentsMargins(18, 18, 18, 18)
        file_layout.setHorizontalSpacing(10)
        file_layout.setVerticalSpacing(12)

        self.system_file_label = QLabel()
        self.bank_file_label = QLabel()
        self.language_label = QLabel()
        self.reference_filter_label = QLabel()

        self.system_path_edit = QLineEdit()
        self.system_path_edit.setReadOnly(True)
        self.bank_path_edit = QLineEdit()
        self.bank_path_edit.setReadOnly(True)

        self.system_choose_button = QPushButton()
        self.bank_choose_button = QPushButton()
        self.system_choose_button.clicked.connect(lambda: self._choose_file("system"))
        self.bank_choose_button.clicked.connect(lambda: self._choose_file("bank"))

        self.language_combo = QComboBox()
        self.language_combo.addItem("Tiếng Việt", "vi")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("中文简体", "zh")
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        self.scan_button = QPushButton()
        self.export_button = QPushButton()
        self.attach_statement_checkbox = QCheckBox()
        self.scan_button.clicked.connect(self._start_scan)
        self.export_button.clicked.connect(self._export_unmatched)
        self.export_button.setEnabled(False)
        self.attach_statement_checkbox.setChecked(False)

        file_layout.addWidget(self.system_file_label, 0, 0)
        file_layout.addWidget(self.system_path_edit, 0, 1)
        file_layout.addWidget(self.system_choose_button, 0, 2)
        file_layout.addWidget(self.bank_file_label, 1, 0)
        file_layout.addWidget(self.bank_path_edit, 1, 1)
        file_layout.addWidget(self.bank_choose_button, 1, 2)
        file_layout.addWidget(self.language_label, 2, 0)
        file_layout.addWidget(self.language_combo, 2, 1)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        action_row.addWidget(self.scan_button)
        action_row.addWidget(self.export_button)
        action_row.addWidget(self.attach_statement_checkbox)
        action_row.addStretch(1)
        file_layout.addLayout(action_row, 2, 2)

        self.history_card = QFrame()
        self.history_card.setObjectName("card")
        history_layout = QVBoxLayout(self.history_card)
        history_layout.setContentsMargins(18, 18, 18, 18)
        self.history_title = QLabel()
        self.history_title.setObjectName("sectionTitle")
        self.history_table = QTableWidget(0, 4)
        self.history_table.verticalHeader().hide()
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.NoSelection)
        self.history_table.setShowGrid(False)
        self.history_table.setMinimumWidth(420)
        history_layout.addWidget(self.history_title)
        history_layout.addWidget(self.history_table)

        top_layout.addWidget(self.file_card, 3)
        top_layout.addWidget(self.history_card, 2)

        self.metadata_card = QFrame()
        self.metadata_card.setObjectName("card")
        metadata_layout = QVBoxLayout(self.metadata_card)
        metadata_layout.setContentsMargins(18, 18, 18, 18)
        self.metadata_title = QLabel()
        self.metadata_title.setObjectName("sectionTitle")
        metadata_layout.addWidget(self.metadata_title)
        self.metadata_grid = QGridLayout()
        self.metadata_grid.setHorizontalSpacing(12)
        self.metadata_grid.setVerticalSpacing(12)
        metadata_layout.addLayout(self.metadata_grid)
        root.addWidget(self.metadata_card)

        self.metric_titles: dict[str, QLabel] = {}
        self.metric_values: dict[str, QLabel] = {}
        metric_order = [
            "meta_bank_name",
            "meta_tax_code",
            "meta_period",
            "meta_account_number",
            "meta_account_name",
            "meta_currency",
            "meta_account_type",
            "meta_opening_balance",
            "meta_actual_balance",
            "meta_closing_balance",
            "meta_total_debits",
            "meta_total_credits",
            "meta_total_fees",
            "meta_total_vat",
            "meta_total_debit_tx",
            "meta_total_credit_tx",
        ]
        for index, key in enumerate(metric_order):
            row = index // 4
            column = index % 4
            card, title_label, value_label = self._create_metric_widget()
            self.metric_titles[key] = title_label
            self.metric_values[key] = value_label
            self.metadata_grid.addWidget(card, row, column)

        self.results_card = QFrame()
        self.results_card.setObjectName("card")
        results_layout = QVBoxLayout(self.results_card)
        results_layout.setContentsMargins(18, 18, 18, 18)
        results_layout.setSpacing(12)
        self.results_title = QLabel()
        self.results_title.setObjectName("sectionTitle")
        results_layout.addWidget(self.results_title)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(8)
        results_layout.addLayout(toolbar_layout)

        self.status_group = QButtonGroup(self)
        self.status_group.setExclusive(True)
        self.status_buttons: dict[str, QPushButton] = {}
        for mode in ("all", "matched", "unmatched"):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(self._apply_filters)
            self.status_group.addButton(button)
            self.status_buttons[mode] = button
            toolbar_layout.addWidget(button)
        self.status_buttons["all"].setChecked(True)

        toolbar_layout.addSpacing(12)

        self.flow_group = QButtonGroup(self)
        self.flow_group.setExclusive(True)
        self.flow_buttons: dict[str, QPushButton] = {}
        for mode in ("all", "income", "expense", "tax"):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(self._apply_filters)
            self.flow_group.addButton(button)
            self.flow_buttons[mode] = button
            toolbar_layout.addWidget(button)
        self.flow_buttons["all"].setChecked(True)

        self.reference_filter_combo = QComboBox()
        self.reference_filter_combo.setMinimumWidth(230)
        self.reference_filter_combo.currentIndexChanged.connect(self._apply_filters)
        toolbar_layout.addSpacing(12)
        toolbar_layout.addWidget(self.reference_filter_label)
        toolbar_layout.addWidget(self.reference_filter_combo)

        toolbar_layout.addStretch(1)
        self.summary_label = QLabel()
        self.summary_label.setObjectName("summaryLabel")
        toolbar_layout.addWidget(self.summary_label)
        self.swap_button = QPushButton()
        self.swap_button.clicked.connect(self._swap_grids)
        toolbar_layout.addWidget(self.swap_button)

        self.locked_label = QLabel()
        self.locked_label.setObjectName("lockedLabel")
        results_layout.addWidget(self.locked_label)

        self.results_content = QWidget()
        content_layout = QHBoxLayout(self.results_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(12)
        self.results_splitter = QSplitter(Qt.Horizontal)
        content_layout.addWidget(self.results_splitter)
        results_layout.addWidget(self.results_content)
        root.addWidget(self.results_card, 1)

        self.system_grid = self._create_grid_panel()
        self.bank_grid = self._create_grid_panel()
        self.results_splitter.addWidget(self.system_grid.container)
        self.results_splitter.addWidget(self.bank_grid.container)
        self.results_splitter.setStretchFactor(0, 1)
        self.results_splitter.setStretchFactor(1, 1)

        self.action_delegate = ActionButtonDelegate(self)
        self.system_grid.table.set_action_delegate(self.action_delegate)
        self.bank_grid.table.set_action_delegate(self.action_delegate)
        self.system_grid.table.action_requested.connect(lambda row: self._open_pair("system", row))
        self.bank_grid.table.action_requested.connect(lambda row: self._open_pair("bank", row))
        self.system_grid.search.textChanged.connect(self._filter_system_grid)
        self.bank_grid.search.textChanged.connect(self._filter_bank_grid)
        self.system_grid.columns.currentIndexChanged.connect(self._filter_system_grid)
        self.bank_grid.columns.currentIndexChanged.connect(self._filter_bank_grid)

        self.overlay = LoadingOverlay(central)
        self.overlay.bind_parent()

    def _create_grid_panel(self) -> GridWidgets:
        container = QFrame()
        container.setObjectName("panelCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_label = QLabel()
        title_label.setObjectName("sectionTitle")
        count_label = QLabel()
        count_label.setObjectName("countLabel")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(count_label)

        filter_row = QHBoxLayout()
        columns_combo = QComboBox()
        search_edit = QLineEdit()
        search_edit.setClearButtonEnabled(True)
        filter_row.addWidget(columns_combo, 1)
        filter_row.addWidget(search_edit, 2)

        table = FrozenTableView()
        table.setSortingEnabled(True)
        table.setSelectionBehavior(FrozenTableView.SelectRows)
        table.setSelectionMode(FrozenTableView.SingleSelection)

        layout.addLayout(title_row)
        layout.addLayout(filter_row)
        layout.addWidget(table)
        return GridWidgets(title_label, count_label, search_edit, columns_combo, table, container)

    def _create_metric_widget(self) -> tuple[QWidget, QLabel, QLabel]:
        frame = QFrame()
        frame.setObjectName("metricCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        title = QLabel()
        title.setObjectName("metricTitle")
        value = QLabel("-")
        value.setObjectName("metricValue")
        value.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(value)
        return frame, title, value

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #f5f7fb;
                color: #18212f;
                font-family: "Segoe UI", "Microsoft YaHei UI";
                font-size: 13px;
            }
            QMainWindow {
                background: #eef3f9;
            }
            QFrame#card, QFrame#panelCard, QFrame#metricCard, QFrame#loadingCard {
                background: white;
                border: 1px solid #dbe4f0;
                border-radius: 16px;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: 700;
                color: #0f172a;
            }
            QLabel#subtitleLabel {
                color: #475569;
                margin-bottom: 2px;
            }
            QLabel#sectionTitle {
                font-size: 15px;
                font-weight: 700;
                color: #111827;
            }
            QLabel#summaryLabel {
                font-weight: 600;
                color: #1f2937;
            }
            QLabel#countLabel, QLabel#metricTitle {
                color: #64748b;
                font-size: 12px;
            }
            QLabel#metricValue {
                font-size: 14px;
                font-weight: 600;
                color: #0f172a;
            }
            QLabel#lockedLabel {
                color: #64748b;
                background: #f8fafc;
                border: 1px dashed #cbd5e1;
                border-radius: 12px;
                padding: 12px;
            }
            QLabel#loadingLabel {
                font-size: 15px;
                font-weight: 600;
                color: #0f172a;
            }
            QLineEdit, QComboBox, QTableWidget, QTableView, QTextBrowser {
                background: white;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 6px 8px;
            }
            QPushButton {
                background: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 8px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #dbe7f6;
            }
            QPushButton:checked {
                background: #dbeafe;
                border: 1px solid #60a5fa;
                color: #1d4ed8;
            }
            QPushButton:disabled {
                color: #94a3b8;
                background: #e5e7eb;
            }
            QHeaderView::section {
                background: #eaf0f8;
                border: none;
                border-bottom: 1px solid #dbe4f0;
                padding: 8px;
                font-weight: 700;
            }
            QTableView {
                gridline-color: #e5e7eb;
                selection-background-color: #bfdbfe;
                alternate-background-color: #f8fafc;
            }
            QTableView::item {
                padding: 4px;
            }
            QProgressBar {
                background: #e2e8f0;
                border-radius: 6px;
                border: none;
                min-height: 12px;
            }
            QProgressBar::chunk {
                background: #2563eb;
                border-radius: 6px;
            }
            """
        )

    def _apply_language(self) -> None:
        self.title_label.setText(tr(self.current_language, "app_title"))
        self.subtitle_label.setText(tr(self.current_language, "app_subtitle"))
        self.system_file_label.setText(tr(self.current_language, "system_file"))
        self.bank_file_label.setText(tr(self.current_language, "bank_file"))
        self.language_label.setText(tr(self.current_language, "language"))
        self.reference_filter_label.setText(tr(self.current_language, "reference_filter"))
        self.system_choose_button.setText(tr(self.current_language, "choose_file"))
        self.bank_choose_button.setText(tr(self.current_language, "choose_file"))
        self.scan_button.setText(tr(self.current_language, "scan"))
        self.export_button.setText(self._export_button_label())
        self.attach_statement_checkbox.setText(tr(self.current_language, "attach_statement"))
        self.history_title.setText(tr(self.current_language, "recent_history"))
        self.metadata_title.setText(tr(self.current_language, "bank_info"))
        self.results_title.setText(tr(self.current_language, "results"))
        self.locked_label.setText(tr(self.current_language, "results_locked"))
        self.swap_button.setText(tr(self.current_language, "swap_grids"))
        self.status_buttons["all"].setText(tr(self.current_language, "status_all"))
        self.status_buttons["matched"].setText(tr(self.current_language, "status_matched"))
        self.status_buttons["unmatched"].setText(tr(self.current_language, "status_unmatched"))
        self.flow_buttons["all"].setText(tr(self.current_language, "flow_all"))
        self.flow_buttons["income"].setText(tr(self.current_language, "flow_income"))
        self.flow_buttons["expense"].setText(tr(self.current_language, "flow_expense"))
        self.flow_buttons["tax"].setText(tr(self.current_language, "flow_tax"))
        self.system_grid.title.setText(tr(self.current_language, "system_grid"))
        self.bank_grid.title.setText(tr(self.current_language, "bank_grid"))
        self.system_grid.search.setPlaceholderText(tr(self.current_language, "search"))
        self.bank_grid.search.setPlaceholderText(tr(self.current_language, "search"))
        for key, label in self.metric_titles.items():
            label.setText(tr(self.current_language, key))
        self._refresh_history_headers()
        self._populate_reference_filter_options()
        if self.system_model:
            self.system_model.set_language(self.current_language)
        if self.bank_model:
            self.bank_model.set_language(self.current_language)
        self._populate_search_columns()
        self._update_summary()
        self._update_row_counts()

    def _refresh_history_headers(self) -> None:
        self.history_table.setHorizontalHeaderLabels(
            [
                tr(self.current_language, "history_time"),
                tr(self.current_language, "history_system"),
                tr(self.current_language, "history_bank"),
                tr(self.current_language, "history_result"),
            ]
        )

    def _choose_file(self, file_type: str) -> None:
        title = tr(self.current_language, "choose_file")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(Path.cwd()),
            "Excel Files (*.xls *.xlsx)",
        )
        if not file_path:
            return
        if file_type == "system":
            self.system_path_edit.setText(file_path)
        else:
            self.bank_path_edit.setText(file_path)

    def _on_language_changed(self) -> None:
        self.current_language = self.language_combo.currentData()
        self._apply_language()

    def _update_locked_state(self, locked: bool) -> None:
        self.results_content.setEnabled(not locked)
        self.locked_label.setVisible(locked)
        self.export_button.setEnabled(not locked and self.current_result is not None)
        self.attach_statement_checkbox.setEnabled(not locked and self.current_result is not None)
        self.metadata_card.setEnabled(not locked)
        self.swap_button.setEnabled(not locked)
        self.reference_filter_combo.setEnabled(not locked)
        for button in self.status_buttons.values():
            button.setEnabled(not locked)
        for button in self.flow_buttons.values():
            button.setEnabled(not locked)

    def _start_scan(self) -> None:
        system_path = self.system_path_edit.text().strip()
        bank_path = self.bank_path_edit.text().strip()
        if not system_path or not bank_path:
            QMessageBox.warning(
                self,
                tr(self.current_language, "app_title"),
                tr(self.current_language, "select_files_first"),
            )
            return
        self.overlay.set_message(tr(self.current_language, "loading"))
        self.overlay.show()
        self.scan_button.setEnabled(False)

        self._scan_thread = QThread(self)
        self._scan_worker = ScanWorker(system_path, bank_path)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._scan_finished)
        self._scan_worker.failed.connect(self._scan_failed)
        self._scan_worker.finished.connect(self._scan_thread.quit)
        self._scan_worker.failed.connect(self._scan_thread.quit)
        self._scan_thread.finished.connect(self._cleanup_scan_thread)
        self._scan_thread.start()

    @Slot(object)
    def _scan_finished(self, result: ReconciliationResult) -> None:
        self.current_result = result
        self.history_store.add_result(result)
        self._bind_result_to_grids(result)
        self._fill_metadata(result)
        self._refresh_history()
        self._update_locked_state(False)
        self.overlay.hide()
        self.scan_button.setEnabled(True)
        QMessageBox.information(
            self,
            tr(self.current_language, "app_title"),
            tr(self.current_language, "scan_success"),
        )

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self.overlay.hide()
        self.scan_button.setEnabled(True)
        QMessageBox.critical(
            self,
            tr(self.current_language, "app_title"),
            f"{tr(self.current_language, 'scan_failed')}\n{message}",
        )

    @Slot()
    def _cleanup_scan_thread(self) -> None:
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None
        if self._scan_thread:
            self._scan_thread.deleteLater()
            self._scan_thread = None

    def _bind_result_to_grids(self, result: ReconciliationResult) -> None:
        self.system_model = TransactionsTableModel(result.system_headers, result.system_rows, self.current_language)
        self.bank_model = TransactionsTableModel(result.bank_headers, result.bank_rows, self.current_language)
        self.system_proxy = TransactionsFilterProxyModel()
        self.bank_proxy = TransactionsFilterProxyModel()
        self.system_proxy.setSourceModel(self.system_model)
        self.bank_proxy.setSourceModel(self.bank_model)
        self.system_proxy.setSortRole(Qt.UserRole + 2)
        self.bank_proxy.setSortRole(Qt.UserRole + 2)
        self.system_grid.table.setModel(self.system_proxy)
        self.bank_grid.table.setModel(self.bank_proxy)
        self.system_grid.table.set_action_delegate(self.action_delegate)
        self.bank_grid.table.set_action_delegate(self.action_delegate)
        self.system_grid.table.sortByColumn(1, Qt.AscendingOrder)
        self.bank_grid.table.sortByColumn(1, Qt.AscendingOrder)
        self._populate_search_columns()
        self._apply_filters()
        self._update_summary()
        self._update_row_counts()

    def _populate_search_columns(self) -> None:
        for combo, model in (
            (self.system_grid.columns, self.system_model),
            (self.bank_grid.columns, self.bank_model),
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(tr(self.current_language, "all_columns"), -1)
            if model:
                for index, header in enumerate(model._headers):
                    combo.addItem(header, index)
            combo.blockSignals(False)

    def _apply_filters(self) -> None:
        if not self.system_proxy or not self.bank_proxy:
            return
        status_mode = next(mode for mode, button in self.status_buttons.items() if button.isChecked())
        flow_mode = next(mode for mode, button in self.flow_buttons.items() if button.isChecked())
        reference_mode = self.reference_filter_combo.currentData() or "all"
        for proxy in (self.system_proxy, self.bank_proxy):
            proxy.set_status_mode(status_mode)
            proxy.set_flow_mode(flow_mode)
            proxy.set_reference_mode(str(reference_mode))
        self._filter_system_grid()
        self._filter_bank_grid()
        self._update_summary()
        self._update_row_counts()

    def _filter_system_grid(self) -> None:
        if not self.system_proxy:
            return
        current_data = self.system_grid.columns.currentData()
        self.system_proxy.set_search_column(-1 if current_data is None else int(current_data))
        self.system_proxy.set_search_text(self.system_grid.search.text())
        self._update_row_counts()

    def _filter_bank_grid(self) -> None:
        if not self.bank_proxy:
            return
        current_data = self.bank_grid.columns.currentData()
        self.bank_proxy.set_search_column(-1 if current_data is None else int(current_data))
        self.bank_proxy.set_search_text(self.bank_grid.search.text())
        self._update_row_counts()

    def _update_summary(self) -> None:
        if not self.current_result:
            self.summary_label.setText("")
            return
        summary = self.current_result.summary
        self.summary_label.setText(
            tr(
                self.current_language,
                "summary_text",
                matched=summary.matched_system,
                review=summary.review_system,
                unmatched=summary.unmatched_system,
            )
        )

    def _update_row_counts(self) -> None:
        for grid, model, proxy in (
            (self.system_grid, self.system_model, self.system_proxy),
            (self.bank_grid, self.bank_model, self.bank_proxy),
        ):
            total = model.total_rows if model else 0
            visible = proxy.rowCount() if proxy else 0
            grid.count.setText(tr(self.current_language, "grid_rows", visible=visible, total=total))

    def _fill_metadata(self, result: ReconciliationResult) -> None:
        metadata = result.metadata
        period_text = ""
        if metadata.from_date and metadata.to_date:
            period_text = f"{metadata.from_date:%Y-%m-%d} -> {metadata.to_date:%Y-%m-%d}"
        values = {
            "meta_bank_name": " / ".join(value for value in (metadata.bank_name_vi, metadata.bank_name_en) if value),
            "meta_tax_code": metadata.tax_code,
            "meta_period": period_text,
            "meta_account_number": metadata.account_number,
            "meta_account_name": metadata.account_name,
            "meta_currency": metadata.currency,
            "meta_account_type": metadata.account_type,
            "meta_opening_balance": format_vnd(metadata.opening_balance),
            "meta_actual_balance": format_vnd(metadata.actual_balance),
            "meta_closing_balance": format_vnd(metadata.closing_balance),
            "meta_total_debits": format_vnd(abs(metadata.total_debits or 0)),
            "meta_total_credits": format_vnd(abs(metadata.total_credits or 0)),
            "meta_total_fees": format_vnd(abs(metadata.total_fees or 0)),
            "meta_total_vat": format_vnd(abs(metadata.total_vat or 0)),
            "meta_total_debit_tx": format_vnd(metadata.total_debit_transactions),
            "meta_total_credit_tx": format_vnd(metadata.total_credit_transactions),
        }
        for key, label in self.metric_values.items():
            label.setText(values.get(key) or "-")

    def _refresh_history(self) -> None:
        records = self.history_store.list_recent()
        self._refresh_history_headers()
        self.history_table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            scanned_at = record["scanned_at"].replace("T", " ")
            summary = f"{record['matched_system']} | {record['review_system']} | {record['unmatched_system']}"
            items = [
                scanned_at,
                Path(str(record["system_file"])).name,
                Path(str(record["bank_file"])).name,
                summary,
            ]
            for column_index, value in enumerate(items):
                item = QTableWidgetItem(value)
                self.history_table.setItem(row_index, column_index, item)
        self.history_table.resizeColumnsToContents()
        self.history_table.horizontalHeader().setStretchLastSection(True)

    def _swap_grids(self) -> None:
        self._system_left = not self._system_left
        self.results_splitter.insertWidget(0, self.system_grid.container if self._system_left else self.bank_grid.container)
        self.results_splitter.insertWidget(1, self.bank_grid.container if self._system_left else self.system_grid.container)

    def _open_pair(self, source: str, row) -> None:
        if self.current_result is None:
            return
        if source == "system":
            system_row = row
            bank_row = self._bank_row_by_id(row.matched_bank_id) if row.matched_bank_id else None
            self._focus_counterpart(self.bank_model, self.bank_proxy, self.bank_grid.table, row.matched_bank_id)
        else:
            bank_row = row
            system_row = self._system_row_by_id(row.matched_system_id) if row.matched_system_id else None
            self._focus_counterpart(self.system_model, self.system_proxy, self.system_grid.table, row.matched_system_id)
        dialog = PairDialog(
            self.current_language,
            tr(self.current_language, "paired_system"),
            self.current_result.system_headers,
            system_row,
            tr(self.current_language, "paired_bank"),
            self.current_result.bank_headers,
            bank_row,
            self,
        )
        dialog.exec()

    def _focus_counterpart(self, model, proxy, table: FrozenTableView, row_id: str | None) -> None:
        if not model or not proxy or not row_id:
            return
        source_row = model.row_index_by_id(row_id)
        if source_row is None:
            return
        source_index = model.index(source_row, 0)
        proxy_index = proxy.mapFromSource(source_index)
        if not proxy_index.isValid():
            return
        table.select_proxy_index(proxy_index)

    def _system_row_by_id(self, row_id: str | None):
        if not self.system_model or row_id is None:
            return None
        index = self.system_model.row_index_by_id(row_id)
        return self.system_model.row_object(index) if index is not None else None

    def _bank_row_by_id(self, row_id: str | None):
        if not self.bank_model or row_id is None:
            return None
        index = self.bank_model.row_index_by_id(row_id)
        return self.bank_model.row_object(index) if index is not None else None

    def _export_unmatched(self) -> None:
        if not self.current_result or not self.system_model or not self.system_proxy:
            return
        rows_to_export = self._visible_system_rows()
        if not rows_to_export:
            QMessageBox.information(
                self,
                tr(self.current_language, "app_title"),
                self._no_rows_to_export_message(),
            )
            return
        status_mode = self._current_status_mode()
        highlight_unmatched = status_mode == "all"
        default_name = (
            f"{self._default_export_name(status_mode)}_{datetime.now():%Y%m%d_%H%M%S}.xlsx"
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr(self.current_language, "save_dialog_title"),
            str(Path.cwd() / safe_name(default_name)),
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            return
        try:
            attached_statement_path = (
                self.current_result.bank_file if self.attach_statement_checkbox.isChecked() else None
            )
            export_system_rows(
                self.current_result.system_headers,
                rows_to_export,
                file_path,
                highlight_unmatched=highlight_unmatched,
                sheet_name="HeThong_Xuat",
                attached_statement_path=attached_statement_path,
            )
        except ValueError:
            QMessageBox.information(
                self,
                tr(self.current_language, "app_title"),
                self._no_rows_to_export_message(),
            )
            return
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(
                self,
                tr(self.current_language, "app_title"),
                f"{tr(self.current_language, 'export_failed')}\n{exc}",
            )
            return
        QMessageBox.information(
            self,
            tr(self.current_language, "app_title"),
            tr(self.current_language, "export_success"),
        )

    def _visible_system_rows(self) -> list[object]:
        if not self.system_model or not self.system_proxy:
            return []
        rows: list[object] = []
        for proxy_row in range(self.system_proxy.rowCount()):
            proxy_index = self.system_proxy.index(proxy_row, 0)
            source_index = self.system_proxy.mapToSource(proxy_index)
            if not source_index.isValid():
                continue
            rows.append(self.system_model.row_object(source_index.row()))
        return rows

    def _current_status_mode(self) -> str:
        return next(mode for mode, button in self.status_buttons.items() if button.isChecked())

    def _export_button_label(self) -> str:
        labels = {
            "vi": "Xuất Excel",
            "en": "Export Excel",
            "zh": "导出 Excel",
        }
        return labels.get(self.current_language, labels["vi"])

    def _default_export_name(self, status_mode: str) -> str:
        if status_mode == "unmatched":
            names = {
                "vi": "HeThong_KhongKhop",
                "en": "System_Unmatched",
                "zh": "系统_未匹配",
            }
        else:
            names = {
                "vi": "HeThong_DangHien",
                "en": "System_CurrentView",
                "zh": "系统_当前视图",
            }
        return names.get(self.current_language, names["vi"])

    def _no_rows_to_export_message(self) -> str:
        messages = {
            "vi": "Không có dữ liệu để xuất theo bộ lọc hiện tại.",
            "en": "There are no rows to export for the current filter.",
            "zh": "当前筛选条件下没有可导出的数据。",
        }
        return messages.get(self.current_language, messages["vi"])

    def _populate_reference_filter_options(self) -> None:
        current_value = self.reference_filter_combo.currentData()
        options = [
            ("all", "reference_all"),
            ("FT", "reference_ft"),
            ("ST", "reference_st"),
            ("SK", "reference_sk"),
            ("LD", "reference_ld"),
            ("HB", "reference_hb"),
        ]
        self.reference_filter_combo.blockSignals(True)
        self.reference_filter_combo.clear()
        for value, key in options:
            self.reference_filter_combo.addItem(tr(self.current_language, key), value)
        if current_value is None:
            current_value = "all"
        index = self.reference_filter_combo.findData(current_value)
        self.reference_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        self.reference_filter_combo.blockSignals(False)
