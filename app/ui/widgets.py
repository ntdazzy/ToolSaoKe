from __future__ import annotations

from PySide6.QtCore import QEvent, QRect, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTableView,
    QVBoxLayout,
    QWidget,
)


class FrozenTableView(QTableView):
    action_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._frozen_view = QTableView(self)
        self._frozen_view.setFocusPolicy(Qt.NoFocus)
        self._frozen_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._frozen_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._frozen_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._frozen_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self._frozen_view.verticalHeader().hide()
        self.viewport().stackUnder(self._frozen_view)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(False)
        self._frozen_view.setAlternatingRowColors(False)
        self.verticalHeader().sectionResized.connect(self._update_row_height)
        self.horizontalHeader().sectionResized.connect(self._update_column_width)
        self.verticalScrollBar().valueChanged.connect(
            self._frozen_view.verticalScrollBar().setValue
        )
        self._frozen_view.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)
        self.doubleClicked.connect(self._handle_double_click)
        self._frozen_view.doubleClicked.connect(self._handle_double_click)

    def setModel(self, model) -> None:  # type: ignore[override]
        super().setModel(model)
        self._frozen_view.setModel(model)
        self._frozen_view.setSelectionModel(self.selectionModel())
        for column in range(model.columnCount()):
            self._frozen_view.setColumnHidden(column, column != 0)
        self._frozen_view.setColumnWidth(0, self.columnWidth(0))
        self._update_frozen_geometry()

    def setSelectionModel(self, selection_model) -> None:  # type: ignore[override]
        super().setSelectionModel(selection_model)
        self._frozen_view.setSelectionModel(selection_model)

    def set_action_delegate(self, delegate) -> None:
        self.setItemDelegateForColumn(0, delegate)
        self._frozen_view.setItemDelegateForColumn(0, delegate)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._update_frozen_geometry()

    def moveCursor(self, cursor_action, modifiers):  # type: ignore[override]
        current = super().moveCursor(cursor_action, modifiers)
        if (
            cursor_action == QAbstractItemView.MoveLeft
            and current.column() > 0
            and self.visualRect(current).topLeft().x() < self._frozen_view.columnWidth(0)
        ):
            new_value = self.horizontalScrollBar().value() + self.visualRect(current).topLeft().x()
            self.horizontalScrollBar().setValue(new_value)
        return current

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible) -> None:  # type: ignore[override]
        if index.column() > 0:
            super().scrollTo(index, hint)

    def select_proxy_index(self, index) -> None:
        if not index.isValid():
            return
        self.selectRow(index.row())
        self.scrollTo(index, QAbstractItemView.PositionAtCenter)

    def auto_fit_columns(
        self,
        fixed_widths: dict[int, int] | None = None,
        *,
        min_width: int = 72,
        max_auto_width: int = 180,
        padding: int = 18,
    ) -> None:
        model = self.model()
        if model is None:
            return
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._frozen_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.resizeColumnsToContents()
        widths = fixed_widths or {}
        for column in range(model.columnCount()):
            if column in widths:
                width = widths[column]
            else:
                measured = self.columnWidth(column) + padding
                width = max(min_width, min(measured, max_auto_width))
            self.setColumnWidth(column, width)
        self._update_frozen_geometry()

    def _update_row_height(self, logical_index: int, _old_size: int, new_size: int) -> None:
        self._frozen_view.setRowHeight(logical_index, new_size)

    def _update_column_width(self, logical_index: int, _old_size: int, new_size: int) -> None:
        if logical_index == 0:
            self._frozen_view.setColumnWidth(0, new_size)
            self._update_frozen_geometry()

    def _update_frozen_geometry(self) -> None:
        frame_width = self.frameWidth()
        header_height = self.horizontalHeader().height()
        self._frozen_view.setGeometry(
            QRect(
                frame_width,
                frame_width,
                self.columnWidth(0) + 2,
                self.viewport().height() + header_height,
            )
        )

    def _handle_double_click(self, index) -> None:
        row = index.data(Qt.UserRole)
        self.action_requested.emit(row)


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self.setStyleSheet("background: rgba(15, 23, 42, 120);")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame(self)
        card.setObjectName("loadingCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 24, 28, 24)
        card_layout.setSpacing(12)

        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setObjectName("loadingLabel")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(240)

        card_layout.addWidget(self.label)
        card_layout.addWidget(self.progress, alignment=Qt.AlignCenter)
        layout.addWidget(card, alignment=Qt.AlignCenter)
        self.hide()

    def set_message(self, text: str) -> None:
        self.label.setText(text)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.parent() and event.type() == QEvent.Resize:
            self.resize(watched.size())
        return super().eventFilter(watched, event)

    def bind_parent(self) -> None:
        if self.parent():
            self.parent().installEventFilter(self)
            self.resize(self.parent().size())
