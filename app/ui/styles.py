from __future__ import annotations


MAIN_WINDOW_STYLESHEET = """
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
    background: rgba(236, 242, 249, 84);
}
QFrame#card, QFrame#resultsCard, QFrame#panelCard, QFrame#metricCard {
    background: #ffffff;
    border: 1px solid #dbe4f0;
    border-radius: 16px;
}
QFrame#loadingCard {
    background: rgba(255, 255, 255, 238);
    border: 1px solid rgba(255, 255, 255, 210);
    border-radius: 24px;
}
QFrame#filterGroup {
    background: #f7faff;
    border: 1px solid #dbe4f0;
    border-radius: 14px;
}
QFrame#summaryActions {
    background: #f7faff;
    border: 1px solid #dbe4f0;
    border-radius: 14px;
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
    border-radius: 14px;
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
    min-width: 84px;
    border-radius: 18px;
    padding: 0 14px;
    border-width: 1px;
    border-style: solid;
}
QPushButton#flowChipAll,
QPushButton#flowChipIncome,
QPushButton#flowChipExpense,
QPushButton#flowChipTax {
    font-size: 11px;
    font-weight: 700;
    min-height: 0px;
    max-height: 36px;
    min-width: 96px;
    border-radius: 18px;
    padding: 0 14px;
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
QPushButton#flowChipAll,
QPushButton#flowChipIncome,
QPushButton#flowChipExpense,
QPushButton#flowChipTax {
    background: #eff4fb;
    border-color: #d7e1ef;
    color: #475569;
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
QPushButton#summaryChipUnmatched:checked:hover,
QPushButton#summaryChipAll:checked:pressed,
QPushButton#summaryChipExact:checked:pressed,
QPushButton#summaryChipGroup:checked:pressed,
QPushButton#summaryChipReview:checked:pressed,
QPushButton#summaryChipUnmatched:checked:pressed {
    border-width: 1px;
    border-style: solid;
    border-radius: 18px;
    padding: 0 14px;
    border-color: #3b82f6;
}
QPushButton#flowChipAll:checked,
QPushButton#flowChipIncome:checked,
QPushButton#flowChipExpense:checked,
QPushButton#flowChipTax:checked,
QPushButton#flowChipAll:pressed,
QPushButton#flowChipIncome:pressed,
QPushButton#flowChipExpense:pressed,
QPushButton#flowChipTax:pressed,
QPushButton#flowChipAll:checked:hover,
QPushButton#flowChipIncome:checked:hover,
QPushButton#flowChipExpense:checked:hover,
QPushButton#flowChipTax:checked:hover,
QPushButton#flowChipAll:checked:pressed,
QPushButton#flowChipIncome:checked:pressed,
QPushButton#flowChipExpense:checked:pressed,
QPushButton#flowChipTax:checked:pressed {
    background: #ffffff;
    border-width: 1px;
    border-style: solid;
    border-radius: 18px;
    padding: 0 14px;
    border-color: #3b82f6;
    color: #1d4ed8;
}
QPushButton#summaryChipAll:hover,
QPushButton#summaryChipExact:hover,
QPushButton#summaryChipGroup:hover,
QPushButton#summaryChipReview:hover,
QPushButton#summaryChipUnmatched:hover {
    border-width: 1px;
    border-style: solid;
    border-radius: 18px;
    padding: 0 14px;
    border-color: #60a5fa;
}
QPushButton#flowChipAll:hover,
QPushButton#flowChipIncome:hover,
QPushButton#flowChipExpense:hover,
QPushButton#flowChipTax:hover {
    background: #f8fbff;
    border-width: 1px;
    border-style: solid;
    border-radius: 18px;
    padding: 0 14px;
    border-color: #60a5fa;
    color: #334155;
}
QPushButton#summaryChipAll:focus,
QPushButton#summaryChipExact:focus,
QPushButton#summaryChipGroup:focus,
QPushButton#summaryChipReview:focus,
QPushButton#summaryChipUnmatched:focus,
QPushButton#flowChipAll:focus,
QPushButton#flowChipIncome:focus,
QPushButton#flowChipExpense:focus,
QPushButton#flowChipTax:focus {
    border-width: 1px;
    border-style: solid;
    border-radius: 18px;
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
QFrame#resultsCard QPushButton#summaryChipUnmatched,
QFrame#resultsCard QPushButton#flowChipAll,
QFrame#resultsCard QPushButton#flowChipIncome,
QFrame#resultsCard QPushButton#flowChipExpense,
QFrame#resultsCard QPushButton#flowChipTax {
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
QLabel#loadingBadge {
    background: #e8f0ff;
    color: #2563eb;
    border: 1px solid #bfdbfe;
    border-radius: 999px;
    padding: 4px 10px;
    font-size: 10px;
    font-weight: 800;
}
QLabel#loadingLabel {
    font-size: 19px;
    font-weight: 500;
    color: #111827;
}
QLabel#loadingHint {
    color: #475569;
    font-size: 14px;
    font-weight: 500;
    line-height: 1.4;
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
QPushButton#summaryChipAll,
QPushButton#summaryChipExact,
QPushButton#summaryChipGroup,
QPushButton#summaryChipReview,
QPushButton#summaryChipUnmatched,
QPushButton#flowChipAll,
QPushButton#flowChipIncome,
QPushButton#flowChipExpense,
QPushButton#flowChipTax {
    border-radius: 18px;
    border-width: 1px;
    border-style: solid;
    padding: 0 14px;
}
QPushButton#summaryChipAll,
QPushButton#summaryChipAll:hover,
QPushButton#summaryChipAll:pressed,
QPushButton#summaryChipAll:checked,
QPushButton#summaryChipAll:checked:hover,
QPushButton#summaryChipAll:checked:pressed {
    background-color: #eff4fb;
    color: #475569;
}
QPushButton#summaryChipExact,
QPushButton#summaryChipExact:hover,
QPushButton#summaryChipExact:pressed,
QPushButton#summaryChipExact:checked,
QPushButton#summaryChipExact:checked:hover,
QPushButton#summaryChipExact:checked:pressed {
    background-color: #dcfce7;
    color: #166534;
}
QPushButton#summaryChipGroup,
QPushButton#summaryChipGroup:hover,
QPushButton#summaryChipGroup:pressed,
QPushButton#summaryChipGroup:checked,
QPushButton#summaryChipGroup:checked:hover,
QPushButton#summaryChipGroup:checked:pressed {
    background-color: #dbeafe;
    color: #1d4ed8;
}
QPushButton#summaryChipReview,
QPushButton#summaryChipReview:hover,
QPushButton#summaryChipReview:pressed,
QPushButton#summaryChipReview:checked,
QPushButton#summaryChipReview:checked:hover,
QPushButton#summaryChipReview:checked:pressed {
    background-color: #fef3c7;
    color: #92400e;
}
QPushButton#summaryChipUnmatched,
QPushButton#summaryChipUnmatched:hover,
QPushButton#summaryChipUnmatched:pressed,
QPushButton#summaryChipUnmatched:checked,
QPushButton#summaryChipUnmatched:checked:hover,
QPushButton#summaryChipUnmatched:checked:pressed {
    background-color: #fecdd3;
    color: #be123c;
}
QPushButton#flowChipAll,
QPushButton#flowChipAll:hover,
QPushButton#flowChipIncome,
QPushButton#flowChipIncome:hover,
QPushButton#flowChipExpense,
QPushButton#flowChipExpense:hover,
QPushButton#flowChipTax,
QPushButton#flowChipTax:hover {
    background-color: #eff4fb;
    color: #475569;
}
QPushButton#flowChipAll:checked,
QPushButton#flowChipIncome:checked,
QPushButton#flowChipExpense:checked,
QPushButton#flowChipTax:checked,
QPushButton#flowChipAll:pressed,
QPushButton#flowChipIncome:pressed,
QPushButton#flowChipExpense:pressed,
QPushButton#flowChipTax:pressed,
QPushButton#flowChipAll:checked:hover,
QPushButton#flowChipIncome:checked:hover,
QPushButton#flowChipExpense:checked:hover,
QPushButton#flowChipTax:checked:hover,
QPushButton#flowChipAll:checked:pressed,
QPushButton#flowChipIncome:checked:pressed,
QPushButton#flowChipExpense:checked:pressed,
QPushButton#flowChipTax:checked:pressed {
    background-color: #ffffff;
    color: #1d4ed8;
}
QPushButton#summaryChipAll,
QPushButton#summaryChipExact,
QPushButton#summaryChipGroup,
QPushButton#summaryChipReview,
QPushButton#summaryChipUnmatched,
QPushButton#flowChipAll,
QPushButton#flowChipIncome,
QPushButton#flowChipExpense,
QPushButton#flowChipTax {
    border-color: #d7e1ef;
}
QPushButton#summaryChipExact {
    border-color: #bbf7d0;
}
QPushButton#summaryChipGroup {
    border-color: #bfdbfe;
}
QPushButton#summaryChipReview {
    border-color: #fde68a;
}
QPushButton#summaryChipUnmatched {
    border-color: #fda4af;
}
QPushButton#summaryChipAll:hover,
QPushButton#summaryChipExact:hover,
QPushButton#summaryChipGroup:hover,
QPushButton#summaryChipReview:hover,
QPushButton#summaryChipUnmatched:hover,
QPushButton#flowChipAll:hover,
QPushButton#flowChipIncome:hover,
QPushButton#flowChipExpense:hover,
QPushButton#flowChipTax:hover {
    border-color: #60a5fa;
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
QPushButton#summaryChipUnmatched:checked:hover,
QPushButton#summaryChipAll:checked:pressed,
QPushButton#summaryChipExact:checked:pressed,
QPushButton#summaryChipGroup:checked:pressed,
QPushButton#summaryChipReview:checked:pressed,
QPushButton#summaryChipUnmatched:checked:pressed,
QPushButton#flowChipAll:checked,
QPushButton#flowChipIncome:checked,
QPushButton#flowChipExpense:checked,
QPushButton#flowChipTax:checked,
QPushButton#flowChipAll:pressed,
QPushButton#flowChipIncome:pressed,
QPushButton#flowChipExpense:pressed,
QPushButton#flowChipTax:pressed,
QPushButton#flowChipAll:checked:hover,
QPushButton#flowChipIncome:checked:hover,
QPushButton#flowChipExpense:checked:hover,
QPushButton#flowChipTax:checked:hover,
QPushButton#flowChipAll:checked:pressed,
QPushButton#flowChipIncome:checked:pressed,
QPushButton#flowChipExpense:checked:pressed,
QPushButton#flowChipTax:checked:pressed {
    border-color: #3b82f6;
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
