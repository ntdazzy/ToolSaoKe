from __future__ import annotations

import logging

from PySide6.QtCore import QSize, QThread, Qt, QTimer, Slot
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.resource_utils import logo_image_path
from app.services.history_store import HistoryStore
from app.ui.components import (
    FilePickerPanel,
)
from app.ui.config import (
    date_filter_text,
    summary_help_tooltip,
)
from app.ui.main_window_actions_mixin import MainWindowActionsMixin
from app.ui.main_window_filter_mixin import MainWindowFilterMixin
from app.ui.main_window_scan_mixin import MainWindowScanMixin
from app.ui.pages import ResultsPage, StartupPage
from app.ui.styles import MAIN_WINDOW_STYLESHEET
from app.ui.widgets import LoadingOverlay
from app.models import ReconciliationResult

logger = logging.getLogger(__name__)


class MainWindow(
    MainWindowActionsMixin,
    MainWindowFilterMixin,
    MainWindowScanMixin,
    QMainWindow,
):
    def __init__(self) -> None:
        super().__init__()
        logo_path = logo_image_path()
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.current_language = "vi"
        self.history_store = HistoryStore("data/history.sqlite")
        self._history_records: list[dict] = []
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
        self._scan_in_progress = False
        self._compact_window_mode = False
        self._file_card_host = "startup"
        self._normal_window_flags = self.windowFlags() | Qt.WindowMinimizeButtonHint | Qt.WindowMaximizeButtonHint
        self._compact_window_flags = self._normal_window_flags & ~Qt.WindowMaximizeButtonHint
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

        self.startup_page = StartupPage()
        self.results_page = ResultsPage()
        self.page_stack.addWidget(self.startup_page)
        self.page_stack.addWidget(self.results_page)

        self.file_card = FilePickerPanel()
        self.startup_page.attach_file_panel(self.file_card)

        self.system_file_label = self.file_card.system_file_label
        self.bank_file_label = self.file_card.bank_file_label
        self.language_label = self.file_card.language_label
        self.system_path_edit = self.file_card.system_path_edit
        self.bank_path_edit = self.file_card.bank_path_edit
        self.system_choose_button = self.file_card.system_choose_button
        self.bank_choose_button = self.file_card.bank_choose_button
        self.language_combo = self.file_card.language_combo
        self.scan_button = self.file_card.scan_button

        self.title_label = self.results_page.title_label
        self.subtitle_label = self.results_page.subtitle_label
        self.top_section = self.results_page.top_section
        self.metadata_card = self.results_page.metadata_card
        self.metadata_title = self.results_page.metadata_title
        self.metric_titles = self.results_page.metric_titles
        self.metric_values = self.results_page.metric_values
        self.metric_cards = self.results_page.metric_cards
        self.results_card = self.results_page.results_card
        self.results_title = self.results_page.results_title
        self.status_filter_group = self.results_page.status_filter_group
        self.status_group_label = self.results_page.status_group_label
        self.status_group = self.results_page.status_group
        self.status_buttons = self.results_page.status_buttons
        self.flow_filter_group = self.results_page.flow_filter_group
        self.flow_group_label = self.results_page.flow_group_label
        self.flow_group = self.results_page.flow_group
        self.flow_buttons = self.results_page.flow_buttons
        self.filter_controls_layout = self.results_page.filter_controls_layout
        self.reference_filter_group = self.results_page.reference_filter_group
        self.reference_filter_label = self.results_page.reference_filter_label
        self.reference_filter_combo = self.results_page.reference_filter_combo
        self.date_filter_group = self.results_page.date_filter_group
        self.date_filter_label = self.results_page.date_filter_label
        self.date_range_separator = self.results_page.date_range_separator
        self.date_from_edit = self.results_page.date_from_edit
        self.date_to_edit = self.results_page.date_to_edit
        self.date_clear_button = self.results_page.date_clear_button
        self.quick_search_group = self.results_page.quick_search_group
        self.quick_search_edit = self.results_page.quick_search_edit
        self.summary_group = self.results_page.summary_group
        self.summary_grid_label = self.results_page.summary_grid_label
        self.summary_filter_group = self.results_page.summary_filter_group
        self.summary_filter_buttons = self.results_page.summary_filter_buttons
        self.summary_help_button = self.results_page.summary_help_button
        self.summary_actions = self.results_page.summary_actions
        self.history_button = self.summary_actions.history_button
        self.export_button = self.summary_actions.export_button
        self.attach_statement_checkbox = self.summary_actions.attach_statement_checkbox
        self.swap_button = self.results_page.swap_button
        self.locked_label = self.results_page.locked_label
        self.results_content = self.results_page.results_content
        self.grid_stack = self.results_page.grid_stack
        self.system_grid = self.results_page.system_grid
        self.bank_grid = self.results_page.bank_grid
        self.system_page = self.results_page.system_page
        self.bank_page = self.results_page.bank_page

        self.system_choose_button.clicked.connect(lambda: self._choose_file("system"))
        self.bank_choose_button.clicked.connect(lambda: self._choose_file("bank"))

        self.language_combo.addItem("Tiếng Việt", "vi")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("中文简体", "zh")
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)

        self.history_button.clicked.connect(self._open_history_dialog)
        self.scan_button.clicked.connect(self._handle_scan_requested)
        self.export_button.clicked.connect(self._export_unmatched)

        self.history_table = QTableWidget(0, 4)
        self.history_table.verticalHeader().hide()
        self.history_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.history_table.setSelectionMode(QTableWidget.NoSelection)
        self.history_table.setShowGrid(False)
        self.history_table.hide()

        for button in self.status_buttons.values():
            button.clicked.connect(lambda _checked=False: self._schedule_filters(with_loading=True))
        for button in self.flow_buttons.values():
            button.clicked.connect(lambda _checked=False: self._schedule_filters(with_loading=True))
        for button in self.summary_filter_buttons.values():
            button.clicked.connect(lambda _checked=False: self._schedule_filters(with_loading=True))

        self.reference_filter_combo.currentIndexChanged.connect(lambda _index: self._schedule_filters(with_loading=True))
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.dateChanged.connect(self._on_date_filter_changed)
        self.date_clear_button.clicked.connect(self._reset_date_filter)
        self.quick_search_edit.textChanged.connect(self._sync_quick_search)
        self.swap_button.clicked.connect(self._swap_grids)

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

    def _apply_responsive_layouts(self) -> None:
        width = self.width()
        if self.page_stack.currentWidget() is self.startup_page:
            self.startup_page.apply_compact_layout(self.file_card)
            return
        self.results_page.apply_responsive_layout(
            width,
            self._active_grid_mode,
            self.system_proxy,
            self.bank_proxy,
            self.file_card,
        )

    def _move_file_card(self, target: str) -> None:
        if self._file_card_host == target:
            return
        if target == "startup":
            self.startup_page.attach_file_panel(self.file_card)
        else:
            self.results_page.attach_file_panel(self.file_card)
        self._file_card_host = target

    def _show_startup_page(self) -> None:
        self._initial_compact_size_applied = False
        self._move_file_card("startup")
        self.page_stack.setCurrentWidget(self.startup_page)
        self._apply_initial_compact_size()

    def _show_results_page(self) -> None:
        self._move_file_card("results")
        self.page_stack.setCurrentWidget(self.results_page)
        self._ensure_results_window_size()
        self._apply_responsive_layouts()

    @Slot(object)
    def _handle_scan_finished_queued(self, result: ReconciliationResult) -> None:
        self._scan_finished(result)

    @Slot(str)
    def _handle_scan_failed_queued(self, message: str) -> None:
        self._scan_failed(message)

    @Slot()
    def _handle_scan_cleanup_queued(self) -> None:
        self._cleanup_scan_thread()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_responsive_layouts()

    def _apply_styles(self) -> None:
        self.setStyleSheet(MAIN_WINDOW_STYLESHEET)


    def _apply_language(self) -> None:
        self.title_label.setText(tr(self.current_language, "app_title"))
        self.subtitle_label.setText(tr(self.current_language, "app_subtitle"))
        self.system_file_label.setText(tr(self.current_language, "system_file"))
        self.bank_file_label.setText(tr(self.current_language, "bank_file"))
        self.language_label.setText(tr(self.current_language, "language"))
        self.history_button.setText(tr(self.current_language, "history_button"))
        self.reference_filter_label.setText(tr(self.current_language, "reference_filter"))
        self.date_filter_label.setText(date_filter_text(self.current_language, "caption"))
        self.date_range_separator.setText("~")
        self.system_choose_button.setText(tr(self.current_language, "choose_file"))
        self.bank_choose_button.setText(tr(self.current_language, "choose_file"))
        self.scan_button.setText(tr(self.current_language, "scan"))
        self.export_button.setText(self._export_button_label())
        self.attach_statement_checkbox.setText(tr(self.current_language, "attach_statement"))
        self.date_clear_button.setText(date_filter_text(self.current_language, "reset"))
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
        self.summary_help_button.setToolTip(summary_help_tooltip(self.current_language))
        self.system_grid.search.setPlaceholderText(tr(self.current_language, "search"))
        self.bank_grid.search.setPlaceholderText(tr(self.current_language, "search"))
        for key, label in self.metric_titles.items():
            label.setText(tr(self.current_language, key))
        self._refresh_history_headers()
        self._populate_reference_filter_options()
        self.overlay.set_badge(tr(self.current_language, "loading_badge"))
        self.overlay.set_hint(tr(self.current_language, "loading_hint"))
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



    def _on_language_changed(self) -> None:
        self.current_language = self.language_combo.currentData()
        self._apply_language()
        logger.info("Đã đổi ngôn ngữ giao diện sang %s", self.current_language)

    def _apply_initial_compact_size(self) -> None:
        if self._initial_compact_size_applied:
            return
        self.startup_page.apply_compact_layout(self.file_card)
        self.file_card.updateGeometry()
        self.startup_page.adjustSize()
        self.page_stack.adjustSize()
        self.adjustSize()
        target_size = self.startup_page.sizeHint()
        self._set_compact_window_mode(True)
        self.setFixedSize(target_size)
        self._initial_compact_size_applied = True

    def _ensure_results_window_size(self) -> None:
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        self.system_path_edit.setMaximumWidth(16777215)
        self.bank_path_edit.setMaximumWidth(16777215)
        self._set_compact_window_mode(False)
        if self.width() < self._expanded_window_size.width() or self.height() < self._expanded_window_size.height():
            self.resize(self._expanded_window_size)
        if self.isVisible():
            self.showNormal()
            self.show()

    def _set_compact_window_mode(self, enabled: bool) -> None:
        if self._compact_window_mode == enabled:
            return
        self._compact_window_mode = enabled
        was_visible = self.isVisible()
        position = self.pos()
        self.setWindowFlags(self._compact_window_flags if enabled else self._normal_window_flags)
        if was_visible:
            if not enabled:
                self.showNormal()
            self.show()
            self.move(position)

    def _update_locked_state(self, locked: bool) -> None:
        has_result = self.current_result is not None
        self.top_section.setVisible(has_result or self._file_card_host == "results")
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
















































