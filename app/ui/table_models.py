from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.i18n import tr
from app.services.utils import normalize_text, parse_vnd_int


STATUS_COLORS = {
    "matched": QColor("#e7f5ea"),
    "review": QColor("#fff4cc"),
    "unmatched": QColor("#fde8e8"),
}


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
                for marker in ("金额", "余额", "Nợ", "Có", "Phí", "Thuế", "Số dư", "Total")
            )
        }

    def set_language(self, language: str) -> None:
        self._language = language
        self.layoutChanged.emit()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers) + 1

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return tr(self._language, "view")
            return row.display_values[index.column() - 1]
        if role == Qt.TextAlignmentRole:
            if index.column() == 0:
                return int(Qt.AlignCenter | Qt.AlignVCenter)
            if index.column() - 1 in self._numeric_columns:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.ForegroundRole:
            if index.column() == 0:
                return None
            if index.column() - 1 in self._numeric_columns:
                value = row.display_values[index.column() - 1]
                if parse_vnd_int(value) < 0:
                    return QColor("#dc2626")
        if role == Qt.BackgroundRole:
            return STATUS_COLORS.get(row.status)
        if role == Qt.ToolTipRole:
            status_key = row.status if row.status in ("matched", "review", "unmatched") else "unmatched"
            status_text = tr(self._language, status_key)
            return f"{status_text}\n{row.match_reason or ''}".strip()
        if role == Qt.UserRole:
            return row
        if role == Qt.UserRole + 1:
            return row.row_id
        if role == Qt.UserRole + 2:
            if index.column() == 0:
                return 0
            value = row.display_values[index.column() - 1]
            if index.column() - 1 in self._numeric_columns:
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
            if section == 0:
                return tr(self._language, "action")
            return self._headers[section - 1]
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

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: TransactionsTableModel = self.sourceModel()  # type: ignore[assignment]
        row = model.row_object(source_row)
        if self._status_mode == "matched" and row.status == "unmatched":
            return False
        if self._status_mode == "unmatched" and row.status != "unmatched":
            return False
        if self._flow_mode == "income" and row.direction != "income":
            return False
        if self._flow_mode == "expense" and row.direction != "expense":
            return False
        if self._flow_mode == "tax" and not row.has_tax:
            return False
        if self._reference_mode != "all":
            if self._reference_mode not in row.reference_prefixes:
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
