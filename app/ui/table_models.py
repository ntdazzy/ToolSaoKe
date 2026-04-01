from __future__ import annotations

from datetime import date
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.i18n import tr
from app.services.utils import normalize_text, parse_vnd_int


STATUS_COLORS = {
    "matched_exact": QColor("#f8fbff"),
    "review": QColor("#fef3c7"),
    "unmatched": QColor("#fecdd3"),
}

GROUP_COLORS = [
    QColor("#e9f2ff"),
    QColor("#eefbf3"),
    QColor("#fff5e8"),
    QColor("#f6efff"),
    QColor("#eef8fb"),
    QColor("#fff2f7"),
]


def status_bucket_for_row(row) -> str:
    if getattr(row, "status", "unmatched") == "matched":
        return "matched_group" if getattr(row, "match_type", "none") == "group" else "matched_exact"
    if getattr(row, "status", "unmatched") == "review":
        return "review"
    return "unmatched"


def group_color_for_row(row) -> QColor | None:
    group_id = getattr(row, "group_id", None)
    if getattr(row, "match_type", "none") != "group" or not group_id:
        return None
    color_index = sum(ord(character) for character in group_id) % len(GROUP_COLORS)
    return GROUP_COLORS[color_index]


def row_background_color(row) -> QColor:
    group_color = group_color_for_row(row)
    if group_color is not None and getattr(row, "status", "unmatched") == "matched":
        return group_color
    return STATUS_COLORS.get(status_bucket_for_row(row), QColor("#f8fbff"))


class TransactionsTableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[object], language: str = "vi") -> None:
        super().__init__()
        self._headers = headers
        self._rows = rows
        self._language = language
        self._row_lookup = {row.row_id: index for index, row in enumerate(rows)}
        self._numeric_columns = {
            index
            for index, header in enumerate(headers)
            if any(
                marker in header
                for marker in ("金额", "余额", "Nợ", "Có", "Chi", "Thu", "Phí", "Thuế", "Số dư", "Total")
            )
        }

    def set_language(self, language: str) -> None:
        self._language = language
        self.layoutChanged.emit()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == Qt.DisplayRole:
            return row.display_values[index.column()]
        if role == Qt.TextAlignmentRole:
            if index.column() in self._numeric_columns:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.ForegroundRole:
            if index.column() in self._numeric_columns:
                value = row.display_values[index.column()]
                if parse_vnd_int(value) < 0:
                    return QColor("#dc2626")
        if role == Qt.BackgroundRole:
            return row_background_color(row)
        if role == Qt.ToolTipRole:
            status_text = tr(self._language, status_bucket_for_row(row))
            reasons = [segment.strip() for segment in (row.match_reason or "").splitlines() if segment.strip()]
            reason_text = "\n".join(f"- {item}" for item in reasons)
            group_id = getattr(row, "group_id", None)
            group_text = f"\nGroup: {group_id}" if group_id else ""
            return f"{status_text}{group_text}\n{reason_text}".strip()
        if role == Qt.UserRole:
            return row
        if role == Qt.UserRole + 1:
            return row.row_id
        if role == Qt.UserRole + 2:
            value = row.display_values[index.column()]
            if index.column() in self._numeric_columns:
                return parse_vnd_int(value)
            return normalize_text(value)
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return section + 1

    def row_object(self, row_index: int) -> object:
        return self._rows[row_index]

    def row_index_by_id(self, row_id: str) -> int | None:
        return self._row_lookup.get(row_id)

    @property
    def total_rows(self) -> int:
        return len(self._rows)


class TransactionsFilterProxyModel(QSortFilterProxyModel):
    def __init__(self) -> None:
        super().__init__()
        self._status_mode = "all"
        self._flow_mode = "all"
        self._reference_mode = "all"
        self._search_text = ""
        self._search_column = -1
        self._date_from: date | None = None
        self._date_to: date | None = None
        self.setDynamicSortFilter(True)

    def set_status_mode(self, mode: str) -> None:
        self._status_mode = mode
        self.invalidateFilter()

    def set_flow_mode(self, mode: str) -> None:
        self._flow_mode = mode
        self.invalidateFilter()

    def set_reference_mode(self, mode: str) -> None:
        self._reference_mode = mode.upper() if mode and mode != "all" else "all"
        self.invalidateFilter()

    def set_search_text(self, value: str) -> None:
        self._search_text = normalize_text(value)
        self.invalidateFilter()

    def set_search_column(self, value: int) -> None:
        self._search_column = value
        self.invalidateFilter()

    def set_date_range(self, date_from: date | None, date_to: date | None) -> None:
        self._date_from = date_from
        self._date_to = date_to
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: TransactionsTableModel = self.sourceModel()  # type: ignore[assignment]
        row = model.row_object(source_row)
        return self._accepts_row_object(row, self._status_mode)

    def count_for_status_mode(self, mode: str) -> int:
        model: TransactionsTableModel | None = self.sourceModel()  # type: ignore[assignment]
        if model is None:
            return 0
        return sum(
            1
            for source_row in range(model.rowCount())
            if self._accepts_row_object(model.row_object(source_row), mode)
        )

    def _accepts_row_object(self, row, status_mode: str) -> bool:
        row_bucket = status_bucket_for_row(row)
        if status_mode == "matched_exact" and row_bucket != "matched_exact":
            return False
        if status_mode == "matched_group" and row_bucket != "matched_group":
            return False
        if status_mode == "review" and row_bucket != "review":
            return False
        if status_mode == "unmatched" and row_bucket != "unmatched":
            return False
        if self._flow_mode == "income" and row.direction != "income":
            return False
        if self._flow_mode == "expense" and row.direction != "expense":
            return False
        if self._flow_mode == "tax":
            if hasattr(row, "vat"):
                if abs(getattr(row, "vat", 0)) <= 0:
                    return False
            elif not bool(getattr(row, "matched_tax", False)):
                return False
        if self._reference_mode != "all":
            if self._reference_mode not in row.reference_prefixes:
                return False
        if self._date_from is not None or self._date_to is not None:
            row_date = self._row_date(row)
            if row_date is None:
                return False
            if self._date_from is not None and row_date < self._date_from:
                return False
            if self._date_to is not None and row_date > self._date_to:
                return False
        if self._search_text:
            values = row.display_values
            if self._search_column >= 0 and self._search_column < len(values):
                haystack = normalize_text(values[self._search_column])
            else:
                haystack = normalize_text(" ".join(values))
            if self._search_text not in haystack:
                return False
        return True

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_row = left.data(Qt.UserRole)
        right_row = right.data(Qt.UserRole)
        if left_row is not None and right_row is not None:
            left_group = getattr(left_row, "group_id", None)
            right_group = getattr(right_row, "group_id", None)
            if self._status_mode == "matched_group":
                if left_group != right_group:
                    return str(left_group or "") < str(right_group or "")
                left_order = getattr(left_row, "group_order", getattr(left_row, "excel_row", 0))
                right_order = getattr(right_row, "group_order", getattr(right_row, "excel_row", 0))
                if left_order != right_order:
                    return left_order < right_order
            elif left_group and left_group == right_group:
                left_order = getattr(left_row, "group_order", getattr(left_row, "excel_row", 0))
                right_order = getattr(right_row, "group_order", getattr(right_row, "excel_row", 0))
                if left_order != right_order:
                    return left_order < right_order

        left_value = left.data(self.sortRole())
        right_value = right.data(self.sortRole())
        if isinstance(left_value, (int, float)) and isinstance(right_value, (int, float)):
            return left_value < right_value
        return str(left_value or "") < str(right_value or "")

    @staticmethod
    def _row_date(row) -> date | None:
        voucher_date = getattr(row, "voucher_date", None)
        if voucher_date is not None:
            return voucher_date
        transaction_date = getattr(row, "transaction_date", None)
        if transaction_date is not None:
            return transaction_date
        requesting_datetime = getattr(row, "requesting_datetime", None)
        if requesting_datetime is not None:
            return requesting_datetime.date()
        return None


class ActionButtonDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index) -> None:  # type: ignore[override]
        if index.column() != 0:
            super().paint(painter, option, index)
            return
        painter.save()
        rect = option.rect.adjusted(8, 6, -8, -6)
        color = QColor("#dbeafe") if option.state & QStyle.State_MouseOver else QColor("#c7d2fe")
        border = QColor("#4f46e5")
        text = str(index.data() or "")
        painter.setRenderHint(painter.RenderHint.Antialiasing)
        painter.setPen(border)
        painter.setBrush(color)
        painter.drawRoundedRect(rect, 10, 10)
        painter.drawText(rect, Qt.AlignCenter, text)
        painter.restore()
