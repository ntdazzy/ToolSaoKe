from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QBoxLayout,
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.components import (
    ChipButton,
    DataGridPanel,
    FilterGroupFrame,
    FilePickerPanel,
    MetricCard,
    SummaryActionsBar,
    match_kind_chip_palette,
    summary_chip_palette,
)
from app.ui.metadata import DEFAULT_METRIC_LAYOUT, METADATA_LAYOUTS
from app.ui.widgets import FrozenTableView, InstantToolTipButton, PopupDateEdit, StyledComboBox


class StartupPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("startupPage")
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(18, 18, 18, 18)
        self.content_layout.setSpacing(0)
        self.content_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

    def attach_file_panel(self, file_panel: FilePickerPanel) -> None:
        current_parent = file_panel.parentWidget()
        if current_parent is not None and current_parent.layout() is not None:
            current_parent.layout().removeWidget(file_panel)
        file_panel.setParent(None)
        self.content_layout.addWidget(file_panel, 0, Qt.AlignTop | Qt.AlignLeft)

    def apply_compact_layout(self, file_panel: FilePickerPanel) -> None:
        self.content_layout.setContentsMargins(18, 18, 18, 18)
        self.content_layout.setSpacing(0)
        file_panel.setMaximumWidth(450)
        file_panel.setMinimumWidth(0)
        file_panel.system_path_edit.setMaximumWidth(200)
        file_panel.bank_path_edit.setMaximumWidth(200)


class ResultsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("resultsPage")

        self.page_layout = QVBoxLayout(self)
        self.page_layout.setContentsMargins(0, 0, 0, 0)
        self.page_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.page_layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget()
        self.scroll_area.setWidget(self.scroll_content)

        self.root_layout = QVBoxLayout(self.scroll_content)
        self.root_layout.setContentsMargins(18, 18, 18, 18)
        self.root_layout.setSpacing(14)
        self.root_layout.setAlignment(Qt.AlignTop)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        self.title_label.hide()
        self.subtitle_label.hide()
        self.root_layout.addWidget(self.title_label)
        self.root_layout.addWidget(self.subtitle_label)

        self.top_section = QWidget()
        self.top_section.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.top_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.top_layout.setContentsMargins(0, 0, 0, 0)
        self.top_layout.setSpacing(16)
        self.top_layout.setAlignment(Qt.AlignTop)
        self.top_section.setLayout(self.top_layout)
        self.root_layout.addWidget(self.top_section)

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
        self.top_layout.addWidget(self.metadata_card, 7, Qt.AlignTop)

        self.metric_titles: dict[str, QLabel] = {}
        self.metric_values: dict[str, QLabel] = {}
        self.metric_cards: dict[str, QWidget] = {}
        self._metric_layout_mode = ""
        self._metric_layouts = METADATA_LAYOUTS
        for key, _row, _column, _row_span, _column_span in DEFAULT_METRIC_LAYOUT:
            card = MetricCard()
            self.metric_cards[key] = card
            self.metric_titles[key] = card.title_label
            self.metric_values[key] = card.value_label
        self.apply_metadata_layout("wide")

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

        self.status_filter_group = FilterGroupFrame()
        status_group_layout = self.status_filter_group.row_layout
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
            self.status_group.addButton(button)
            self.status_buttons[mode] = button
            status_group_layout.addWidget(button)
        self.status_buttons["all"].setChecked(True)
        self.toolbar_groups_layout.addWidget(self.status_filter_group)

        self.flow_filter_group = FilterGroupFrame()
        flow_group_layout = self.flow_filter_group.row_layout
        self.flow_group_label = QLabel()
        self.flow_group_label.setObjectName("filterLabel")
        flow_group_layout.addWidget(self.flow_group_label)
        self.flow_filter_combo = StyledComboBox()
        self.flow_filter_combo.setMinimumWidth(176)
        self.flow_filter_combo.setMinimumHeight(36)
        flow_group_layout.addWidget(self.flow_filter_combo)

        self.filter_controls_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self.filter_controls_layout.setSpacing(14)
        results_layout.addLayout(self.filter_controls_layout)

        self.reference_filter_label = QLabel()
        self.reference_filter_label.setObjectName("filterLabel")
        self.reference_filter_combo = StyledComboBox()
        self.reference_filter_combo.setMinimumWidth(220)
        self.reference_filter_combo.setMinimumHeight(36)
        self.reference_filter_group = FilterGroupFrame()
        reference_group_layout = self.reference_filter_group.row_layout
        reference_group_layout.addWidget(self.reference_filter_label)
        reference_group_layout.addWidget(self.reference_filter_combo)

        self.match_kind_filter_label = QLabel()
        self.match_kind_filter_label.setObjectName("filterLabel")
        self.match_kind_filter_group = FilterGroupFrame(minimum_height=54)
        self.match_kind_filter_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        match_kind_group_layout = self.match_kind_filter_group.row_layout
        self.match_kind_group = QButtonGroup(self)
        self.match_kind_group.setExclusive(True)
        self.match_kind_buttons: dict[str, QPushButton] = {}
        match_kind_group_layout.addWidget(self.match_kind_filter_label)
        for mode in ("all", "exact", "tax_group", "composite_group", "review_nn_group"):
            button = ChipButton(match_kind_chip_palette(mode), min_width=84, max_width=152, horizontal_padding=14)
            button.setObjectName(f"matchKindChip{mode.title().replace('_', '')}")
            self.match_kind_group.addButton(button)
            self.match_kind_buttons[mode] = button
            match_kind_group_layout.addWidget(button)
        self.match_kind_buttons["all"].setChecked(True)

        self.date_filter_label = QLabel()
        self.date_filter_label.setObjectName("filterLabel")
        self.date_range_separator = QLabel("~")
        self.date_range_separator.setObjectName("filterLabel")
        self.date_from_edit = PopupDateEdit()
        self.date_to_edit = PopupDateEdit()
        self.date_clear_button = QPushButton()
        self.date_clear_button.setMinimumHeight(36)
        self.date_clear_button.setFixedWidth(116)
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.setCalendarPopup(True)
            widget.setDisplayFormat("yyyy-MM-dd")
            widget.setMinimumHeight(36)
            widget.setFixedWidth(132)
        self.date_filter_group = FilterGroupFrame()
        date_group_layout = self.date_filter_group.row_layout
        date_group_layout.addWidget(self.date_filter_label)
        date_group_layout.addWidget(self.date_from_edit)
        date_group_layout.addWidget(self.date_range_separator)
        date_group_layout.addWidget(self.date_to_edit)
        date_group_layout.addWidget(self.date_clear_button)

        self.quick_search_edit = QLineEdit()
        self.quick_search_edit.setClearButtonEnabled(True)
        self.quick_search_edit.setMinimumHeight(36)
        self.quick_search_edit.setMinimumWidth(260)
        self.quick_search_group = FilterGroupFrame()
        quick_search_layout = self.quick_search_group.row_layout
        quick_search_layout.addWidget(self.quick_search_edit)

        self.filter_controls_layout.addWidget(self.reference_filter_group)
        self.filter_controls_layout.addWidget(self.flow_filter_group)
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
        self.summary_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        summary_group_layout = QHBoxLayout(self.summary_group)
        summary_group_layout.setContentsMargins(10, 8, 10, 8)
        summary_group_layout.setSpacing(8)
        self.summary_grid_label = QLabel()
        self.summary_grid_label.setObjectName("summaryGridLabel")
        summary_group_layout.addWidget(self.summary_grid_label)

        self.summary_buttons_widget = QWidget(self.summary_group)
        self.summary_buttons_widget.setObjectName("summaryButtons")
        self.summary_buttons_widget.setMinimumHeight(36)
        self.summary_buttons_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.summary_buttons_layout = QGridLayout(self.summary_buttons_widget)
        self.summary_buttons_layout.setContentsMargins(0, 0, 0, 0)
        self.summary_buttons_layout.setHorizontalSpacing(8)
        self.summary_buttons_layout.setVerticalSpacing(6)
        self.summary_filter_group = QButtonGroup(self)
        self.summary_filter_group.setExclusive(True)
        self.summary_filter_buttons: dict[str, QPushButton] = {}
        for mode, object_name in (
            ("all", "summaryChipAll"),
            ("matched", "summaryChipMatched"),
            ("review", "summaryChipReview"),
            ("unmatched", "summaryChipUnmatched"),
        ):
            button = ChipButton(summary_chip_palette(mode), min_width=84, max_width=164, horizontal_padding=14)
            button.setObjectName(object_name)
            self.summary_filter_group.addButton(button)
            self.summary_filter_buttons[mode] = button
        self.summary_filter_buttons["all"].setChecked(True)
        self.summary_help_button = InstantToolTipButton()
        self.summary_help_button.setObjectName("summaryHelpButton")
        self.summary_help_button.setText("!")
        self.summary_help_button.setCursor(Qt.PointingHandCursor)
        self.summary_help_button.setAutoRaise(True)
        summary_group_layout.addWidget(self.summary_buttons_widget, 0, Qt.AlignLeft | Qt.AlignVCenter)
        self.reflow_summary_buttons(width_hint=1520)
        self.toolbar_groups_layout.insertWidget(0, self.summary_group, 0)
        self.toolbar_groups_layout.addWidget(self.match_kind_filter_group, 0, Qt.AlignLeft)
        self.toolbar_groups_layout.addStretch(1)

        self.summary_actions = SummaryActionsBar()
        self.summary_actions.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.clear_filters_button = QPushButton()
        self.clear_filters_button.setFixedWidth(156)
        self.clear_filters_button.setFixedHeight(36)
        self.swap_button = QPushButton()
        self.swap_button.setFixedWidth(148)
        self.swap_button.setFixedHeight(36)
        self.summary_row_layout.addWidget(self.summary_actions, 0)
        self.summary_row_layout.addStretch(1)
        self.summary_row_layout.addWidget(self.clear_filters_button)
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
        self.root_layout.addWidget(self.results_card)

        self.system_grid = DataGridPanel()
        self.bank_grid = DataGridPanel()
        self.system_page = self._wrap_grid_panel(self.system_grid)
        self.bank_page = self._wrap_grid_panel(self.bank_grid)
        self.grid_stack.addWidget(self.system_page)
        self.grid_stack.addWidget(self.bank_page)
        self.grid_stack.setCurrentWidget(self.bank_page)

    def attach_file_panel(self, file_panel: FilePickerPanel) -> None:
        current_parent = file_panel.parentWidget()
        if current_parent is not None and current_parent.layout() is not None:
            current_parent.layout().removeWidget(file_panel)
        file_panel.setParent(None)
        self.top_layout.insertWidget(0, file_panel, 3, Qt.AlignTop)

    def apply_metadata_layout(self, mode: str) -> None:
        if self._metric_layout_mode == mode:
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
        self._metric_layout_mode = mode

    def reflow_summary_buttons(self, width_hint: int) -> None:
        while self.summary_buttons_layout.count():
            item = self.summary_buttons_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self.summary_buttons_layout.removeWidget(widget)

        if width_hint < 900:
            columns = 2
        elif width_hint < 1250:
            columns = 3
        else:
            columns = 5

        ordered_widgets = [
            self.summary_filter_buttons["all"],
            self.summary_filter_buttons["matched"],
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

    def update_grid_heights(
        self,
        active_grid_mode: str,
        system_proxy,
        bank_proxy,
    ) -> None:
        grids = (
            ("system", self.system_grid, system_proxy),
            ("bank", self.bank_grid, bank_proxy),
        )
        heights: dict[str, int] = {}
        for mode, grid, proxy in grids:
            table_model = grid.table.model()
            visible_rows = table_model.rowCount() if table_model is not None else (proxy.rowCount() if proxy else 0)
            table_height = self._table_target_height(grid.table, visible_rows)
            panel_height = table_height + self._grid_panel_extra_height(grid)
            grid.table.setMinimumHeight(table_height)
            grid.table.setMaximumHeight(table_height)
            grid.setMinimumHeight(panel_height)
            grid.setMaximumHeight(panel_height)
            heights[mode] = panel_height
        active_height = heights.get(active_grid_mode, 360)
        self.grid_stack.setMinimumHeight(active_height)
        self.grid_stack.setMaximumHeight(active_height)

    def apply_responsive_layout(self, width: int, active_grid_mode: str, system_proxy, bank_proxy, file_panel: FilePickerPanel) -> None:
        if width < 1180:
            self.root_layout.setContentsMargins(12, 12, 12, 12)
        else:
            self.root_layout.setContentsMargins(18, 18, 18, 18)
        self.root_layout.setSpacing(14)

        top_vertical = width < 1400
        self.top_layout.setDirection(QBoxLayout.TopToBottom if top_vertical else QBoxLayout.LeftToRight)
        file_panel.setMaximumWidth(16777215 if top_vertical else 500)
        file_panel.setMinimumWidth(0)
        file_panel.system_path_edit.setMaximumWidth(16777215)
        file_panel.bank_path_edit.setMaximumWidth(16777215)

        if width < 860:
            self.apply_metadata_layout("compact")
        elif width < 1120:
            self.apply_metadata_layout("narrow")
        elif width < 1480:
            self.apply_metadata_layout("medium")
        else:
            self.apply_metadata_layout("wide")

        self.summary_row_layout.setDirection(QBoxLayout.TopToBottom if width < 1120 else QBoxLayout.LeftToRight)
        self.summary_group.setMinimumWidth(0)
        self.summary_group.setMaximumWidth(16777215)
        self.summary_group.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.summary_buttons_widget.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.toolbar_groups_layout.setDirection(QBoxLayout.TopToBottom if width < 1320 else QBoxLayout.LeftToRight)
        self.match_kind_filter_group.setMinimumWidth(0)
        self.match_kind_filter_group.setMaximumWidth(16777215)
        self.filter_controls_layout.setDirection(QBoxLayout.TopToBottom if width < 1320 else QBoxLayout.LeftToRight)
        self.reflow_summary_buttons(width)
        self.update_grid_heights(active_grid_mode, system_proxy, bank_proxy)

    @staticmethod
    def _wrap_grid_panel(panel: QWidget) -> QWidget:
        page = QWidget()
        page.setObjectName("gridPage")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(panel, 0, Qt.AlignTop)
        layout.addStretch(1)
        return page

    @staticmethod
    def _grid_panel_extra_height(grid: DataGridPanel) -> int:
        title_height = max(grid.title.sizeHint().height(), grid.count.sizeHint().height(), 22)
        filter_height = grid.search.sizeHint().height() if grid.search.isVisible() else 0
        return 24 + title_height + filter_height + 24

    @staticmethod
    def _table_target_height(table: FrozenTableView, visible_rows: int) -> int:
        rows_to_show = max(1, min(visible_rows, 25))
        header_height = max(table.horizontalHeader().height(), table.horizontalHeader().sizeHint().height(), 28)
        row_height = table.rowHeight(0) if visible_rows > 0 else table.verticalHeader().defaultSectionSize()
        row_height = max(row_height, 24)
        horizontal_scroll_height = table.horizontalScrollBar().sizeHint().height() + 4
        frame_height = table.frameWidth() * 2
        return header_height + (rows_to_show * row_height) + horizontal_scroll_height + frame_height + 4
