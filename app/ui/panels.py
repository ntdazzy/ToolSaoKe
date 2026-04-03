from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.ui.widgets import FrozenTableView, StyledCheckBox, StyledComboBox


class FilePickerPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QGridLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setHorizontalSpacing(8)
        layout.setVerticalSpacing(8)
        layout.setColumnStretch(1, 1)

        self.system_file_label = QLabel()
        self.bank_file_label = QLabel()
        self.language_label = QLabel()

        self.system_path_edit = QLineEdit()
        self.system_path_edit.setReadOnly(True)
        self.system_path_edit.setMinimumHeight(38)

        self.bank_path_edit = QLineEdit()
        self.bank_path_edit.setReadOnly(True)
        self.bank_path_edit.setMinimumHeight(38)

        self.system_choose_button = QPushButton()
        self.bank_choose_button = QPushButton()
        for button in (self.system_choose_button, self.bank_choose_button):
            button.setFixedWidth(126)
            button.setMinimumHeight(38)

        self.language_combo = StyledComboBox()
        self.language_combo.setObjectName("compactCombo")
        self.language_combo.setMaximumWidth(158)
        self.language_combo.setFixedHeight(28)

        self.scan_button = QPushButton()
        self.scan_button.setFixedWidth(126)
        self.scan_button.setMinimumHeight(38)

        layout.addWidget(self.system_file_label, 0, 0)
        layout.addWidget(self.system_path_edit, 0, 1)
        layout.addWidget(self.system_choose_button, 0, 2)
        layout.addWidget(self.bank_file_label, 1, 0)
        layout.addWidget(self.bank_path_edit, 1, 1)
        layout.addWidget(self.bank_choose_button, 1, 2)
        layout.addWidget(self.language_label, 2, 0)

        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)
        controls_row.addWidget(self.language_combo)
        controls_row.addStretch(1)
        controls_row.addWidget(self.scan_button)
        layout.addLayout(controls_row, 2, 1, 1, 2)


class FilterGroupFrame(QFrame):
    def __init__(
        self,
        *,
        object_name: str = "filterGroup",
        minimum_height: int | None = None,
        margins: tuple[int, int, int, int] = (10, 8, 10, 8),
        spacing: int = 8,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        if minimum_height is not None:
            self.setMinimumHeight(minimum_height)
        self.row_layout = QHBoxLayout(self)
        self.row_layout.setContentsMargins(*margins)
        self.row_layout.setSpacing(spacing)


class MetricCard(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("metricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 9, 7)
        layout.setSpacing(1)
        self.title_label = QLabel()
        self.title_label.setObjectName("metricTitle")
        self.value_label = QLabel("-")
        self.value_label.setObjectName("metricValue")
        self.value_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)


class SummaryActionsBar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("summaryActions")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)

        self.history_button = QPushButton()
        self.history_button.setFixedWidth(106)
        self.history_button.setFixedHeight(36)

        self.export_button = QPushButton()
        self.export_button.setFixedWidth(106)
        self.export_button.setFixedHeight(36)
        self.export_button.setEnabled(False)

        self.attach_statement_checkbox = StyledCheckBox()
        self.attach_statement_checkbox.setChecked(False)

        layout.addWidget(self.history_button)
        layout.addWidget(self.export_button)
        layout.addWidget(self.attach_statement_checkbox)
        layout.addStretch(1)


class DataGridPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("panelCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("sectionTitle")
        self.count = QLabel()
        self.count.setObjectName("countLabel")
        title_row.addWidget(self.title)
        title_row.addStretch(1)
        title_row.addWidget(self.count)

        filter_row = QHBoxLayout()
        self.columns = StyledComboBox()
        self.columns.setMinimumWidth(188)
        self.columns.setMinimumHeight(36)
        self.columns.hide()
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        self.search.setMinimumHeight(36)
        filter_row.addWidget(self.search, 1)

        self.table = FrozenTableView()
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(FrozenTableView.SelectRows)
        self.table.setSelectionMode(FrozenTableView.SingleSelection)
        self.table.setMinimumHeight(280)

        layout.addLayout(title_row)
        layout.addLayout(filter_row)
        layout.addWidget(self.table)
