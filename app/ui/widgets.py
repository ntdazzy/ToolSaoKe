from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)


class FrozenTableView(QTableView):
    action_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().hide()
        self.setAlternatingRowColors(False)
        self.doubleClicked.connect(self._handle_double_click)

    def set_action_delegate(self, delegate) -> None:
        self.setItemDelegateForColumn(0, delegate)

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
        self.resizeColumnsToContents()
        widths = fixed_widths or {}
        for column in range(model.columnCount()):
            if column in widths:
                width = widths[column]
            else:
                measured = self.columnWidth(column) + padding
                width = max(min_width, min(measured, max_auto_width))
            self.setColumnWidth(column, width)

    def _handle_double_click(self, index) -> None:
        row = index.data(Qt.UserRole)
        self.action_requested.emit(row)


class PopupDateEdit(QDateEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._calendar_bound = False

    def _ensure_calendar_binding(self) -> None:
        if self._calendar_bound:
            return
        calendar = self.calendarWidget()
        calendar.clicked.connect(self._apply_calendar_date)
        calendar.activated.connect(self._apply_calendar_date)
        self._calendar_bound = True

    def _apply_calendar_date(self, date) -> None:
        self.setDate(date)
        self.calendarWidget().hide()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self.calendarPopup():
            self._ensure_calendar_binding()
            calendar = self.calendarWidget()
            calendar.setWindowFlag(Qt.Popup, True)
            calendar.setSelectedDate(self.date())
            calendar.move(self.mapToGlobal(self.rect().bottomLeft()))
            calendar.show()
            calendar.raise_()
            calendar.activateWindow()


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self._blur_targets: list[QWidget] = []
        self._spinner_frames = ["|", "/", "-", "\\"]
        self._spinner_index = 0
        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(90)
        self._spinner_timer.timeout.connect(self._advance_spinner)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.card = QFrame(self)
        self.card.setObjectName("loadingCard")
        self.card.setMinimumWidth(180)
        self.card.setMaximumWidth(240)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(26, 22, 26, 22)
        card_layout.setSpacing(10)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(Qt.black)
        self.card.setGraphicsEffect(shadow)

        self.spinner = QLabel(self._spinner_frames[0])
        self.spinner.setAlignment(Qt.AlignCenter)
        self.spinner.setObjectName("loadingSpinner")

        self.title = QLabel("Loading")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setObjectName("loadingLabel")

        card_layout.addWidget(self.spinner)
        card_layout.addWidget(self.title)
        layout.addWidget(self.card, alignment=Qt.AlignCenter)
        self.hide()

    def set_message(self, text: str) -> None:
        self.title.setText(text or "Loading")

    def set_blur_targets(self, targets: list[QWidget]) -> None:
        self._blur_targets = targets

    def _advance_spinner(self) -> None:
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_frames)
        self.spinner.setText(self._spinner_frames[self._spinner_index])

    def _set_blur_enabled(self, enabled: bool) -> None:
        for target in self._blur_targets:
            if enabled:
                effect = QGraphicsBlurEffect(target)
                effect.setBlurRadius(10)
                target.setGraphicsEffect(effect)
            else:
                target.setGraphicsEffect(None)

    def showEvent(self, event) -> None:
        self._spinner_index = 0
        self.spinner.setText(self._spinner_frames[self._spinner_index])
        self._spinner_timer.start()
        self._set_blur_enabled(True)
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._spinner_timer.stop()
        self._set_blur_enabled(False)
        super().hideEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.parent() and event.type() == QEvent.Resize:
            self.resize(watched.size())
        return super().eventFilter(watched, event)

    def bind_parent(self) -> None:
        if self.parent():
            self.parent().installEventFilter(self)
            self.resize(self.parent().size())
