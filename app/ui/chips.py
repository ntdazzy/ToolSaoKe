from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QPushButton, QSizePolicy, QWidget


@dataclass(frozen=True)
class ChipPalette:
    background: str
    border: str
    text: str
    hover_border: str = "#60a5fa"
    active_background: str | None = None
    active_border: str = "#3b82f6"
    active_text: str | None = None


class ChipButton(QPushButton):
    def __init__(
        self,
        palette: ChipPalette,
        *,
        min_width: int = 84,
        max_width: int = 176,
        horizontal_padding: int = 14,
        fixed_height: int = 36,
        radius: int = 18,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._palette = palette
        self._base_min_width = min_width
        self._max_width = max_width
        self._horizontal_padding = horizontal_padding
        self._fixed_height = fixed_height
        self._radius = radius
        self._font = QFont(self.font())
        self._font.setPointSize(11)
        self._font.setWeight(QFont.DemiBold)
        self.setFont(self._font)
        self.setCursor(Qt.PointingHandCursor)
        self.setAutoDefault(False)
        self.setDefault(False)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.setCheckable(True)
        self.setFixedHeight(self._fixed_height)
        self.setMaximumWidth(self._max_width)
        self._sync_width()

    def setText(self, text: str) -> None:
        super().setText(text)
        self._sync_width()
        self.update()

    def sizeHint(self) -> QSize:
        metrics = QFontMetrics(self.font())
        width = max(
            self._base_min_width,
            metrics.horizontalAdvance(self.text()) + (self._horizontal_padding * 2) + 12,
        )
        width = min(width, self._max_width)
        return QSize(width, self._fixed_height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)

        background, border, text_color = self._state_colors()
        painter.setBrush(background)
        pen = QPen(border, 1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        radius = min(float(self._radius), rect.height() / 2.0)
        painter.drawRoundedRect(rect, radius, radius)

        painter.setFont(self.font())
        painter.setPen(text_color)
        text_rect = rect.adjusted(float(self._horizontal_padding), 0.0, -float(self._horizontal_padding), 0.0)
        metrics = painter.fontMetrics()
        text = metrics.elidedText(self.text(), Qt.ElideRight, int(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignCenter, text)
        painter.end()

    def _state_colors(self) -> tuple[QColor, QColor, QColor]:
        palette = self._palette
        is_active = self.isChecked() or self.isDown()
        is_hovered = self.underMouse()

        background = QColor(palette.background)
        border = QColor(palette.border)
        text = QColor(palette.text)

        if is_hovered:
            border = QColor(palette.hover_border)

        if is_active:
            background = QColor(palette.active_background or palette.background)
            border = QColor(palette.active_border)
            text = QColor(palette.active_text or palette.text)

        if not self.isEnabled():
            background.setAlpha(160)
            border.setAlpha(160)
            text.setAlpha(140)

        return background, border, text

    def _sync_width(self) -> None:
        hint = self.sizeHint()
        self.setMinimumWidth(hint.width())
        self.setMaximumWidth(self._max_width)
        self.updateGeometry()


def summary_chip_palette(mode: str) -> ChipPalette:
    palettes = {
        "all": ChipPalette("#eff4fb", "#d7e1ef", "#475569"),
        "matched": ChipPalette("#dcfce7", "#bbf7d0", "#166534"),
        "matched_exact": ChipPalette("#dcfce7", "#bbf7d0", "#166534"),
        "matched_group": ChipPalette("#dbeafe", "#bfdbfe", "#1d4ed8"),
        "review": ChipPalette("#fef3c7", "#fde68a", "#92400e"),
        "unmatched": ChipPalette("#fecdd3", "#fda4af", "#be123c"),
    }
    return palettes[mode]


def flow_chip_palette() -> ChipPalette:
    return ChipPalette(
        "#eff4fb",
        "#d7e1ef",
        "#475569",
        active_background="#ffffff",
        active_border="#3b82f6",
        active_text="#1d4ed8",
    )


def match_kind_chip_palette(mode: str) -> ChipPalette:
    palettes = {
        "all": ChipPalette(
            "#eff4fb",
            "#d7e1ef",
            "#475569",
            active_background="#ffffff",
            active_border="#3b82f6",
            active_text="#1d4ed8",
        ),
        "exact": ChipPalette("#dcfce7", "#bbf7d0", "#166534"),
        "tax_group": ChipPalette("#dbeafe", "#bfdbfe", "#1d4ed8"),
        "composite_group": ChipPalette("#ede9fe", "#ddd6fe", "#6d28d9"),
        "review_nn_group": ChipPalette("#fef3c7", "#fde68a", "#92400e"),
    }
    return palettes[mode]
