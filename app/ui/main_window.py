from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from html import escape
import logging
from pathlib import Path

from PySide6.QtCore import QDate, QObject, QSize, QThread, Qt, Signal, Slot, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDateEdit,
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
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.models import ReconciliationResult
from app.resource_utils import logo_image_path
from app.services.excel_loader import detect_excel_file_kind
from app.services.exporter import export_system_rows
from app.services.history_store import HistoryStore
from app.services.reconciliation import ReconciliationService
from app.services.utils import format_vnd
from app.ui.table_models import TransactionsFilterProxyModel, TransactionsTableModel, status_bucket_for_row
from app.ui.widgets import FrozenTableView, InstantToolTipButton, LoadingOverlay, PopupDateEdit, StyledComboBox

logger = logging.getLogger(__name__)


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
            logger.info(
                "Worker bắt đầu dò. system_file=%s | bank_file=%s",
                self.system_path,
                self.bank_path,
            )
            result = ReconciliationService().run(self.system_path, self.bank_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Worker dò lỗi: %s", exc)
            self.failed.emit(str(exc))
            return
        logger.info("Worker dò hoàn tất.")
        self.finished.emit(result)


class PairDialog(QDialog):
    def __init__(
        self,
        language: str,
        system_title: str,
        system_headers: list[str],
        system_rows,
        bank_title: str,
        bank_headers: list[str],
        bank_rows,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        logo_path = logo_image_path()
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.language = language
        self.system_rows = list(system_rows or [])
        self.bank_rows = list(bank_rows or [])
        self.setWindowTitle(tr(language, "open_pair_title"))
        self.resize(960, 620)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)
        layout.addWidget(self._build_panel(system_title, system_headers, self.system_rows, self.bank_rows), 1)
        layout.addWidget(self._build_panel(bank_title, bank_headers, self.bank_rows, self.system_rows), 1)

    def _build_panel(self, title: str, headers: list[str], rows: list[object], counterpart_rows: list[object]) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        browser = QTextBrowser(panel)
        browser.setOpenExternalLinks(False)
        browser.setHtml(self._build_details_html(headers, rows))
        layout.addWidget(title_label)
        layout.addWidget(browser, 1)

        if rows:
            toggle = QToolButton(panel)
            toggle.setCheckable(True)
            toggle.setChecked(False)
            toggle.setArrowType(Qt.RightArrow)
            toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            toggle.setText(self._label("explain_show"))

            explanation = QTextBrowser(panel)
            explanation.setOpenExternalLinks(False)
            explanation.setVisible(False)
            explanation.setMaximumHeight(220)
            explanation.setHtml(self._build_explanation_html(rows, counterpart_rows))

            toggle.toggled.connect(
                lambda checked, button=toggle, widget=explanation: self._toggle_explanation(button, widget, checked)
            )
            layout.addWidget(toggle, alignment=Qt.AlignLeft)
            layout.addWidget(explanation)
        return panel

    def _build_details_html(self, headers: list[str], rows: list[object]) -> str:
        if not rows:
            return f"<p>{escape(tr(self.language, 'no_pair'))}</p>"
        if len(rows) == 1:
            details_rows = self._single_row_details(headers, rows[0])
            return self._table_html(details_rows) if details_rows else f"<p>{escape(tr(self.language, 'no_pair'))}</p>"

        html_sections = [
            "<div style='margin-bottom:10px;padding:10px 12px;border:1px solid #dbe4f0;"
            "border-radius:12px;background:#f8fbff'>"
            f"<b>{escape(self._label('group_summary'))}</b><br>"
            f"{escape(self._label('group_rows'))}: {len(rows)}<br>"
            f"{escape(self._label('group_total'))}: {escape(format_vnd(sum(getattr(row, 'amount', 0) for row in rows)))}"
            "</div>"
        ]
        for index, row in enumerate(rows, start=1):
            details_rows = self._single_row_details(headers, row)
            if not details_rows:
                continue
            html_sections.append(
                "<div style='margin-bottom:14px'>"
                f"<div style='margin-bottom:6px;font-weight:700;color:#0f172a'>"
                f"{escape(self._row_heading(index, row))}"
                "</div>"
                f"{self._table_html(details_rows)}"
                "</div>"
            )
        if len(html_sections) == 1:
            return f"<p>{escape(tr(self.language, 'no_pair'))}</p>"
        return "".join(html_sections)

    def _single_row_details(self, headers: list[str], row) -> list[str]:
        rows: list[str] = []
        for header, value in zip(headers, row.display_values, strict=False):
            text = (value or "").strip()
            if not text:
                continue
            rows.append(self._table_row(header, text))
        return rows

    def _build_explanation_html(self, current_rows: list[object], counterpart_rows: list[object]) -> str:
        first_row = current_rows[0]
        counterpart_first = counterpart_rows[0] if counterpart_rows else None
        counterpart_row = (
            getattr(first_row, "matched_bank_row", None)
            or getattr(first_row, "matched_system_row", None)
            or getattr(counterpart_first, "excel_row", None)
        )
        current_total = sum(getattr(row, "amount", 0) for row in current_rows)
        counterpart_total = sum(getattr(row, "amount", 0) for row in counterpart_rows)
        rows = [
            self._table_row(self._label("status_label"), tr(self.language, status_bucket_for_row(first_row))),
            self._table_row(self._label("match_type_label"), self._match_type_text(first_row)),
            self._table_row(self._label("group_id_label"), getattr(first_row, "group_id", None) or self._label("debug_none")),
            self._table_row(self._label("group_shape_label"), f"{len(current_rows)}-{len(counterpart_rows)}"),
            self._table_row(self._label("group_total_current"), format_vnd(current_total)),
            self._table_row(self._label("group_total_counterpart"), format_vnd(counterpart_total)),
            self._table_row(self._label("group_diff"), format_vnd(current_total - counterpart_total)),
            self._table_row(self._label("debug_confidence"), self._format_confidence(getattr(first_row, "confidence", 0))),
            self._table_row(
                self._label("debug_current_row"),
                self._rows_label(current_rows),
            ),
            self._table_row(
                self._label("debug_counterpart_row"),
                self._rows_label(counterpart_rows) if counterpart_rows else (
                    str(counterpart_row) if counterpart_row else self._label("debug_none")
                ),
            ),
            self._table_row(self._label("debug_date_basis"), self._date_basis_label(getattr(first_row, "match_reason", ""))),
            self._table_row(
                self._label("debug_basis"),
                self._format_match_basis(getattr(first_row, "match_reason", "")),
                is_html=True,
            ),
        ]
        return self._table_html(rows)

    def _table_html(self, rows: list[str]) -> str:
        return (
            "<table width='100%' cellspacing='0' cellpadding='0' "
            "style='border-collapse:collapse;table-layout:fixed'>"
            + "".join(rows)
            + "</table>"
        )

    def _table_row(self, label: str, value: str, *, is_html: bool = False) -> str:
        rendered = value if is_html else escape(value)
        return (
            "<tr>"
            "<td style='width:34%;padding:8px 10px;font-weight:600;vertical-align:top;"
            "background:#f8fafc;border-bottom:1px solid #e5e7eb;word-break:break-word'>"
            f"{escape(label)}"
            "</td>"
            "<td style='padding:8px 10px;vertical-align:top;border-bottom:1px solid #e5e7eb;"
            "white-space:pre-wrap;word-break:break-word'>"
            f"{rendered}"
            "</td>"
            "</tr>"
        )

    def _toggle_explanation(self, button: QToolButton, widget: QTextBrowser, checked: bool) -> None:
        widget.setVisible(checked)
        button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        button.setText(self._label("explain_hide") if checked else self._label("explain_show"))

    def _rows_label(self, rows: list[object]) -> str:
        if not rows:
            return self._label("debug_none")
        return ", ".join(str(getattr(row, "excel_row", "")) for row in rows if getattr(row, "excel_row", None))

    def _row_heading(self, index: int, row) -> str:
        return (
            f"{self._label('group_row')} {index} | "
            f"{self._label('debug_current_row')}: {getattr(row, 'excel_row', self._label('debug_none'))} | "
            f"{self._label('group_amount')}: {format_vnd(getattr(row, 'amount', 0))}"
        )

    def _match_type_text(self, row) -> str:
        match_type = getattr(row, "match_type", "none")
        if match_type == "group":
            return tr(self.language, "matched_group")
        if match_type == "exact":
            return tr(self.language, "matched_exact")
        return self._label("debug_none")

    def _label(self, key: str) -> str:
        labels = {
            "vi": {
                "status_label": "Trạng thái",
                "match_type_label": "Kiểu khớp",
                "group_id_label": "Mã nhóm",
                "group_shape_label": "Cấu trúc nhóm",
                "group_total_current": "Tổng tiền bên này",
                "group_total_counterpart": "Tổng tiền bên kia",
                "group_diff": "Chênh lệch",
                "group_summary": "Tóm tắt nhóm giao dịch",
                "group_rows": "Số dòng",
                "group_total": "Tổng tiền",
                "group_row": "Dòng",
                "group_amount": "Số tiền",
                "debug_confidence": "Độ tin cậy",
                "debug_current_row": "Dòng hiện tại",
                "debug_counterpart_row": "Dòng đối ứng",
                "debug_date_basis": "Ngày dùng để dò",
                "debug_basis": "Căn cứ dò",
                "debug_date_transaction": "Ngày giao dịch",
                "debug_date_reference": "Ngày suy ra từ mã nội bộ",
                "debug_none": "Không có",
                "explain_show": "Xem giải thích cách dò",
                "explain_hide": "Ẩn giải thích cách dò",
            },
            "en": {
                "status_label": "Status",
                "match_type_label": "Match type",
                "group_id_label": "Group ID",
                "group_shape_label": "Group shape",
                "group_total_current": "This side total",
                "group_total_counterpart": "Other side total",
                "group_diff": "Difference",
                "group_summary": "Grouped transaction summary",
                "group_rows": "Rows",
                "group_total": "Total amount",
                "group_row": "Row",
                "group_amount": "Amount",
                "debug_confidence": "Confidence",
                "debug_current_row": "Current row",
                "debug_counterpart_row": "Matched row",
                "debug_date_basis": "Date used",
                "debug_basis": "Matching basis",
                "debug_date_transaction": "Transaction date",
                "debug_date_reference": "Date derived from internal code",
                "debug_none": "None",
                "explain_show": "Show reconciliation basis",
                "explain_hide": "Hide reconciliation basis",
            },
            "zh": {
                "status_label": "状态",
                "match_type_label": "匹配类型",
                "group_id_label": "组编号",
                "group_shape_label": "组结构",
                "group_total_current": "当前侧合计",
                "group_total_counterpart": "对侧合计",
                "group_diff": "差额",
                "group_summary": "组合交易摘要",
                "group_rows": "行数",
                "group_total": "总金额",
                "group_row": "行",
                "group_amount": "金额",
                "debug_confidence": "置信度",
                "debug_current_row": "当前行",
                "debug_counterpart_row": "对应行",
                "debug_date_basis": "使用日期",
                "debug_basis": "匹配依据",
                "debug_date_transaction": "交易日期",
                "debug_date_reference": "从内部编码推导的日期",
                "debug_none": "无",
                "explain_show": "查看对账依据",
                "explain_hide": "隐藏对账依据",
            },
        }
        language_labels = labels.get(self.language, labels["vi"])
        return language_labels.get(key, key)

    def _format_confidence(self, confidence: int) -> str:
        if confidence <= 0:
            return self._label("debug_none")
        return f"{confidence}/100"

    def _format_match_basis(self, reason: str) -> str:
        if not reason:
            return self._label("debug_none")
        reasons = [segment.strip() for segment in reason.splitlines() if segment.strip()]
        if not reasons:
            return escape(self._label("debug_none"))
        return (
            "<ul style='margin:0;padding-left:18px'>"
            + "".join(f"<li style='margin:0 0 4px 0'>{escape(item)}</li>" for item in reasons)
            + "</ul>"
        )

    def _date_basis_label(self, reason: str) -> str:
        if "Ngày theo mã nội bộ" in reason:
            return self._label("debug_date_reference")
        if "Ngày giao dịch" in reason:
            return self._label("debug_date_transaction")
        return self._label("debug_none")


class HistoryDialog(QDialog):
    def __init__(self, language: str, records: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        logo_path = logo_image_path()
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.language = language
        self.setWindowTitle(tr(language, "recent_history"))
        self.resize(920, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(tr(language, "recent_history"))
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        self.table = QTableWidget(0, 4, self)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "history_time"),
                tr(language, "history_system"),
                tr(language, "history_bank"),
                tr(language, "history_result"),
            ]
        )
        layout.addWidget(self.table)
        self._fill_rows(records)

    def _fill_rows(self, records: list[dict]) -> None:
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            scanned_at = str(record.get("scanned_at", "")).replace("T", " ")
            summary = self._history_summary_text(record)
            values = [
                scanned_at,
                Path(str(record.get("system_file", ""))).name,
                Path(str(record.get("bank_file", ""))).name,
                summary,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(int(Qt.AlignLeft | Qt.AlignVCenter))
                self.table.setItem(row_index, column_index, item)
        self.table.setWordWrap(True)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 260)
        self.table.horizontalHeader().setStretchLastSection(True)

    def _history_summary_text(self, record: dict[str, object]) -> str:
        if self.language == "en":
            system_label = "System"
            bank_label = "Statement"
            matched_label = "matched"
            review_label = "review"
            unmatched_label = "unmatched"
        elif self.language == "zh":
            system_label = "系统"
            bank_label = "流水"
            matched_label = "已匹配"
            review_label = "待复核"
            unmatched_label = "未匹配"
        else:
            system_label = "Hệ thống"
            bank_label = "Sao kê"
            matched_label = "khớp"
            review_label = "cần kiểm tra"
            unmatched_label = "không khớp"
        return (
            f"{system_label}: {record.get('matched_system', 0)} {matched_label}, "
            f"{record.get('review_system', 0)} {review_label}, "
            f"{record.get('unmatched_system', 0)} {unmatched_label}\n"
            f"{bank_label}: {record.get('matched_bank', 0)} {matched_label}, "
            f"{record.get('review_bank', 0)} {review_label}, "
            f"{record.get('unmatched_bank', 0)} {unmatched_label}"
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        logo_path = logo_image_path()
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.current_language = "vi"
        self.history_store = HistoryStore("data/history.sqlite")
        self._history_records: list[dict] = []
        self._metadata_layout_mode = ""
        self._selected_system_path = ""
        self._selected_bank_path = ""
        self.current_result: ReconciliationResult | None = None
        self._initial_compact_size_applied = False
        self._expanded_window_size = QSize(1520, 980)
        self._compact_window_size = QSize(0, 0)
        self._scan_thread: QThread | None = None
        self._scan_worker: ScanWorker | None = None
        self.system_model: TransactionsTableModel | None = None
        self.bank_model: TransactionsTableModel | None = None
        self.system_proxy: TransactionsFilterProxyModel | None = None
        self.bank_proxy: TransactionsFilterProxyModel | None = None
        self._active_grid_mode = "bank"
        self._date_filter_active = False
        self._filter_overlay_active = False
        self._filter_apply_scheduled = False
        self._compact_window_mode = False
        self._build_ui()
        self._apply_styles()
        self._refresh_history()
        self._update_locked_state(True)
        self._apply_language()
        QTimer.singleShot(0, self._show_startup_page)
        logger.info("Đã khởi tạo MainWindow.")

    def _build_ui(self) -> None:
        self.setWindowTitle("BSR v1.0")
        self.resize(self._expanded_window_size)

        central = QWidget(self)
        self.setCentralWidget(central)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)

        self.page_stack = QStackedWidget(central)
        self.page_stack.setObjectName("mainPageStack")
        central_layout.addWidget(self.page_stack)

        self.startup_page = QWidget()
        self.startup_page.setObjectName("startupPage")
        self.startup_layout = QVBoxLayout(self.startup_page)
        self.startup_layout.setContentsMargins(18, 18, 18, 18)
        self.startup_layout.setSpacing(0)
        self.startup_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.page_stack.addWidget(self.startup_page)

        self.results_page = QWidget()
        self.results_page.setObjectName("resultsPage")
        self.results_page_layout = QVBoxLayout(self.results_page)
        self.results_page_layout.setContentsMargins(0, 0, 0, 0)
        self.results_page_layout.setSpacing(0)
        self.page_stack.addWidget(self.results_page)

        self.scroll_area = QScrollArea(self.results_page)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.results_page_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)

        root = QVBoxLayout(self.scroll_content)
        self.root_layout = root
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)
        root.setAlignment(Qt.AlignTop)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        self.title_label.hide()
        self.subtitle_label.hide()
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)

        self.top_section = QWidget()
        self.top_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.top_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(16)
        self.top_layout.setAlignment(Qt.AlignTop)
        self.top_section.setLayout(self.top_layout)
        root.addWidget(self.top_section)

        self.file_card = QFrame()
        self.file_card.setObjectName("card")
        self.file_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        file_layout = QGridLayout(self.file_card)
        file_layout.setContentsMargins(14, 14, 14, 14)
        file_layout.setHorizontalSpacing(8)
        file_layout.setVerticalSpacing(8)
        file_layout.setColumnStretch(1, 1)

        self.system_file_label = QLabel()
        self.bank_file_label = QLabel()
        self.language_label = QLabel()
        self.reference_filter_label = QLabel()
        self.reference_filter_label.setObjectName("filterLabel")

        self.system_path_edit = QLineEdit()
        self.system_path_edit.setReadOnly(True)
        self.bank_path_edit = QLineEdit()
        self.bank_path_edit.setReadOnly(True)
        self.system_path_edit.setMinimumHeight(38)
        self.bank_path_edit.setMinimumHeight(38)

        self.system_choose_button = QPushButton()
        self.bank_choose_button = QPushButton()
        for button in (self.system_choose_button, self.bank_choose_button):
            button.setFixedWidth(126)
            button.setMinimumHeight(38)
        self.system_choose_button.clicked.connect(lambda: self._choose_file("system"))
        self.bank_choose_button.clicked.connect(lambda: self._choose_file("bank"))

        self.language_combo = StyledComboBox()
        self.language_combo.setObjectName("compactCombo")
        self.language_combo.addItem("Tiếng Việt", "vi")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("中文简体", "zh")
        self.language_combo.setMaximumWidth(158)
        self.language_combo.setFixedHeight(28)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        self.history_button = QPushButton()
        self.scan_button = QPushButton()
        self.export_button = QPushButton()
        self.attach_statement_checkbox = QCheckBox()
        self.history_button.clicked.connect(self._open_history_dialog)
        self.scan_button.clicked.connect(self._handle_scan_requested)
        self.export_button.clicked.connect(self._export_unmatched)
        self.history_button.setFixedWidth(106)
        self.history_button.setMinimumHeight(36)
        self.scan_button.setFixedWidth(126)
        self.scan_button.setMinimumHeight(38)
        self.export_button.setFixedWidth(106)
        self.export_button.setMinimumHeight(36)
        self.export_button.setEnabled(False)
        self.attach_statement_checkbox.setChecked(False)

        file_layout.addWidget(self.system_file_label, 0, 0)
        file_layout.addWidget(self.system_path_edit, 0, 1)
        file_layout.addWidget(self.system_choose_button, 0, 2)
        file_layout.addWidget(self.bank_file_label, 1, 0)
        file_layout.addWidget(self.bank_path_edit, 1, 1)
        file_layout.addWidget(self.bank_choose_button, 1, 2)
        file_layout.addWidget(self.language_label, 2, 0)
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        controls_row.addWidget(self.language_combo)
        controls_row.addStretch(1)
        controls_row.addWidget(self.scan_button)
        file_layout.addLayout(controls_row, 2, 1, 1, 2)
        self.startup_layout.addWidget(self.file_card, 0, Qt.AlignTop | Qt.AlignLeft)

        self.history_table = QTableWidget(0, 4)
        self.history_table.verticalHeader().hide()
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.NoSelection)
        self.history_table.setShowGrid(False)
        self.history_table.hide()

        self.metadata_card = QFrame()
        self.metadata_card.setObjectName("card")
        self.metadata_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        metadata_layout = QVBoxLayout(self.metadata_card)
        metadata_layout.setContentsMargins(14, 12, 14, 12)
        metadata_layout.setSpacing(8)
        self.metadata_title = QLabel()
        self.metadata_title.setObjectName("sectionTitle")
        metadata_layout.addWidget(self.metadata_title)
        self.metadata_grid = QGridLayout()
        self.metadata_grid.setHorizontalSpacing(8)
        self.metadata_grid.setVerticalSpacing(8)
        for column in range(7):
            self.metadata_grid.setColumnStretch(column, 1)
        metadata_layout.addLayout(self.metadata_grid)

        self.top_layout.addWidget(self.metadata_card, 1, Qt.AlignTop)

        self.metric_titles: dict[str, QLabel] = {}
        self.metric_values: dict[str, QLabel] = {}
        self.metric_cards: dict[str, QWidget] = {}
        self._metric_layouts = {
            "wide": [
                ("meta_bank_name", 0, 0, 1, 2),
                ("meta_account_name", 0, 2, 1, 2),
                ("meta_period", 0, 4, 1, 2),
                ("meta_account_number", 1, 0, 1, 2),
                ("meta_account_type", 1, 2, 1, 1),
                ("meta_currency", 1, 3, 1, 1),
                ("meta_tax_code", 1, 4, 1, 2),
                ("meta_opening_balance", 2, 0, 1, 2),
                ("meta_actual_balance", 2, 2, 1, 2),
                ("meta_closing_balance", 2, 4, 1, 2),
                ("meta_total_debits", 3, 0, 1, 1),
                ("meta_total_credits", 3, 1, 1, 1),
                ("meta_total_fees", 3, 2, 1, 1),
                ("meta_total_vat", 3, 3, 1, 1),
                ("meta_total_debit_tx", 3, 4, 1, 1),
                ("meta_total_credit_tx", 3, 5, 1, 1),
            ],
            "medium": [
                ("meta_bank_name", 0, 0, 1, 2),
                ("meta_account_name", 0, 2, 1, 2),
                ("meta_period", 1, 0, 1, 2),
                ("meta_account_number", 1, 2, 1, 1),
                ("meta_tax_code", 1, 3, 1, 1),
                ("meta_account_type", 2, 0, 1, 1),
                ("meta_currency", 2, 1, 1, 1),
                ("meta_opening_balance", 2, 2, 1, 1),
                ("meta_actual_balance", 2, 3, 1, 1),
                ("meta_closing_balance", 3, 0, 1, 1),
                ("meta_total_debits", 3, 1, 1, 1),
                ("meta_total_credits", 3, 2, 1, 1),
                ("meta_total_fees", 3, 3, 1, 1),
                ("meta_total_vat", 4, 0, 1, 1),
                ("meta_total_debit_tx", 4, 1, 1, 1),
                ("meta_total_credit_tx", 4, 2, 1, 1),
            ],
            "narrow": [
                ("meta_bank_name", 0, 0, 1, 3),
                ("meta_account_name", 1, 0, 1, 3),
                ("meta_period", 2, 0, 1, 2),
                ("meta_currency", 2, 2, 1, 1),
                ("meta_account_number", 3, 0, 1, 1),
                ("meta_account_type", 3, 1, 1, 1),
                ("meta_tax_code", 3, 2, 1, 1),
                ("meta_opening_balance", 4, 0, 1, 1),
                ("meta_actual_balance", 4, 1, 1, 1),
                ("meta_closing_balance", 4, 2, 1, 1),
                ("meta_total_debits", 5, 0, 1, 1),
                ("meta_total_credits", 5, 1, 1, 1),
                ("meta_total_fees", 5, 2, 1, 1),
                ("meta_total_vat", 6, 0, 1, 1),
                ("meta_total_debit_tx", 6, 1, 1, 1),
                ("meta_total_credit_tx", 6, 2, 1, 1),
            ],
            "compact": [
                ("meta_bank_name", 0, 0, 1, 2),
                ("meta_account_name", 1, 0, 1, 2),
                ("meta_period", 2, 0, 1, 2),
                ("meta_account_number", 3, 0, 1, 1),
                ("meta_tax_code", 3, 1, 1, 1),
                ("meta_account_type", 4, 0, 1, 1),
                ("meta_currency", 4, 1, 1, 1),
                ("meta_opening_balance", 5, 0, 1, 1),
                ("meta_actual_balance", 5, 1, 1, 1),
                ("meta_closing_balance", 6, 0, 1, 2),
                ("meta_total_debits", 7, 0, 1, 1),
                ("meta_total_credits", 7, 1, 1, 1),
                ("meta_total_fees", 8, 0, 1, 1),
                ("meta_total_vat", 8, 1, 1, 1),
                ("meta_total_debit_tx", 9, 0, 1, 1),
                ("meta_total_credit_tx", 9, 1, 1, 1),
            ],
        }
        metric_layout = [
            ("meta_bank_name", 0, 0, 1, 2),
            ("meta_account_name", 0, 2, 1, 2),
            ("meta_period", 0, 4, 1, 2),
            ("meta_account_number", 1, 0, 1, 2),
            ("meta_account_type", 1, 2, 1, 1),
            ("meta_currency", 1, 3, 1, 1),
            ("meta_tax_code", 1, 4, 1, 2),
            ("meta_opening_balance", 2, 0, 1, 2),
            ("meta_actual_balance", 2, 2, 1, 2),
            ("meta_closing_balance", 2, 4, 1, 2),
            ("meta_total_debits", 3, 0, 1, 1),
            ("meta_total_credits", 3, 1, 1, 1),
            ("meta_total_fees", 3, 2, 1, 1),
            ("meta_total_vat", 3, 3, 1, 1),
            ("meta_total_debit_tx", 3, 4, 1, 1),
            ("meta_total_credit_tx", 3, 5, 1, 1),
        ]
        for key, row, column, row_span, column_span in metric_layout:
            card, title_label, value_label = self._create_metric_widget()
            self.metric_cards[key] = card
            self.metric_titles[key] = title_label
            self.metric_values[key] = value_label
        self._apply_metadata_layout("wide")

        self.results_card = QFrame()
        self.results_card.setObjectName("resultsCard")
        results_layout = QVBoxLayout(self.results_card)
        results_layout.setContentsMargins(14, 14, 14, 14)
        results_layout.setSpacing(12)
        self.results_title = QLabel()
        self.results_title.setObjectName("sectionTitle")
        results_layout.addWidget(self.results_title)

        self.toolbar_groups_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.toolbar_groups_layout.setSpacing(14)
        results_layout.addLayout(self.toolbar_groups_layout)

        self.status_filter_group = QFrame()
        self.status_filter_group.setObjectName("filterGroup")
        status_group_layout = QHBoxLayout(self.status_filter_group)
        status_group_layout.setContentsMargins(10, 8, 10, 8)
        status_group_layout.setSpacing(8)
        self.status_group_label = QLabel()
        self.status_group_label.setObjectName("filterLabel")
        status_group_layout.addWidget(self.status_group_label)

        self.status_group = QButtonGroup(self)
        self.status_group.setExclusive(True)
        self.status_buttons: dict[str, QPushButton] = {}
        for mode in ("all", "matched_exact", "matched_group", "review", "unmatched"):
            button = QPushButton()
            button.setCheckable(True)
            button.setMinimumHeight(36)
            button.clicked.connect(lambda _checked=False: self._schedule_filters(with_loading=True))
            self.status_group.addButton(button)
            self.status_buttons[mode] = button
            status_group_layout.addWidget(button)
        self.status_buttons["all"].setChecked(True)
        self.toolbar_groups_layout.addWidget(self.status_filter_group)

        self.flow_filter_group = QFrame()
        self.flow_filter_group.setObjectName("filterGroup")
        self.flow_filter_group.setMinimumHeight(54)
        flow_group_layout = QHBoxLayout(self.flow_filter_group)
        flow_group_layout.setContentsMargins(10, 8, 10, 8)
        flow_group_layout.setSpacing(8)
        self.flow_group_label = QLabel()
        self.flow_group_label.setObjectName("filterLabel")
        flow_group_layout.addWidget(self.flow_group_label)

        self.flow_group = QButtonGroup(self)
        self.flow_group.setExclusive(True)
        self.flow_buttons: dict[str, QPushButton] = {}
        for mode in ("all", "income", "expense", "tax"):
            button = QPushButton()
            button.setCheckable(True)
            button.setMinimumHeight(36)
            button.clicked.connect(lambda _checked=False: self._schedule_filters(with_loading=True))
            self.flow_group.addButton(button)
            self.flow_buttons[mode] = button
            flow_group_layout.addWidget(button)
        self.flow_buttons["all"].setChecked(True)
        self.toolbar_groups_layout.addWidget(self.flow_filter_group)

        self.filter_controls_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.filter_controls_layout.setSpacing(14)
        results_layout.addLayout(self.filter_controls_layout)
        self.date_filter_label = QLabel()
        self.date_filter_label.setObjectName("filterLabel")
        self.date_range_separator = QLabel("~")
        self.date_range_separator.setObjectName("filterLabel")
        self.date_from_edit = PopupDateEdit()
        self.date_to_edit = PopupDateEdit()
        self.reference_filter_combo = StyledComboBox()
        self.reference_filter_combo.setMinimumWidth(220)
        self.reference_filter_combo.setMinimumHeight(36)
        self.reference_filter_combo.currentIndexChanged.connect(lambda _index: self._schedule_filters(with_loading=True))
        self.date_clear_button = QPushButton()
        self.date_clear_button.setMinimumHeight(36)
        self.date_clear_button.setFixedWidth(116)
        self.quick_search_edit = QLineEdit()
        self.quick_search_edit.setClearButtonEnabled(True)
        self.quick_search_edit.setMinimumHeight(36)
        self.quick_search_edit.setMinimumWidth(260)
        self.quick_search_edit.textChanged.connect(self._sync_quick_search)
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setMinimumHeight(36)
            widget.setFixedWidth(132)
            widget.dateChanged.connect(self._on_date_filter_changed)
        self.date_clear_button.clicked.connect(self._reset_date_filter)
        self.reference_filter_group = QFrame()
        self.reference_filter_group.setObjectName("filterGroup")
        reference_group_layout = QHBoxLayout(self.reference_filter_group)
        reference_group_layout.setContentsMargins(10, 8, 10, 8)
        reference_group_layout.setSpacing(8)
        reference_group_layout.addWidget(self.reference_filter_label)
        reference_group_layout.addWidget(self.reference_filter_combo)

        self.date_filter_group = QFrame()
        self.date_filter_group.setObjectName("filterGroup")
        date_group_layout = QHBoxLayout(self.date_filter_group)
        date_group_layout.setContentsMargins(10, 8, 10, 8)
        date_group_layout.setSpacing(8)
        date_group_layout.addWidget(self.date_filter_label)
        date_group_layout.addWidget(self.date_from_edit)
        date_group_layout.addWidget(self.date_range_separator)
        date_group_layout.addWidget(self.date_to_edit)
        date_group_layout.addWidget(self.date_clear_button)

        self.quick_search_group = QFrame()
        self.quick_search_group.setObjectName("filterGroup")
        quick_search_layout = QHBoxLayout(self.quick_search_group)
        quick_search_layout.setContentsMargins(10, 8, 10, 8)
        quick_search_layout.setSpacing(8)
        quick_search_layout.addWidget(self.quick_search_edit)

        self.filter_controls_layout.addWidget(self.reference_filter_group)
        self.filter_controls_layout.addWidget(self.date_filter_group)
        self.filter_controls_layout.addWidget(self.quick_search_group, 1)

        self.summary_row_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.summary_row_layout.setSpacing(8)
        results_layout.addLayout(self.summary_row_layout)
        self.summary_group = QFrame()
        self.summary_group.setObjectName("summaryGroup")
        self.summary_group.setMinimumWidth(0)
        self.summary_group.setMinimumHeight(54)
        self.summary_group.setMaximumWidth(16777215)
        self.summary_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        summary_group_layout = QHBoxLayout(self.summary_group)
        summary_group_layout.setContentsMargins(10, 8, 10, 8)
        summary_group_layout.setSpacing(8)
        self.summary_grid_label = QLabel()
        self.summary_grid_label.setObjectName("summaryGridLabel")
        summary_group_layout.addWidget(self.summary_grid_label)
        self.summary_buttons_widget = QWidget(self.summary_group)
        self.summary_buttons_widget.setObjectName("summaryButtons")
        self.summary_buttons_widget.setMinimumHeight(36)
        self.summary_buttons_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.summary_buttons_layout = QGridLayout(self.summary_buttons_widget)
        self.summary_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_buttons_layout.setHorizontalSpacing(8)
        self.summary_buttons_layout.setVerticalSpacing(6)
        self.summary_filter_group = QButtonGroup(self)
        self.summary_filter_group.setExclusive(True)
        self.summary_filter_buttons: dict[str, QPushButton] = {}
        summary_button_specs = (
            ("all", "summaryChipAll"),
            ("matched_exact", "summaryChipExact"),
            ("matched_group", "summaryChipGroup"),
            ("review", "summaryChipReview"),
            ("unmatched", "summaryChipUnmatched"),
        )
        for mode, object_name in summary_button_specs:
            button = QPushButton()
            button.setObjectName(object_name)
            button.setCheckable(True)
            button.setAutoDefault(False)
            button.setDefault(False)
            button.setFixedHeight(36)
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            button.setFocusPolicy(Qt.NoFocus)
            button.clicked.connect(lambda _checked=False: self._schedule_filters(with_loading=True))
            self.summary_filter_group.addButton(button)
            self.summary_filter_buttons[mode] = button
        self.summary_filter_buttons["all"].setChecked(True)
        self.summary_help_button = InstantToolTipButton()
        self.summary_help_button.setObjectName("summaryHelpButton")
        self.summary_help_button.setText("!")
        self.summary_help_button.setCursor(Qt.PointingHandCursor)
        self.summary_help_button.setAutoRaise(True)
        summary_group_layout.addWidget(self.summary_buttons_widget, 1)
        self._reflow_summary_buttons()
        self.toolbar_groups_layout.insertWidget(0, self.summary_group, 3)
        self.toolbar_groups_layout.addStretch(1)
        self.summary_actions = QFrame()
        self.summary_actions.setObjectName("summaryActions")
        self.summary_actions.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        summary_actions_layout = QHBoxLayout(self.summary_actions)
        summary_actions_layout.setContentsMargins(10, 6, 10, 6)
        summary_actions_layout.setSpacing(10)
        summary_actions_layout.addWidget(self.history_button)
        summary_actions_layout.addWidget(self.export_button)
        summary_actions_layout.addWidget(self.attach_statement_checkbox)
        self.swap_button = QPushButton()
        self.swap_button.setFixedWidth(148)
        self.swap_button.setMinimumHeight(36)
        self.swap_button.clicked.connect(self._swap_grids)
        summary_actions_layout.addStretch(1)
        self.summary_row_layout.addWidget(self.summary_actions, 1)
        self.summary_row_layout.addWidget(self.swap_button)

        self.locked_label = QLabel()
        self.locked_label.setObjectName("lockedLabel")
        results_layout.addWidget(self.locked_label)

        self.results_content = QWidget()
        self.results_content.setObjectName("resultsContent")
        content_layout = QVBoxLayout(self.results_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self.grid_stack = QStackedWidget(self.results_content)
        self.grid_stack.setObjectName("gridStack")
        self.grid_stack.setMinimumHeight(360)
        self.grid_stack.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        content_layout.addWidget(self.grid_stack, 0, Qt.AlignTop)
        content_layout.addStretch(1)
        results_layout.addWidget(self.results_content)
        root.addWidget(self.results_card)

        self.system_grid = self._create_grid_panel()
        self.bank_grid = self._create_grid_panel()
        self.system_page = self._wrap_grid_panel(self.system_grid.container)
        self.bank_page = self._wrap_grid_panel(self.bank_grid.container)
        self.grid_stack.addWidget(self.system_page)
        self.grid_stack.addWidget(self.bank_page)
        self.grid_stack.setCurrentWidget(self.bank_page)

        self.system_grid.table.action_requested.connect(lambda row: self._open_pair("system", row))
        self.bank_grid.table.action_requested.connect(lambda row: self._open_pair("bank", row))
        self.system_grid.search.textChanged.connect(self._filter_system_grid)
        self.bank_grid.search.textChanged.connect(self._filter_bank_grid)
        self.system_grid.columns.currentIndexChanged.connect(self._filter_system_grid)
        self.bank_grid.columns.currentIndexChanged.connect(self._filter_bank_grid)
        self.system_grid.search.hide()
        self.bank_grid.search.hide()

        self.overlay = LoadingOverlay(central)
        self.overlay.bind_parent()
        self.overlay.set_blur_targets([self.page_stack])
        self.page_stack.setCurrentWidget(self.startup_page)
        self._apply_responsive_layouts()

    def _create_grid_panel(self) -> GridWidgets:
        container = QFrame()
        container.setObjectName("panelCard")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_label = QLabel()
        title_label.setObjectName("sectionTitle")
        count_label = QLabel()
        count_label.setObjectName("countLabel")
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(count_label)

        filter_row = QHBoxLayout()
        columns_combo = StyledComboBox()
        columns_combo.setMinimumWidth(188)
        columns_combo.setMinimumHeight(36)
        columns_combo.hide()
        search_edit = QLineEdit()
        search_edit.setClearButtonEnabled(True)
        search_edit.setMinimumHeight(36)
        filter_row.addWidget(search_edit, 1)

        table = FrozenTableView()
        table.setSortingEnabled(True)
        table.setSelectionBehavior(FrozenTableView.SelectRows)
        table.setSelectionMode(FrozenTableView.SingleSelection)
        table.setMinimumHeight(280)

        layout.addLayout(title_row)
        layout.addLayout(filter_row)
        layout.addWidget(table)
        return GridWidgets(title_label, count_label, search_edit, columns_combo, table, container)

    def _wrap_grid_panel(self, panel: QWidget) -> QWidget:
        page = QWidget()
        page.setObjectName("gridPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(panel, 0, Qt.AlignTop)
        layout.addStretch(1)
        return page

    def _create_metric_widget(self) -> tuple[QWidget, QLabel, QLabel]:
        frame = QFrame()
        frame.setObjectName("metricCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(1)
        title = QLabel()
        title.setObjectName("metricTitle")
        value = QLabel("-")
        value.setObjectName("metricValue")
        value.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(value)
        return frame, title, value

    def _apply_metadata_layout(self, mode: str) -> None:
        if self._metadata_layout_mode == mode:
            return
        while self.metadata_grid.count():
            item = self.metadata_grid.takeAt(0)
            if widget := item.widget():
                widget.hide()
        specs = self._metric_layouts.get(mode, self._metric_layouts["wide"])
        max_column = max((column + span) for _, _, column, _, span in specs)
        for column in range(7):
            self.metadata_grid.setColumnStretch(column, 1 if column < max_column else 0)
            self.metadata_grid.setColumnMinimumWidth(column, 0)
        for key, row, column, row_span, column_span in specs:
            card = self.metric_cards[key]
            self.metadata_grid.addWidget(card, row, column, row_span, column_span)
            card.show()
        self._metadata_layout_mode = mode

    def _grid_area_min_height(self) -> int:
        return 360

    def _grid_panel_extra_height(self, grid: GridWidgets) -> int:
        title_height = max(grid.title.sizeHint().height(), grid.count.sizeHint().height(), 22)
        filter_height = grid.search.sizeHint().height() if grid.search.isVisible() else 0
        return 24 + title_height + filter_height + 24

    def _table_target_height(self, table: FrozenTableView, visible_rows: int) -> int:
        rows_to_show = max(1, min(visible_rows, 25))
        header_height = max(table.horizontalHeader().height(), table.horizontalHeader().sizeHint().height(), 28)
        row_height = table.rowHeight(0) if visible_rows > 0 else table.verticalHeader().defaultSectionSize()
        row_height = max(row_height, 24)
        horizontal_scroll_height = table.horizontalScrollBar().sizeHint().height() + 4
        frame_height = table.frameWidth() * 2
        return header_height + (rows_to_show * row_height) + horizontal_scroll_height + frame_height + 4

    def _update_grid_heights(self) -> None:
        grids = (
            ("system", self.system_grid, self.system_proxy),
            ("bank", self.bank_grid, self.bank_proxy),
        )
        heights: dict[str, int] = {}
        for mode, grid, proxy in grids:
            visible_rows = proxy.rowCount() if proxy else 0
            table_height = self._table_target_height(grid.table, visible_rows)
            panel_height = table_height + self._grid_panel_extra_height(grid)
            grid.table.setMinimumHeight(table_height)
            grid.table.setMaximumHeight(table_height)
            grid.container.setMinimumHeight(panel_height)
            grid.container.setMaximumHeight(panel_height)
            heights[mode] = panel_height
        active_height = heights.get(self._active_grid_mode, self._grid_area_min_height())
        self.grid_stack.setMinimumHeight(active_height)
        self.grid_stack.setMaximumHeight(active_height)

    def _reflow_summary_buttons(self) -> None:
        while self.summary_buttons_layout.count():
            item = self.summary_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self.summary_buttons_layout.removeWidget(widget)

        width = self.width()
        if width < 900:
            columns = 2
        elif width < 1250:
            columns = 3
        else:
            columns = 6

        ordered_widgets = [
            self.summary_filter_buttons["all"],
            self.summary_filter_buttons["matched_exact"],
            self.summary_filter_buttons["matched_group"],
            self.summary_filter_buttons["review"],
            self.summary_filter_buttons["unmatched"],
            self.summary_help_button,
        ]
        for index, widget in enumerate(ordered_widgets):
            row = index // columns
            column = index % columns
            self.summary_buttons_layout.addWidget(widget, row, column)
        for column in range(columns):
            self.summary_buttons_layout.setColumnStretch(column, 0)
        self.summary_buttons_layout.setColumnStretch(columns, 1)

    def _apply_responsive_layouts(self) -> None:
        width = self.width()
        if self.page_stack.currentWidget() is self.startup_page:
            self.file_card.setMaximumWidth(450)
            self.file_card.setMinimumWidth(0)
            self.system_path_edit.setMaximumWidth(200)
            self.bank_path_edit.setMaximumWidth(200)
            return

        if width < 1180:
            self.root_layout.setContentsMargins(12, 12, 12, 12)
        else:
            self.root_layout.setContentsMargins(18, 18, 18, 18)
        self.root_layout.setSpacing(14)

        self.top_layout.setDirection(QBoxLayout.LeftToRight)
        self.system_path_edit.setMaximumWidth(16777215)
        self.bank_path_edit.setMaximumWidth(16777215)

        if width < 860:
            self._apply_metadata_layout("compact")
        elif width < 1120:
            self._apply_metadata_layout("narrow")
        elif width < 1480:
            self._apply_metadata_layout("medium")
        else:
            self._apply_metadata_layout("wide")

        self.summary_row_layout.setDirection(QBoxLayout.TopToBottom if width < 1120 else QBoxLayout.LeftToRight)
        self.summary_group.setMinimumWidth(0)
        self.summary_group.setMaximumWidth(16777215)
        self.toolbar_groups_layout.setDirection(QBoxLayout.TopToBottom if width < 1320 else QBoxLayout.LeftToRight)
        self.filter_controls_layout.setDirection(QBoxLayout.TopToBottom if width < 1320 else QBoxLayout.LeftToRight)
        self._reflow_summary_buttons()
        self._update_grid_heights()

    def _show_startup_page(self) -> None:
        self._initial_compact_size_applied = False
        self.page_stack.setCurrentWidget(self.startup_page)
        self._apply_initial_compact_size()

    def _show_results_page(self) -> None:
        self.page_stack.setCurrentWidget(self.results_page)
        self._apply_responsive_layouts()
        self._ensure_results_window_size()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layouts()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #eef3f9;
                color: #18212f;
                font-family: "Segoe UI", "Microsoft YaHei UI";
                font-size: 13px;
            }
            QMainWindow {
                background: #eef3f9;
            }
            QLabel,
            QCheckBox {
                background: transparent;
            }
            QCheckBox {
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #94a3b8;
                border-radius: 4px;
                background: #ffffff;
            }
            QCheckBox::indicator:hover {
                border-color: #60a5fa;
            }
            QCheckBox::indicator:checked {
                border-color: #3b82f6;
                background: #dbeafe;
            }
            QScrollArea {
                border: none;
                background: #eef3f9;
            }
            QWidget#resultsContent,
            QWidget#gridPage,
            QStackedWidget#gridStack {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 14px;
                margin: 6px 3px 6px 0;
            }
            QScrollBar::handle:vertical {
                background: #c9d6e8;
                border: 1px solid #b8c7dc;
                border-radius: 6px;
                min-height: 36px;
            }
            QScrollBar::handle:vertical:hover {
                background: #b4c7e0;
                border-color: #9cb3d3;
            }
            QScrollBar::handle:vertical:pressed {
                background: #94add0;
                border-color: #7f9bc3;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: transparent;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: rgba(148, 163, 184, 0.12);
                border-radius: 6px;
            }
            QScrollBar:horizontal {
                background: transparent;
                height: 14px;
                margin: 0 6px 3px 6px;
            }
            QScrollBar::handle:horizontal {
                background: #c9d6e8;
                border: 1px solid #b8c7dc;
                border-radius: 6px;
                min-width: 40px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #b4c7e0;
                border-color: #9cb3d3;
            }
            QScrollBar::handle:horizontal:pressed {
                background: #94add0;
                border-color: #7f9bc3;
            }
            QScrollBar::add-line:horizontal,
            QScrollBar::sub-line:horizontal {
                width: 0px;
                border: none;
                background: transparent;
            }
            QScrollBar::add-page:horizontal,
            QScrollBar::sub-page:horizontal {
                background: rgba(148, 163, 184, 0.12);
                border-radius: 6px;
            }
            QWidget#loadingOverlay {
                background: rgba(107, 114, 128, 132);
            }
            QFrame#card, QFrame#resultsCard, QFrame#panelCard, QFrame#metricCard {
                background: #ffffff;
                border: 1px solid #dbe4f0;
                border-radius: 16px;
            }
            QFrame#loadingCard {
                background: #ffffff;
                border: 1px solid #d1d5db;
                border-radius: 18px;
            }
            QFrame#filterGroup {
                background: #f7faff;
                border: 1px solid #dbe4f0;
                border-radius: 12px;
            }
            QFrame#summaryActions {
                background: #f7faff;
                border: 1px solid #dbe4f0;
                border-radius: 12px;
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
            QLabel#filterLabel {
                color: #64748b;
                font-size: 12px;
                font-weight: 600;
            }
            QLabel#summaryLabel {
                font-weight: 600;
                color: #1f2937;
            }
            QFrame#summaryGroup {
                background: #f7faff;
                border: 1px solid #dbe4f0;
                border-radius: 12px;
            }
            QWidget#summaryButtons {
                background: transparent;
                border: none;
            }
            QLabel#summaryGridLabel {
                font-size: 12px;
                font-weight: 700;
                color: #0f172a;
                padding-right: 2px;
            }
            QPushButton#summaryChipAll,
            QPushButton#summaryChipExact,
            QPushButton#summaryChipGroup,
            QPushButton#summaryChipReview,
            QPushButton#summaryChipUnmatched {
                font-size: 11px;
                font-weight: 700;
                min-height: 0px;
                max-height: 36px;
                min-width: 72px;
                border-radius: 14px;
                padding: 0 12px;
                border-width: 1px;
                border-style: solid;
            }
            QPushButton#summaryChipAll {
                background: #eff4fb;
                border-color: #d7e1ef;
                color: #475569;
            }
            QPushButton#summaryChipExact {
                background: #dcfce7;
                border-color: #bbf7d0;
                color: #166534;
            }
            QPushButton#summaryChipGroup {
                background: #dbeafe;
                border-color: #bfdbfe;
                color: #1d4ed8;
            }
            QPushButton#summaryChipReview {
                background: #fef3c7;
                border-color: #fde68a;
                color: #92400e;
            }
            QPushButton#summaryChipUnmatched {
                background: #fecdd3;
                border-color: #fda4af;
                color: #be123c;
            }
            QPushButton#summaryChipAll:checked,
            QPushButton#summaryChipExact:checked,
            QPushButton#summaryChipGroup:checked,
            QPushButton#summaryChipReview:checked,
            QPushButton#summaryChipUnmatched:checked {
                border-color: #3b82f6;
            }
            QPushButton#summaryChipAll:hover,
            QPushButton#summaryChipExact:hover,
            QPushButton#summaryChipGroup:hover,
            QPushButton#summaryChipReview:hover,
            QPushButton#summaryChipUnmatched:hover {
                border-color: #60a5fa;
            }
            QPushButton#summaryChipAll:focus,
            QPushButton#summaryChipExact:focus,
            QPushButton#summaryChipGroup:focus,
            QPushButton#summaryChipReview:focus,
            QPushButton#summaryChipUnmatched:focus {
                outline: none;
            }
            QFrame#resultsCard QLabel#sectionTitle,
            QFrame#panelCard QLabel#sectionTitle {
                font-size: 14px;
            }
            QFrame#resultsCard QLabel#summaryLabel {
                font-size: 12px;
            }
            QFrame#resultsCard QLabel#summaryGridLabel {
                font-size: 12px;
            }
            QFrame#resultsCard QPushButton#summaryChipAll,
            QFrame#resultsCard QPushButton#summaryChipExact,
            QFrame#resultsCard QPushButton#summaryChipGroup,
            QFrame#resultsCard QPushButton#summaryChipReview,
            QFrame#resultsCard QPushButton#summaryChipUnmatched {
                font-size: 11px;
            }
            QFrame#resultsCard QLabel#countLabel,
            QFrame#resultsCard QLabel#filterLabel,
            QFrame#panelCard QLabel#countLabel {
                font-size: 10px;
            }
            QLabel#countLabel, QLabel#metricTitle {
                color: #64748b;
                font-size: 11px;
            }
            QLabel#metricValue {
                font-size: 12px;
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
            QLabel#loadingSpinner {
                font-size: 30px;
                font-weight: 700;
                color: #374151;
            }
            QLabel#loadingLabel {
                font-size: 18px;
                font-weight: 700;
                color: #111827;
            }
            QLineEdit, QComboBox, QDateEdit, QTableWidget, QTableView, QTextBrowser {
                background: #ffffff;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 5px 10px;
            }
            QComboBox, QDateEdit {
                min-height: 34px;
                padding-right: 34px;
            }
            QComboBox#compactCombo {
                min-height: 28px;
                max-height: 28px;
                padding-top: 1px;
                padding-bottom: 1px;
            }
            QComboBox:focus,
            QComboBox:on {
                outline: none;
                border: 1px solid #cbd5e1;
            }
            QFrame#resultsCard QLineEdit,
            QFrame#resultsCard QComboBox,
            QFrame#resultsCard QDateEdit,
            QFrame#resultsCard QPushButton,
            QFrame#panelCard QLineEdit,
            QFrame#panelCard QComboBox,
            QFrame#panelCard QPushButton {
                font-size: 12px;
            }
            QFrame#resultsCard QLineEdit,
            QFrame#resultsCard QComboBox,
            QFrame#resultsCard QDateEdit,
            QFrame#panelCard QLineEdit,
            QFrame#panelCard QComboBox {
                padding: 4px 8px;
            }
            QFrame#resultsCard QComboBox,
            QFrame#resultsCard QDateEdit {
                min-height: 28px;
                padding-top: 2px;
                padding-bottom: 2px;
            }
            QFrame#resultsCard QPushButton,
            QFrame#panelCard QPushButton {
                padding: 6px 12px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 32px;
                border: none;
                border-left: 1px solid #dbe4f0;
                background: #f3f7fc;
                border-top-right-radius: 10px;
                border-bottom-right-radius: 10px;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QDateEdit::drop-down {
                border: none;
                width: 28px;
            }
            QComboBox QAbstractItemView {
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                background: #ffffff;
                selection-background-color: #dbeafe;
                selection-color: #0f172a;
                outline: 0;
                padding: 4px;
            }
            QComboBox QAbstractItemView::item {
                min-height: 28px;
                padding: 6px 10px;
                margin: 1px 2px;
                border-radius: 8px;
            }
            QComboBox QAbstractItemView::item:hover {
                background: #eff6ff;
            }
            QComboBox QAbstractItemView::item:selected {
                background: #dbeafe;
                color: #1d4ed8;
            }
            QListView#comboPopup {
                outline: none;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                background: #ffffff;
                padding: 4px;
            }
            QFrame#comboPopupContainer {
                border: none;
                background: transparent;
            }
            QListView#comboPopup:focus {
                outline: none;
                border: 1px solid #cbd5e1;
            }
            QListView#comboPopup::item {
                min-height: 28px;
                padding: 6px 10px;
                margin: 1px 2px;
                border-radius: 8px;
            }
            QListView#comboPopup::item:hover {
                background: #eff6ff;
            }
            QListView#comboPopup::item:selected {
                background: #dbeafe;
                color: #1d4ed8;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #f8fafc;
            }
            QCalendarWidget QTableView {
                background: #ffffff;
                border: 1px solid #dbe4f0;
                border-top: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
                padding: 4px;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background: #f8fbff;
                border: 1px solid #dbe4f0;
                border-bottom: none;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                min-height: 34px;
            }
            QCalendarWidget QToolButton {
                color: #0f172a;
                font-weight: 600;
                background: transparent;
                border: none;
                margin: 4px 2px;
                padding: 4px 8px;
            }
            QCalendarWidget QToolButton:hover {
                background: #eaf2ff;
                border-radius: 8px;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }
            QCalendarWidget QMenu {
                width: 140px;
                left: 18px;
            }
            QCalendarWidget QSpinBox {
                width: 72px;
                font-weight: 600;
            }
            QCalendarWidget QHeaderView::section {
                background: #f8fbff;
                color: #475569;
                border: none;
                border-bottom: 1px solid #dbe4f0;
                padding: 6px 4px;
                font-size: 11px;
                font-weight: 700;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #18212f;
                selection-background-color: #dbeafe;
                selection-color: #1d4ed8;
            }
            QPushButton {
                background: #e2e8f0;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                padding: 7px 14px;
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
            QPushButton#summaryChipAll,
            QPushButton#summaryChipExact,
            QPushButton#summaryChipGroup,
            QPushButton#summaryChipReview,
            QPushButton#summaryChipUnmatched {
                border-width: 1px;
                border-style: solid;
                border-radius: 14px;
                padding: 4px 12px;
            }
            QPushButton#summaryChipAll:checked,
            QPushButton#summaryChipExact:checked,
            QPushButton#summaryChipGroup:checked,
            QPushButton#summaryChipReview:checked,
            QPushButton#summaryChipUnmatched:checked,
            QPushButton#summaryChipAll:pressed,
            QPushButton#summaryChipExact:pressed,
            QPushButton#summaryChipGroup:pressed,
            QPushButton#summaryChipReview:pressed,
            QPushButton#summaryChipUnmatched:pressed,
            QPushButton#summaryChipAll:checked:hover,
            QPushButton#summaryChipExact:checked:hover,
            QPushButton#summaryChipGroup:checked:hover,
            QPushButton#summaryChipReview:checked:hover,
            QPushButton#summaryChipUnmatched:checked:hover {
                border: 1px solid #3b82f6;
            }
            QPushButton#summaryChipAll:focus,
            QPushButton#summaryChipExact:focus,
            QPushButton#summaryChipGroup:focus,
            QPushButton#summaryChipReview:focus,
            QPushButton#summaryChipUnmatched:focus {
                border-width: 1px;
                border-style: solid;
                outline: none;
            }
            QToolButton {
                background: transparent;
                border: none;
                color: #2563eb;
                font-weight: 600;
                padding: 2px 0;
            }
            QToolButton:hover {
                color: #1d4ed8;
            }
            QToolButton#summaryHelpButton {
                background: #eef2ff;
                border: 1px solid #c7d2fe;
                border-radius: 9px;
                color: #4338ca;
                font-size: 11px;
                font-weight: 800;
                min-width: 18px;
                max-width: 18px;
                min-height: 18px;
                max-height: 18px;
                padding: 0;
            }
            QToolButton#summaryHelpButton:hover {
                background: #dbeafe;
                border-color: #93c5fd;
                color: #1d4ed8;
            }
            QToolTip {
                background: #111827;
                color: white;
                border: 1px solid #1f2937;
                border-radius: 8px;
                padding: 8px 10px;
            }
            QHeaderView::section {
                background: #e8f0fa;
                border: none;
                border-bottom: 1px solid #dbe4f0;
                border-right: 1px solid #d5dfec;
                padding: 8px;
                font-weight: 700;
            }
            QTableCornerButton::section {
                background: #e8f0fa;
                border: none;
                border-bottom: 1px solid #dbe4f0;
                border-right: 1px solid #d5dfec;
            }
            QFrame#resultsCard QHeaderView::section,
            QFrame#panelCard QHeaderView::section {
                font-size: 11px;
                padding: 6px 7px;
            }
            QTableView {
                background: #ffffff;
                gridline-color: #e5e7eb;
                selection-background-color: #bfdbfe;
                selection-color: #18212f;
                alternate-background-color: #f8fafc;
                border: none;
                outline: 0;
            }
            QFrame#resultsCard QTableView,
            QFrame#panelCard QTableView {
                font-size: 11px;
            }
            QTableView::item {
                padding: 4px;
            }
            QFrame#resultsCard QTableView::item,
            QFrame#panelCard QTableView::item {
                padding: 2px 4px;
            }
            QTableView::item:selected {
                color: #18212f;
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
        self.history_button.setText(tr(self.current_language, "history_button"))
        self.reference_filter_label.setText(tr(self.current_language, "reference_filter"))
        self.date_filter_label.setText(self._date_filter_text("caption"))
        self.date_range_separator.setText("~")
        self.system_choose_button.setText(tr(self.current_language, "choose_file"))
        self.bank_choose_button.setText(tr(self.current_language, "choose_file"))
        self.scan_button.setText(tr(self.current_language, "scan"))
        self.export_button.setText(self._export_button_label())
        self.attach_statement_checkbox.setText(tr(self.current_language, "attach_statement"))
        self.date_clear_button.setText(self._date_filter_text("reset"))
        self.quick_search_edit.setPlaceholderText(self._quick_search_placeholder())
        self.metadata_title.setText(tr(self.current_language, "bank_info"))
        self.results_title.setText(tr(self.current_language, "results"))
        self.locked_label.setText(tr(self.current_language, "results_locked"))
        self.status_group_label.setText(tr(self.current_language, "status_filter_title"))
        self.flow_group_label.setText(tr(self.current_language, "flow_filter_title"))
        self._update_grid_toggle_button()
        self.status_buttons["all"].setText(tr(self.current_language, "status_all"))
        self.status_buttons["matched_exact"].setText(tr(self.current_language, "status_matched_exact"))
        self.status_buttons["matched_group"].setText(tr(self.current_language, "status_matched_group"))
        self.status_buttons["review"].setText(tr(self.current_language, "status_review"))
        self.status_buttons["unmatched"].setText(tr(self.current_language, "status_unmatched"))
        self.flow_buttons["all"].setText(tr(self.current_language, "flow_all"))
        self.flow_buttons["income"].setText(tr(self.current_language, "flow_income"))
        self.flow_buttons["expense"].setText(tr(self.current_language, "flow_expense"))
        self.flow_buttons["tax"].setText(tr(self.current_language, "flow_tax"))
        self.system_grid.title.setText(tr(self.current_language, "system_grid"))
        self.bank_grid.title.setText(tr(self.current_language, "bank_grid"))
        self.summary_help_button.setToolTip(self._summary_help_tooltip())
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
        if self.system_model and self.bank_model:
            self._apply_grid_column_widths()
        self._update_summary()
        self._update_row_counts()
        self._apply_responsive_layouts()

    def _summary_help_tooltip(self) -> str:
        texts = {
            "vi": (
                "<b>Giải thích trạng thái</b><br>"
                "Khớp lẻ: 1 giao dịch hệ thống khớp 1 giao dịch sao kê.<br>"
                "Phí/VAT đã khớp: chỉ áp dụng cho các dòng phí/VAT từ sao kê được gom về 1 dòng hệ thống.<br>"
                "Cần kiểm tra: tool có ứng viên hợp lý nhưng chưa đủ an toàn để chốt.<br>"
                "Chưa khớp: chưa tìm được đối ứng phù hợp, hoặc thuộc ca n-n không tự ghép."
            ),
            "en": (
                "<b>Status meaning</b><br>"
                "Exact matched: one system row matches one statement row.<br>"
                "Fee/VAT matched: statement fee/VAT rows that were merged into one system row.<br>"
                "Needs review: the tool found a plausible candidate but not enough proof.<br>"
                "Unmatched: no safe counterpart was found, including n-n cases."
            ),
            "zh": (
                "<b>状态说明</b><br>"
                "单笔已匹配：系统与流水 1 对 1 对应。<br>"
                "费用/VAT 已匹配：仅显示流水费用/VAT 汇总到 1 条系统记录的情况。<br>"
                "需要复核：存在合理候选，但证据不足。<br>"
                "未匹配：尚未找到安全的对应交易，n-n 默认也归入此类。"
            ),
        }
        return texts.get(self.current_language, texts["vi"])

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
        file_name = Path(file_path).name
        if file_type == "system":
            self._selected_system_path = file_path
            self.system_path_edit.setText(file_name)
            self.system_path_edit.setToolTip(file_path)
        else:
            self._selected_bank_path = file_path
            self.bank_path_edit.setText(file_name)
            self.bank_path_edit.setToolTip(file_path)
        logger.info("Đã chọn file %s: %s", file_type, file_path)

    def _on_language_changed(self) -> None:
        self.current_language = self.language_combo.currentData()
        self._apply_language()
        logger.info("Đã đổi ngôn ngữ giao diện sang %s", self.current_language)

    def _apply_initial_compact_size(self) -> None:
        if self._initial_compact_size_applied or self.current_result is not None:
            return
        self.startup_layout.setContentsMargins(18, 18, 18, 18)
        self.startup_layout.setSpacing(0)
        self.file_card.setMaximumWidth(450)
        self.file_card.setMinimumWidth(0)
        self.system_path_edit.setMaximumWidth(200)
        self.bank_path_edit.setMaximumWidth(200)
        self.file_card.updateGeometry()
        self.startup_page.adjustSize()
        self.page_stack.adjustSize()
        self.adjustSize()
        target_size = self.startup_page.sizeHint()
        self._set_compact_window_mode(True)
        self.setFixedSize(target_size)
        self._initial_compact_size_applied = True

    def _ensure_results_window_size(self) -> None:
        self._set_compact_window_mode(False)
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.system_path_edit.setMaximumWidth(16777215)
        self.bank_path_edit.setMaximumWidth(16777215)
        if self.width() < self._expanded_window_size.width() or self.height() < self._expanded_window_size.height():
            self.resize(self._expanded_window_size)

    def _set_compact_window_mode(self, enabled: bool) -> None:
        if self._compact_window_mode == enabled:
            return
        self._compact_window_mode = enabled
        was_visible = self.isVisible()
        position = self.pos()
        self.setWindowFlag(Qt.WindowMaximizeButtonHint, not enabled)
        if was_visible:
            if not enabled:
                self.showNormal()
            self.show()
            self.move(position)

    def _update_locked_state(self, locked: bool) -> None:
        has_result = self.current_result is not None
        self.top_section.setVisible(has_result)
        self.metadata_card.setVisible(has_result)
        self.results_card.setVisible(has_result)
        self.results_content.setEnabled(not locked)
        self.results_content.setVisible(has_result)
        self.locked_label.setVisible(False)
        self.status_filter_group.setVisible(False)
        self.flow_filter_group.setVisible(has_result)
        self.reference_filter_group.setVisible(has_result)
        self.date_filter_group.setVisible(has_result)
        self.quick_search_group.setVisible(has_result)
        self.summary_group.setVisible(has_result)
        self.summary_actions.setVisible(has_result)
        self.swap_button.setVisible(has_result)
        self.export_button.setEnabled(not locked and has_result)
        for card in self.metric_cards.values():
            card.setVisible(has_result)
        self.metadata_card.setEnabled(has_result)
        self.results_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.results_card.setMaximumHeight(16777215)
        self.metadata_card.setMaximumHeight(16777215)
        self.swap_button.setEnabled(not locked and has_result)
        self.reference_filter_combo.setEnabled(not locked)
        self.date_from_edit.setEnabled(not locked and has_result)
        self.date_to_edit.setEnabled(not locked and has_result)
        self.date_clear_button.setEnabled(not locked and has_result)
        for button in self.status_buttons.values():
            button.setEnabled(not locked)
        for button in self.summary_filter_buttons.values():
            button.setEnabled(not locked)
        for button in self.flow_buttons.values():
            button.setEnabled(not locked)
        self._update_export_controls_state(locked)
        self.results_card.updateGeometry()
        self.metadata_card.updateGeometry()
        self.top_section.updateGeometry()

    def _update_export_controls_state(self, locked: bool) -> None:
        has_result = self.current_result is not None
        allow_attach_statement = not locked and has_result
        self.attach_statement_checkbox.setEnabled(allow_attach_statement)

    def _validate_selected_files(self, system_path: str, bank_path: str) -> str | None:
        system_kind, system_reason = detect_excel_file_kind(system_path)
        bank_kind, bank_reason = detect_excel_file_kind(bank_path)
        logger.info(
            "Kiem tra file truoc khi do. system_kind=%s | bank_kind=%s | system_reason=%s | bank_reason=%s",
            system_kind,
            bank_kind,
            system_reason,
            bank_reason,
        )
        system_name = Path(system_path).name
        bank_name = Path(bank_path).name

        if system_kind == "bank" and bank_kind == "system":
            return self._file_validation_text("swapped", system_name=system_name, bank_name=bank_name)
        if system_kind == "bank":
            return self._file_validation_text("system_is_bank", name=system_name)
        if system_kind != "system":
            return self._file_validation_text("invalid_system", name=system_name)
        if bank_kind == "system":
            return self._file_validation_text("bank_is_system", name=bank_name)
        if bank_kind != "bank":
            return self._file_validation_text("invalid_bank", name=bank_name)
        return None

    def _file_validation_text(self, key: str, **kwargs: str) -> str:
        messages = {
            "vi": {
                "swapped": (
                    "Bạn đang chọn ngược 2 file.\n"
                    "- Ô File hệ thống đang là file sao kê ngân hàng: {system_name}\n"
                    "- Ô File sao kê đang là file hệ thống: {bank_name}\n"
                    "Vui lòng đổi lại đúng vị trí rồi dò lại."
                ),
                "system_is_bank": (
                    "Ô File hệ thống đang chọn file sao kê ngân hàng: {name}\n"
                    "Vui lòng chuyển file này sang ô Sao kê, hoặc chọn lại đúng file hệ thống."
                ),
                "invalid_system": (
                    "File hệ thống không đúng mẫu: {name}\n"
                    "Vui lòng chọn đúng file giao dịch hệ thống (.xls)."
                ),
                "bank_is_system": (
                    "Ô File sao kê đang chọn file hệ thống: {name}\n"
                    "Vui lòng chuyển file này sang ô Hệ thống, hoặc chọn lại đúng file sao kê."
                ),
                "invalid_bank": (
                    "File sao kê không đúng mẫu: {name}\n"
                    "Vui lòng chọn đúng file sao kê ngân hàng (.xlsx)."
                ),
            },
            "en": {
                "swapped": (
                    "The two files are selected in the wrong slots.\n"
                    "- The System file is actually a bank statement: {system_name}\n"
                    "- The Statement file is actually a system file: {bank_name}\n"
                    "Please switch them and try again."
                ),
                "system_is_bank": (
                    "The System slot currently contains a bank statement file: {name}\n"
                    "Please move this file to the Statement slot, or choose the correct system file."
                ),
                "invalid_system": (
                    "The selected System file does not match the expected template: {name}\n"
                    "Please choose the correct system transaction file (.xls)."
                ),
                "bank_is_system": (
                    "The Statement slot currently contains a system file: {name}\n"
                    "Please move this file to the System slot, or choose the correct statement file."
                ),
                "invalid_bank": (
                    "The selected Statement file does not match the expected template: {name}\n"
                    "Please choose the correct bank statement file (.xlsx)."
                ),
            },
            "zh": {
                "swapped": (
                    "两个文件放反了。\n"
                    "- 系统文件栏位现在是银行流水: {system_name}\n"
                    "- 流水文件栏位现在是系统文件: {bank_name}\n"
                    "请调换后再重试。"
                ),
                "system_is_bank": (
                    "系统文件栏位现在选的是银行流水: {name}\n"
                    "请将该文件放到流水栏位，或重新选择正确的系统文件。"
                ),
                "invalid_system": (
                    "所选的系统文件不符合预期模板: {name}\n"
                    "请选择正确的系统交易文件 (.xls)。"
                ),
                "bank_is_system": (
                    "流水文件栏位现在选的是系统文件: {name}\n"
                    "请将该文件放到系统栏位，或重新选择正确的流水文件。"
                ),
                "invalid_bank": (
                    "所选的流水文件不符合预期模板: {name}\n"
                    "请选择正确的银行流水文件 (.xlsx)。"
                ),
            },
        }
        language_messages = messages.get(self.current_language, messages["vi"])
        template = language_messages.get(key, messages["vi"][key])
        return template.format(**kwargs)

    def _handle_scan_requested(self) -> None:
        system_path = self._selected_system_path.strip()
        bank_path = self._selected_bank_path.strip()
        if system_path and bank_path:
            validation_message = self._validate_selected_files(system_path, bank_path)
            if validation_message:
                logger.warning(
                    "Chan thao tac do vi chon sai file. system_file=%s | bank_file=%s | message=%s",
                    system_path,
                    bank_path,
                    validation_message.replace("\n", " | "),
                )
                QMessageBox.warning(
                    self,
                    tr(self.current_language, "app_title"),
                    validation_message,
                )
                return
        self._start_scan()

    def _start_scan(self) -> None:
        system_path = self._selected_system_path.strip()
        bank_path = self._selected_bank_path.strip()
        if not system_path or not bank_path:
            logger.warning("Người dùng bấm dò nhưng chưa chọn đủ 2 file.")
            QMessageBox.warning(
                self,
                tr(self.current_language, "app_title"),
                tr(self.current_language, "select_files_first"),
            )
            return
        logger.info(
            "Bắt đầu dò từ giao diện. system_file=%s | bank_file=%s",
            system_path,
            bank_path,
        )
        self._update_locked_state(True)
        self._show_results_page()
        self.overlay.set_message("Loading")
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
        self._show_results_page()
        self.overlay.hide()
        self.scan_button.setEnabled(True)
        logger.info(
            "Dò hoàn tất trên giao diện. matched=%s | review=%s | unmatched=%s",
            result.summary.matched_system,
            result.summary.review_system,
            result.summary.unmatched_system,
        )

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self.overlay.hide()
        self.scan_button.setEnabled(True)
        self._update_locked_state(True)
        self._show_startup_page()
        logger.error("Dò thất bại trên giao diện: %s", message)
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
        self.bank_model = TransactionsTableModel(self._bank_grid_headers(), result.bank_rows, self.current_language)
        self.system_proxy = TransactionsFilterProxyModel()
        self.bank_proxy = TransactionsFilterProxyModel()
        self.system_proxy.setSourceModel(self.system_model)
        self.bank_proxy.setSourceModel(self.bank_model)
        self.system_proxy.setSortRole(Qt.UserRole + 2)
        self.bank_proxy.setSortRole(Qt.UserRole + 2)
        self.system_grid.table.setModel(self.system_proxy)
        self.bank_grid.table.setModel(self.bank_proxy)
        self.system_grid.table.sortByColumn(0, Qt.AscendingOrder)
        self.bank_grid.table.sortByColumn(0, Qt.AscendingOrder)
        self._set_active_grid_mode("bank")
        self._configure_date_filters(result)
        self._populate_search_columns()
        self._apply_filters()
        self._apply_grid_column_widths()
        self._update_summary()
        self._update_row_counts()
        logger.info(
            "Đã bind dữ liệu vào lưới. system_rows=%s | bank_rows=%s",
            len(result.system_rows),
            len(result.bank_rows),
        )

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

    def _apply_grid_column_widths(self) -> None:
        self.system_grid.table.auto_fit_columns(
            self._system_grid_fixed_widths(),
            min_width=66,
            max_auto_width=132,
            padding=14,
        )
        self.bank_grid.table.auto_fit_columns(
            self._bank_grid_fixed_widths(),
            min_width=62,
            max_auto_width=170,
            padding=14,
        )

    @staticmethod
    def _system_grid_fixed_widths() -> dict[int, int]:
        return {
            2: 250,
            3: 170,
        }

    @staticmethod
    def _bank_grid_fixed_widths() -> dict[int, int]:
        return {
            3: 138,
            4: 132,
            5: 160,
            6: 300,
        }

    @staticmethod
    def _bank_grid_headers() -> list[str]:
        return [
            "Ngày yêu cầu",
            "Ngày GD",
            "Mã GD",
            "NH đối tác",
            "TK đối tác",
            "Tên đối tác",
            "Diễn giải",
            "Chi",
            "Thu",
            "Phí",
            "Thuế",
            "Số dư",
        ]

    def _apply_filters(self) -> None:
        if not self.system_proxy or not self.bank_proxy:
            if self._filter_overlay_active:
                self.overlay.hide()
                self._filter_overlay_active = False
            return
        status_mode = self._current_status_mode()
        flow_mode = next(mode for mode, button in self.flow_buttons.items() if button.isChecked())
        reference_mode = self.reference_filter_combo.currentData() or "all"
        use_date_filter = self._date_filter_active and self.date_from_edit.isEnabled()
        date_from = self.date_from_edit.date().toPython() if use_date_filter else None
        date_to = self.date_to_edit.date().toPython() if use_date_filter else None
        for proxy in (self.system_proxy, self.bank_proxy):
            proxy.set_status_mode(status_mode)
            proxy.set_flow_mode(flow_mode)
            proxy.set_reference_mode(str(reference_mode))
            proxy.set_date_range(date_from, date_to)
        self._filter_system_grid()
        self._filter_bank_grid()
        self._update_summary()
        self._update_row_counts()
        logger.debug(
            "Áp dụng bộ lọc. status=%s | flow=%s | reference=%s | system_visible=%s | bank_visible=%s",
            status_mode,
            flow_mode,
            reference_mode,
            self.system_proxy.rowCount() if self.system_proxy else 0,
            self.bank_proxy.rowCount() if self.bank_proxy else 0,
        )
        if self._filter_overlay_active:
            self.overlay.hide()
            self._filter_overlay_active = False

    def _schedule_filters(self, *, with_loading: bool = False) -> None:
        if self._filter_apply_scheduled:
            self._filter_overlay_active = self._filter_overlay_active or with_loading
            return
        self._filter_apply_scheduled = True
        if with_loading and self.current_result is not None:
            self.overlay.set_message(self._filter_loading_text())
            self.overlay.show()
            self._filter_overlay_active = True
            QApplication.processEvents()
        QTimer.singleShot(0, self._run_scheduled_filters)

    def _run_scheduled_filters(self) -> None:
        self._filter_apply_scheduled = False
        self._apply_filters()

    def _filter_system_grid(self) -> None:
        if not self.system_proxy:
            return
        current_data = self.system_grid.columns.currentData()
        self.system_proxy.set_search_column(-1 if current_data is None else int(current_data))
        self.system_proxy.set_search_text(self.system_grid.search.text())
        self._update_row_counts()
        logger.debug(
            "Lọc lưới hệ thống. column=%s | search=%s | visible=%s",
            current_data,
            self.system_grid.search.text(),
            self.system_proxy.rowCount(),
        )

    def _filter_bank_grid(self) -> None:
        if not self.bank_proxy:
            return
        current_data = self.bank_grid.columns.currentData()
        self.bank_proxy.set_search_column(-1 if current_data is None else int(current_data))
        self.bank_proxy.set_search_text(self.bank_grid.search.text())
        self._update_row_counts()
        logger.debug(
            "Lọc lưới sao kê. column=%s | search=%s | visible=%s",
            current_data,
            self.bank_grid.search.text(),
            self.bank_proxy.rowCount(),
        )

    def _sync_quick_search(self, text: str) -> None:
        for grid in (self.system_grid, self.bank_grid):
            grid.columns.blockSignals(True)
            grid.columns.setCurrentIndex(0)
            grid.columns.blockSignals(False)
            grid.search.blockSignals(True)
            grid.search.setText(text)
            grid.search.blockSignals(False)
        self._filter_system_grid()
        self._filter_bank_grid()

    def _update_summary(self) -> None:
        if not self.current_result:
            self.summary_grid_label.setText("")
            for button in self.summary_filter_buttons.values():
                button.setText("")
            return
        proxy = self.bank_proxy if self._active_grid_mode == "bank" else self.system_proxy
        grid_label = tr(self.current_language, "bank_grid") if self._active_grid_mode == "bank" else tr(self.current_language, "system_grid")
        exact, group, review, unmatched = self._status_breakdown(proxy)
        self.summary_grid_label.setText(grid_label)
        self.summary_filter_buttons["all"].setText(tr(self.current_language, "status_all"))
        self.summary_filter_buttons["matched_exact"].setText(f"{exact} {tr(self.current_language, 'matched_exact')}")
        self.summary_filter_buttons["matched_group"].setText(f"{group} {tr(self.current_language, 'status_matched_group')}")
        self.summary_filter_buttons["review"].setText(f"{review} {tr(self.current_language, 'review')}")
        self.summary_filter_buttons["unmatched"].setText(f"{unmatched} {tr(self.current_language, 'unmatched')}")

    def _status_breakdown(self, proxy) -> tuple[int, int, int, int]:
        if proxy is None:
            return 0, 0, 0, 0
        return (
            proxy.count_for_status_mode("matched_exact"),
            proxy.count_for_status_mode("matched_group"),
            proxy.count_for_status_mode("review"),
            proxy.count_for_status_mode("unmatched"),
        )

    def _update_row_counts(self) -> None:
        for grid, model, proxy in (
            (self.system_grid, self.system_model, self.system_proxy),
            (self.bank_grid, self.bank_model, self.bank_proxy),
        ):
            total = model.total_rows if model else 0
            visible = proxy.rowCount() if proxy else 0
            grid.count.setText(tr(self.current_language, "grid_rows", visible=visible, total=total))
        self._update_grid_heights()

    def _fill_metadata(self, result: ReconciliationResult) -> None:
        metadata = result.metadata
        period_text = ""
        if metadata.from_date and metadata.to_date:
            period_text = f"{metadata.from_date:%Y-%m-%d} → {metadata.to_date:%Y-%m-%d}"
        values = {
            "meta_bank_name": metadata.bank_name_vi or metadata.bank_name_en,
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
        self._history_records = list(records)
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
        logger.debug("Đã tải lịch sử lên giao diện. rows=%s", len(records))

    def _open_history_dialog(self) -> None:
        dialog = HistoryDialog(self.current_language, self._history_records, self)
        dialog.exec()

    def _swap_grids(self) -> None:
        target_mode = "bank" if self._active_grid_mode == "system" else "system"
        self._set_active_grid_mode(target_mode)
        logger.info("Đã chuyển lưới đang xem sang %s", target_mode)

    def _open_pair(self, source: str, row) -> None:
        if self.current_result is None:
            return
        logger.info(
            "Mở popup chi tiết đối ứng. source=%s | excel_row=%s | status=%s",
            source,
            getattr(row, "excel_row", None),
            getattr(row, "status", None),
        )
        if getattr(row, "match_type", "none") == "group" and getattr(row, "group_id", None):
            system_rows, bank_rows = self._group_rows(row.group_id)
            if source == "system" and not system_rows:
                system_rows = [row]
            if source == "bank" and not bank_rows:
                bank_rows = [row]
            if source == "system" and bank_rows:
                self._focus_counterpart_rows(
                    self.bank_model,
                    self.bank_proxy,
                    self.bank_grid.table,
                    [bank_row.row_id for bank_row in bank_rows],
                )
            elif source == "bank" and system_rows:
                self._focus_counterpart_rows(
                    self.system_model,
                    self.system_proxy,
                    self.system_grid.table,
                    [system_row.row_id for system_row in system_rows],
                )
            dialog = PairDialog(
                self.current_language,
                tr(self.current_language, "paired_system"),
                self.current_result.system_headers,
                system_rows,
                tr(self.current_language, "paired_bank"),
                self._bank_grid_headers(),
                bank_rows,
                self,
            )
            dialog.exec()
            return
        if source == "system":
            system_rows = [row]
            bank_rows = self._review_or_matched_bank_rows(row)
            self._focus_counterpart_rows(
                self.bank_model,
                self.bank_proxy,
                self.bank_grid.table,
                [bank_row.row_id for bank_row in bank_rows],
            )
        else:
            bank_rows = [row]
            system_rows = self._review_or_matched_system_rows(row)
            self._focus_counterpart_rows(
                self.system_model,
                self.system_proxy,
                self.system_grid.table,
                [system_row.row_id for system_row in system_rows],
            )
        dialog = PairDialog(
            self.current_language,
            tr(self.current_language, "paired_system"),
            self.current_result.system_headers,
            system_rows,
            tr(self.current_language, "paired_bank"),
            self._bank_grid_headers(),
            bank_rows,
            self,
        )
        dialog.exec()

    def _focus_counterpart_rows(self, model, proxy, table: FrozenTableView, row_ids: list[str]) -> None:
        if not model or not proxy or not row_ids:
            return
        source_row = model.row_index_by_id(row_ids[0])
        if source_row is None:
            return
        target_column = 1 if model.columnCount() > 1 else 0
        source_index = model.index(source_row, target_column)
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

    def _review_or_matched_bank_rows(self, row) -> list[object]:
        matched_row = self._bank_row_by_id(getattr(row, "matched_bank_id", None))
        if matched_row is not None:
            return [matched_row]
        review_ids = list(getattr(row, "review_bank_ids", []) or [])
        review_rows = [self._bank_row_by_id(row_id) for row_id in review_ids]
        return [candidate for candidate in review_rows if candidate is not None]

    def _review_or_matched_system_rows(self, row) -> list[object]:
        matched_row = self._system_row_by_id(getattr(row, "matched_system_id", None))
        if matched_row is not None:
            return [matched_row]
        review_ids = list(getattr(row, "review_system_ids", []) or [])
        review_rows = [self._system_row_by_id(row_id) for row_id in review_ids]
        return [candidate for candidate in review_rows if candidate is not None]

    def _group_rows(self, group_id: str) -> tuple[list[object], list[object]]:
        if self.current_result is None:
            return [], []
        system_rows = sorted(
            [row for row in self.current_result.system_rows if getattr(row, "group_id", None) == group_id],
            key=lambda row: (getattr(row, "group_order", 0), getattr(row, "excel_row", 0)),
        )
        bank_rows = sorted(
            [row for row in self.current_result.bank_rows if getattr(row, "group_id", None) == group_id],
            key=lambda row: (getattr(row, "group_order", 0), getattr(row, "excel_row", 0)),
        )
        return system_rows, bank_rows

    def _export_unmatched(self) -> None:
        if not self.current_result:
            return
        rows_to_export = self._visible_rows_for_active_grid()
        if not rows_to_export:
            logger.warning("Không có dữ liệu để xuất theo bộ lọc hiện tại.")
            QMessageBox.information(
                self,
                tr(self.current_language, "app_title"),
                self._no_rows_to_export_message(),
            )
            return
        status_mode = self._current_status_mode()
        highlight_unmatched = status_mode == "all"
        default_path = self._default_export_path()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr(self.current_language, "save_dialog_title"),
            str(default_path),
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            logger.info("Người dùng hủy thao tác xuất Excel.")
            return
        try:
            headers = self._active_headers_for_export()
            sheet_name = self._active_export_sheet_name()
            attached_statement_path = (
                self.current_result.bank_file
                if self.attach_statement_checkbox.isChecked()
                else None
            )
            logger.info(
                "Bắt đầu xuất Excel từ giao diện. grid=%s | output=%s | rows=%s | highlight_unmatched=%s | attach_statement=%s",
                self._active_grid_mode,
                file_path,
                len(rows_to_export),
                highlight_unmatched,
                bool(attached_statement_path),
            )
            export_system_rows(
                headers,
                rows_to_export,
                file_path,
                highlight_unmatched=highlight_unmatched,
                sheet_name=sheet_name,
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
            logger.exception("Xuất Excel thất bại: %s", exc)
            QMessageBox.critical(
                self,
                tr(self.current_language, "app_title"),
                f"{tr(self.current_language, 'export_failed')}\n{exc}",
            )
            return
        logger.info("Xuất Excel thành công. output=%s", file_path)
        QMessageBox.information(
            self,
            tr(self.current_language, "app_title"),
            tr(self.current_language, "export_success"),
        )

    def _active_model_and_proxy(self) -> tuple[TransactionsTableModel | None, TransactionsFilterProxyModel | None]:
        if self._active_grid_mode == "bank":
            return self.bank_model, self.bank_proxy
        return self.system_model, self.system_proxy

    def _visible_rows_for_active_grid(self) -> list[object]:
        model, proxy = self._active_model_and_proxy()
        if not model or not proxy:
            return []
        rows: list[object] = []
        for proxy_row in range(proxy.rowCount()):
            proxy_index = proxy.index(proxy_row, 0)
            source_index = proxy.mapToSource(proxy_index)
            if not source_index.isValid():
                continue
            rows.append(model.row_object(source_index.row()))
        return rows

    def _active_headers_for_export(self) -> list[str]:
        if self._active_grid_mode == "bank":
            return list(self.current_result.bank_headers) if self.current_result else self._bank_grid_headers()
        return list(self.current_result.system_headers) if self.current_result else []

    def _active_export_sheet_name(self) -> str:
        return "SaoKe_Xuat" if self._active_grid_mode == "bank" else "HeThong_Xuat"

    def _current_status_mode(self) -> str:
        return next(mode for mode, button in self.summary_filter_buttons.items() if button.isChecked())

    def _export_button_label(self) -> str:
        labels = {
            "vi": "Xuất Excel",
            "en": "Export Excel",
            "zh": "导出 Excel",
        }
        return labels.get(self.current_language, labels["vi"])

    def _filter_loading_text(self) -> str:
        labels = {
            "vi": "Đang lọc...",
            "en": "Filtering...",
            "zh": "正在筛选...",
        }
        return labels.get(self.current_language, labels["vi"])

    def _quick_search_placeholder(self) -> str:
        labels = {
            "vi": "Tìm giao dịch liên quan",
            "en": "Search related transactions",
            "zh": "搜索相关交易",
        }
        return labels.get(self.current_language, labels["vi"])

    def _default_export_path(self) -> Path:
        if self.current_result:
            selected_file = self.current_result.bank_file if self._active_grid_mode == "bank" else self.current_result.system_file
            if selected_file:
                selected_path = Path(selected_file)
                if selected_path.suffix.lower() == ".xlsx":
                    return selected_path.with_name(f"{selected_path.stem}_Xuat.xlsx")
                if selected_path.suffix:
                    return selected_path.with_suffix(".xlsx")
                return selected_path.with_name(f"{selected_path.name}_Xuat.xlsx")
        default_name = "sao_ke_xuat.xlsx" if self._active_grid_mode == "bank" else "he_thong_xuat.xlsx"
        return Path.cwd() / default_name

    def _no_rows_to_export_message(self) -> str:
        messages = {
            "vi": "Không có dữ liệu để xuất theo bộ lọc hiện tại.",
            "en": "There are no rows to export for the current filter.",
            "zh": "当前筛选条件下没有可导出的数据。",
        }
        return messages.get(self.current_language, messages["vi"])

    def _configure_date_filters(self, result: ReconciliationResult) -> None:
        available_dates = self._all_result_dates(result)
        if not available_dates:
            return
        self._date_filter_active = False
        min_date = min(available_dates)
        max_date = max(available_dates)
        min_qdate = QDate(min_date.year, min_date.month, min_date.day)
        max_qdate = QDate(max_date.year, max_date.month, max_date.day)
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.blockSignals(True)
            widget.setMinimumDate(min_qdate)
            widget.setMaximumDate(max_qdate)
        self.date_from_edit.setDate(min_qdate)
        self.date_to_edit.setDate(max_qdate)
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.blockSignals(False)

    def _reset_date_filter(self) -> None:
        if self.current_result is None:
            return
        self._date_filter_active = False
        self._configure_date_filters(self.current_result)
        self._schedule_filters(with_loading=True)

    def _on_date_filter_changed(self) -> None:
        if self.current_result is None:
            return
        self._date_filter_active = True
        self._schedule_filters(with_loading=True)

    def _all_result_dates(self, result: ReconciliationResult) -> list[date]:
        values: list[date] = []
        for row in result.system_rows:
            if row.voucher_date is not None:
                values.append(row.voucher_date)
        for row in result.bank_rows:
            if row.transaction_date is not None:
                values.append(row.transaction_date)
            elif row.requesting_datetime is not None:
                values.append(row.requesting_datetime.date())
        return values

    def _date_filter_text(self, key: str) -> str:
        labels = {
            "vi": {
                "caption": "Ngày",
                "from": "Từ ngày",
                "to": "Đến ngày",
                "reset": "Tất cả ngày",
            },
            "en": {
                "caption": "Date",
                "from": "From",
                "to": "To",
                "reset": "All dates",
            },
            "zh": {
                "caption": "日期",
                "from": "从",
                "to": "到",
                "reset": "全部日期",
            },
        }
        language_labels = labels.get(self.current_language, labels["vi"])
        return language_labels[key]

    def _populate_reference_filter_options(self) -> None:
        current_value = self.reference_filter_combo.currentData()
        options = [
            ("all", "reference_all"),
            ("FT", "reference_ft"),
            ("TT", "reference_tt"),
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

    def _set_active_grid_mode(self, mode: str) -> None:
        self._active_grid_mode = "bank" if mode == "bank" else "system"
        current_widget = self.bank_page if self._active_grid_mode == "bank" else self.system_page
        self.grid_stack.setCurrentWidget(current_widget)
        self._update_grid_toggle_button()
        self._update_summary()
        self._update_export_controls_state(self.current_result is None)
        self._update_grid_heights()

    def _update_grid_toggle_button(self) -> None:
        labels = {
            "vi": {"system": "Xem sao kê", "bank": "Xem hệ thống"},
            "en": {"system": "View statement", "bank": "View system"},
            "zh": {"system": "查看流水", "bank": "查看系统"},
        }
        language_labels = labels.get(self.current_language, labels["vi"])
        self.swap_button.setText(language_labels[self._active_grid_mode])
