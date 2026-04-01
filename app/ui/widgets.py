from __future__ import annotations

import math

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QComboBox,
    QDateEdit,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
    QHeaderView,
    QLabel,
    QListView,
    QTableView,
    QToolButton,
    QToolTip,
    QVBoxLayout,
    QWidget,
)


class FrozenTableView(QTableView):
    action_requested = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.NoFrame)
        self.setLineWidth(0)
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


class StyledComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        popup = QListView(self)
        popup.setObjectName("comboPopup")
        popup.setFrameShape(QFrame.NoFrame)
        popup.setLineWidth(0)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        popup.setSpacing(2)
        popup.setUniformItemSizes(False)
        self.setView(popup)
        self.setCursor(Qt.PointingHandCursor)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setFocusPolicy(Qt.NoFocus)
        popup.setFocusPolicy(Qt.NoFocus)
        popup.viewport().setFocusPolicy(Qt.NoFocus)
        self._style_popup_container()

    def _style_popup_container(self) -> None:
        container = self.view().window()
        if isinstance(container, QFrame):
            container.setObjectName("comboPopupContainer")
            container.setFrameShape(QFrame.NoFrame)
            container.setLineWidth(0)
            container.setMidLineWidth(0)
            container.setContentsMargins(0, 0, 0, 0)
            container.setWindowFlag(Qt.FramelessWindowHint, True)
            container.setWindowFlag(Qt.NoDropShadowWindowHint, True)

    def showPopup(self) -> None:
        self._style_popup_container()
        super().showPopup()
        container = self.view().window()
        if isinstance(container, QFrame):
            container.setMask(container.rect())

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(0, 0, -1, -1)
        arrow_rect = QRect(rect.right() - 29, rect.top() + 5, 23, rect.height() - 10)

        separator_pen = QPen(QColor("#dbe4f0"))
        painter.setPen(separator_pen)
        painter.drawLine(
            arrow_rect.left() - 6,
            rect.top() + 6,
            arrow_rect.left() - 6,
            rect.bottom() - 6,
        )

        arrow_pen = QPen(QColor("#64748b"), 2)
        arrow_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(arrow_pen)
        center_x = arrow_rect.center().x()
        center_y = arrow_rect.center().y() + 1
        painter.drawLine(center_x - 4, center_y - 2, center_x, center_y + 2)
        painter.drawLine(center_x, center_y + 2, center_x + 4, center_y - 2)
        painter.end()


class PopupDateEdit(QDateEdit):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._calendar_bound = False
        self.setCalendarPopup(True)
        calendar = self._calendar()
        calendar.setHorizontalHeaderFormat(QCalendarWidget.ShortDayNames)
        calendar.setMinimumWidth(320)
        calendar.setMinimumHeight(240)

    def _calendar(self) -> QCalendarWidget:
        calendar = self.calendarWidget()
        if calendar is None:
            calendar = QCalendarWidget(self)
            self.setCalendarWidget(calendar)
        return calendar

    def _ensure_calendar_binding(self) -> None:
        if self._calendar_bound:
            return
        calendar = self._calendar()
        calendar.clicked.connect(self._apply_calendar_date)
        calendar.activated.connect(self._apply_calendar_date)
        self._calendar_bound = True

    def _apply_calendar_date(self, date) -> None:
        self.setDate(date)
        self._calendar().hide()

    def mousePressEvent(self, event) -> None:
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton and self.calendarPopup():
            self._ensure_calendar_binding()
            calendar = self._calendar()
            calendar.setWindowFlag(Qt.Popup, True)
            calendar.setSelectedDate(self.date())
            calendar.move(self.mapToGlobal(self.rect().bottomLeft()))
            calendar.show()
            calendar.raise_()
            calendar.activateWindow()


class InstantToolTipButton(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)

    def _show_tooltip(self, global_pos: QPoint | None = None) -> None:
        text = self.toolTip().strip()
        if not text:
            return
        pos = global_pos or self.mapToGlobal(self.rect().bottomLeft() + QPoint(0, 6))
        QToolTip.showText(pos, text, self, self.rect(), 30000)

    def enterEvent(self, event) -> None:
        self._show_tooltip()
        super().enterEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self._show_tooltip(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        QToolTip.hideText()
        super().leaveEvent(event)


class SpinnerWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._step = 0
        self._timer = QTimer(self)
        self._timer.setInterval(85)
        self._timer.timeout.connect(self._advance)
        self.setFixedSize(30, 30)

    def start(self) -> None:
        self._step = 0
        self._timer.start()
        self.update()

    def stop(self) -> None:
        self._timer.stop()
        self.update()

    def _advance(self) -> None:
        self._step = (self._step + 1) % 8
        self.update()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        center_x = self.width() / 2
        center_y = self.height() / 2
        orbit = min(self.width(), self.height()) / 2 - 5
        radius = 2.7
        for index in range(8):
            angle = ((math.pi * 2) / 8) * index - (math.pi / 2)
            x = center_x + math.cos(angle) * orbit
            y = center_y + math.sin(angle) * orbit
            distance = (index - self._step) % 8
            alpha = max(55, 255 - (distance * 26))
            color = QColor("#2563eb")
            color.setAlpha(alpha)
            painter.setBrush(color)
            painter.drawEllipse(QPoint(int(x - radius), int(y - radius)), int(radius), int(radius))
        painter.end()


class LoadingOverlay(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("loadingOverlay")
        self.setAttribute(Qt.WA_NoSystemBackground, False)
        self._blur_targets: list[QWidget] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.card = QFrame(self)
        self.card.setObjectName("loadingCard")
        self.card.setMinimumWidth(150)
        self.card.setMaximumWidth(170)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(8)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(18)
        shadow.setOffset(0, 6)
        shadow.setColor(Qt.black)
        self.card.setGraphicsEffect(shadow)

        self.spinner = SpinnerWidget(self.card)
        self.spinner.setObjectName("loadingSpinner")

        self.title = QLabel("Loading")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setObjectName("loadingLabel")

        card_layout.addWidget(self.spinner, alignment=Qt.AlignCenter)
        card_layout.addWidget(self.title)
        layout.addWidget(self.card, alignment=Qt.AlignCenter)
        self.hide()

    def set_message(self, text: str) -> None:
        self.title.setText(text or "Loading")

    def set_blur_targets(self, targets: list[QWidget]) -> None:
        self._blur_targets = targets

    def _set_blur_enabled(self, enabled: bool) -> None:
        for target in self._blur_targets:
            if enabled:
                effect = QGraphicsBlurEffect(target)
                effect.setBlurRadius(10)
                target.setGraphicsEffect(effect)
            else:
                target.setGraphicsEffect(None)

    def showEvent(self, event) -> None:
        self.spinner.start()
        self._set_blur_enabled(True)
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self.spinner.stop()
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
