from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyle, QStyledItemDelegate

from app.i18n import tr
from app.ui.config import reference_prefix_summary_text
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

ROLE_ROW_KIND = Qt.UserRole + 10
ROLE_GROUP_KEY = Qt.UserRole + 11
ROLE_CHILD_ROW_ID = Qt.UserRole + 12


@dataclass(frozen=True)
class GroupMeta:
    key: str
    label: str
    status: str
    match_type: str
    rule_code: str
    system_count: int
    bank_count: int


@dataclass
class GroupDisplayRow:
    group_key: str
    group_label: str
    status: str
    match_type: str
    rule_code: str
    child_row_ids: list[str]
    display_values: list[str]
    tooltip: str


@dataclass
class DisplayEntry:
    row_kind: str
    row: object | None = None
    group: GroupDisplayRow | None = None
    child_tint: QColor | None = None


def status_bucket_for_row(row) -> str:
    if getattr(row, "status", "unmatched") == "matched":
        return "matched_group" if getattr(row, "match_type", "none") == "group" else "matched_exact"
    if getattr(row, "status", "unmatched") == "review":
        return "review"
    return "unmatched"


def match_kind_for_row(row) -> str:
    status = getattr(row, "status", "unmatched")
    if status == "matched":
        if getattr(row, "match_type", "none") == "exact":
            return "exact"
        rule_code = getattr(row, "rule_code", "none")
        if rule_code == "tax_vat_group":
            return "tax_group"
        if rule_code == "bank_composite_split":
            return "composite_group"
    if status == "review" and getattr(row, "review_group_id", None):
        return "review_nn_group"
    return "all"


def group_color_for_row(row) -> QColor | None:
    group_id = getattr(row, "group_id", None)
    if getattr(row, "match_type", "none") != "group" or not group_id:
        return None
    color_index = sum(ord(character) for character in group_id) % len(GROUP_COLORS)
    return GROUP_COLORS[color_index]


def review_group_color_for_row(row) -> QColor | None:
    review_group_id = getattr(row, "review_group_id", None)
    if getattr(row, "status", "unmatched") != "review" or not review_group_id:
        return None
    color_index = sum(ord(character) for character in review_group_id) % len(GROUP_COLORS)
    return GROUP_COLORS[color_index]


def row_background_color(row) -> QColor:
    group_color = group_color_for_row(row)
    if group_color is not None and getattr(row, "status", "unmatched") == "matched":
        return group_color
    review_group_color = review_group_color_for_row(row)
    if review_group_color is not None:
        return review_group_color
    return STATUS_COLORS.get(status_bucket_for_row(row), QColor("#f8fbff"))


def build_group_meta(system_rows: list[object], bank_rows: list[object]) -> dict[str, GroupMeta]:
    groups: dict[str, dict[str, object]] = {}

    def ensure_group(key: str, row, side: str) -> None:
        bucket = groups.setdefault(
            key,
            {
                "label": getattr(row, "group_id", None) or getattr(row, "review_group_id", None) or key,
                "status": getattr(row, "status", "unmatched"),
                "match_type": getattr(row, "match_type", "none"),
                "rule_code": getattr(row, "rule_code", "none"),
                "system_count": 0,
                "bank_count": 0,
            },
        )
        count_key = "system_count" if side == "system" else "bank_count"
        bucket[count_key] = int(bucket[count_key]) + 1

    for row in system_rows:
        if getattr(row, "match_type", "none") == "group" and getattr(row, "group_id", None):
            ensure_group(f"matched:{row.group_id}", row, "system")
        if getattr(row, "status", "unmatched") == "review" and getattr(row, "review_group_id", None):
            ensure_group(f"review:{row.review_group_id}", row, "system")

    for row in bank_rows:
        if getattr(row, "match_type", "none") == "group" and getattr(row, "group_id", None):
            ensure_group(f"matched:{row.group_id}", row, "bank")
        if getattr(row, "status", "unmatched") == "review" and getattr(row, "review_group_id", None):
            ensure_group(f"review:{row.review_group_id}", row, "bank")

    return {
        key: GroupMeta(
            key=key,
            label=str(values["label"]),
            status=str(values["status"]),
            match_type=str(values["match_type"]),
            rule_code=str(values["rule_code"]),
            system_count=int(values["system_count"]),
            bank_count=int(values["bank_count"]),
        )
        for key, values in groups.items()
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
            group_id = getattr(row, "group_id", None) or getattr(row, "review_group_id", None)
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
        self._match_kind_mode = "all"
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

    def set_match_kind_mode(self, mode: str) -> None:
        self._match_kind_mode = mode or "all"
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

    def count_for_status_mode(self, mode: str, *, ignore_match_kind: bool = False) -> int:
        model: TransactionsTableModel | None = self.sourceModel()  # type: ignore[assignment]
        if model is None:
            return 0
        return sum(
            1
            for source_row in range(model.rowCount())
            if self._accepts_row_object(
                model.row_object(source_row),
                mode,
                match_kind_override="all" if ignore_match_kind else None,
            )
        )

    def count_for_status_and_match_kind(self, status_mode: str, match_kind_mode: str) -> int:
        model: TransactionsTableModel | None = self.sourceModel()  # type: ignore[assignment]
        if model is None:
            return 0
        return sum(
            1
            for source_row in range(model.rowCount())
            if self._accepts_row_object(model.row_object(source_row), status_mode, match_kind_override=match_kind_mode)
        )

    def count_unique_groups_for_status_and_match_kind(self, status_mode: str, match_kind_mode: str) -> int:
        model: TransactionsTableModel | None = self.sourceModel()  # type: ignore[assignment]
        if model is None:
            return 0
        if match_kind_mode != "review_nn_group":
            return self.count_for_status_and_match_kind(status_mode, match_kind_mode)
        group_ids: set[str] = set()
        for source_row in range(model.rowCount()):
            row = model.row_object(source_row)
            if not self._accepts_row_object(row, status_mode, match_kind_override=match_kind_mode):
                continue
            review_group_id = getattr(row, "review_group_id", None)
            if review_group_id:
                group_ids.add(str(review_group_id))
        return len(group_ids)

    def _accepts_row_object(self, row, status_mode: str, *, match_kind_override: str | None = None) -> bool:
        row_bucket = status_bucket_for_row(row)
        row_match_kind = match_kind_for_row(row)
        if status_mode == "matched" and row_bucket not in {"matched_exact", "matched_group"}:
            return False
        if status_mode == "matched_exact" and row_bucket != "matched_exact":
            return False
        if status_mode == "matched_group" and row_bucket != "matched_group":
            return False
        if status_mode == "review" and row_bucket != "review":
            return False
        if status_mode == "unmatched" and row_bucket != "unmatched":
            return False
        active_match_kind_mode = self._match_kind_mode if match_kind_override is None else match_kind_override
        if active_match_kind_mode != "all" and row_match_kind != active_match_kind_mode:
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
            left_review_group = getattr(left_row, "review_group_id", None)
            right_review_group = getattr(right_row, "review_group_id", None)
            if self._status_mode == "matched_group" or (
                self._status_mode == "matched" and self._match_kind_mode in {"tax_group", "composite_group"}
            ):
                if left_group != right_group:
                    return str(left_group or "") < str(right_group or "")
                left_order = getattr(left_row, "group_order", getattr(left_row, "excel_row", 0))
                right_order = getattr(right_row, "group_order", getattr(right_row, "excel_row", 0))
                if left_order != right_order:
                    return left_order < right_order
            elif self._status_mode == "review":
                left_key = (0 if left_review_group else 1, str(left_review_group or ""), getattr(left_row, "review_group_order", 0))
                right_key = (0 if right_review_group else 1, str(right_review_group or ""), getattr(right_row, "review_group_order", 0))
                if left_key != right_key:
                    return left_key < right_key
            elif left_group and left_group == right_group:
                left_order = getattr(left_row, "group_order", getattr(left_row, "excel_row", 0))
                right_order = getattr(right_row, "group_order", getattr(right_row, "excel_row", 0))
                if left_order != right_order:
                    return left_order < right_order
            elif left_review_group and left_review_group == right_review_group:
                left_order = getattr(left_row, "review_group_order", getattr(left_row, "excel_row", 0))
                right_order = getattr(right_row, "review_group_order", getattr(right_row, "excel_row", 0))
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


class TransactionsDisplayModel(QAbstractTableModel):
    def __init__(
        self,
        headers: list[str],
        source_proxy: TransactionsFilterProxyModel,
        *,
        language: str = "vi",
        grid_kind: str,
        group_meta: dict[str, GroupMeta] | None = None,
    ) -> None:
        super().__init__()
        self._headers = [""] + list(headers)
        self._source_proxy = source_proxy
        self._language = language
        self._grid_kind = grid_kind
        self._group_meta = group_meta or {}
        self._expanded_groups: set[str] = set()
        self._entries: list[DisplayEntry] = []
        self._row_lookup: dict[str, int] = {}
        self._group_lookup: dict[str, int] = {}
        self._source_proxy.modelReset.connect(self.rebuild)
        self._source_proxy.layoutChanged.connect(self.rebuild)
        self._source_proxy.rowsInserted.connect(lambda *_args: self.rebuild())
        self._source_proxy.rowsRemoved.connect(lambda *_args: self.rebuild())
        self.rebuild()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._entries)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return section + 1

    def set_language(self, language: str) -> None:
        self._language = language
        self.rebuild()

    def set_group_meta(self, group_meta: dict[str, GroupMeta]) -> None:
        self._group_meta = group_meta
        self.rebuild()

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid():
            return None
        entry = self._entries[index.row()]
        if role == Qt.DisplayRole:
            if index.column() == 0:
                if entry.row_kind == "group" and entry.group is not None:
                    return "▾" if entry.group.group_key in self._expanded_groups else "▸"
                return ""
            display_values = self._display_values_for_entry(entry)
            if index.column() - 1 < len(display_values):
                return display_values[index.column() - 1]
            return ""
        if role == Qt.TextAlignmentRole:
            if index.column() == 0:
                return int(Qt.AlignCenter | Qt.AlignVCenter)
            if self._is_numeric_column(index.column()):
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return int(Qt.AlignLeft | Qt.AlignVCenter)
        if role == Qt.ForegroundRole and index.column() > 0:
            display_values = self._display_values_for_entry(entry)
            value = display_values[index.column() - 1] if index.column() - 1 < len(display_values) else ""
            if self._is_numeric_column(index.column()) and parse_vnd_int(value) < 0:
                return QColor("#dc2626")
            if entry.row_kind == "group":
                return QColor("#0f172a")
        if role == Qt.BackgroundRole:
            if entry.child_tint is not None:
                return entry.child_tint
            if entry.row_kind == "group":
                base = QColor("#f8fbff")
                if entry.group and entry.group.status == "review":
                    base = QColor("#fffbeb")
                return base
            if entry.row is not None:
                return row_background_color(entry.row)
        if role == Qt.ToolTipRole:
            if entry.row_kind == "group" and entry.group is not None:
                return entry.group.tooltip
            if entry.row is not None:
                status_text = tr(self._language, status_bucket_for_row(entry.row))
                reasons = [segment.strip() for segment in (entry.row.match_reason or "").splitlines() if segment.strip()]
                reason_text = "\n".join(f"- {item}" for item in reasons)
                group_id = getattr(entry.row, "group_id", None) or getattr(entry.row, "review_group_id", None)
                group_text = f"\nGroup: {group_id}" if group_id else ""
                return f"{status_text}{group_text}\n{reason_text}".strip()
        if role == Qt.UserRole:
            return entry.group if entry.row_kind == "group" else entry.row
        if role == ROLE_ROW_KIND:
            return entry.row_kind
        if role == ROLE_GROUP_KEY:
            if entry.row_kind == "group" and entry.group is not None:
                return entry.group.group_key
            if entry.row is not None:
                if getattr(entry.row, "status", "unmatched") == "review" and getattr(entry.row, "review_group_id", None):
                    return f"review:{entry.row.review_group_id}"
                if getattr(entry.row, "match_type", "none") == "group" and getattr(entry.row, "group_id", None):
                    return f"matched:{entry.row.group_id}"
            return None
        if role == ROLE_CHILD_ROW_ID and entry.row is not None:
            return getattr(entry.row, "row_id", None)
        if role == Qt.UserRole + 2:
            if entry.row_kind == "group" and entry.group is not None:
                if index.column() == 0:
                    return entry.group.group_key
                display_values = entry.group.display_values
                value = display_values[index.column() - 1] if index.column() - 1 < len(display_values) else ""
                if self._is_numeric_column(index.column()):
                    return parse_vnd_int(value)
                return normalize_text(value)
            if entry.row is not None:
                if index.column() == 0:
                    return getattr(entry.row, "excel_row", 0)
                display_values = entry.row.display_values
                value = display_values[index.column() - 1] if index.column() - 1 < len(display_values) else ""
                if self._is_numeric_column(index.column()):
                    return parse_vnd_int(value)
                return normalize_text(value)
        return None

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:
        source_column = max(0, column - 1)
        self._source_proxy.sort(source_column, order)
        self.rebuild()

    def rebuild(self) -> None:
        self.beginResetModel()
        self._entries = []
        self._row_lookup = {}
        self._group_lookup = {}

        rows = self._visible_rows_in_proxy_order()
        grouped_rows: dict[str, list[object]] = {}
        ordered_tokens: list[tuple[str, object]] = []
        seen_groups: set[str] = set()

        for row in rows:
            group_key = self._group_key_for_row(row)
            if group_key:
                grouped_rows.setdefault(group_key, []).append(row)
                if group_key not in seen_groups:
                    ordered_tokens.append(("group", group_key))
                    seen_groups.add(group_key)
            else:
                ordered_tokens.append(("row", row))

        for token_kind, token_value in ordered_tokens:
            if token_kind == "row":
                entry = DisplayEntry(row_kind="row", row=token_value)
                self._entries.append(entry)
                row_id = getattr(token_value, "row_id", None)
                if row_id:
                    self._row_lookup[row_id] = len(self._entries) - 1
                continue

            group_key = str(token_value)
            group_rows = self._sorted_group_rows(grouped_rows.get(group_key, []))
            if len(group_rows) <= 1:
                for row in group_rows:
                    entry = DisplayEntry(row_kind="row", row=row)
                    self._entries.append(entry)
                    row_id = getattr(row, "row_id", None)
                    if row_id:
                        self._row_lookup[row_id] = len(self._entries) - 1
                continue

            group_entry = DisplayEntry(row_kind="group", group=self._build_group_row(group_key, group_rows))
            self._entries.append(group_entry)
            self._group_lookup[group_key] = len(self._entries) - 1
            if group_key in self._expanded_groups:
                tint = self._child_tint(group_key, group_rows[0])
                for row in group_rows:
                    entry = DisplayEntry(row_kind="row", row=row, child_tint=tint)
                    self._entries.append(entry)
                    row_id = getattr(row, "row_id", None)
                    if row_id:
                        self._row_lookup[row_id] = len(self._entries) - 1

        self.endResetModel()

    def toggle_group(self, group_key: str) -> None:
        if not group_key:
            return
        if group_key in self._expanded_groups:
            self._expanded_groups.remove(group_key)
        else:
            self._expanded_groups.add(group_key)
        self.rebuild()

    def ensure_row_visible(self, row_id: str, column: int = 1) -> QModelIndex:
        row_index = self._row_lookup.get(row_id)
        if row_index is not None:
            return self.index(row_index, max(0, min(column, self.columnCount() - 1)))

        for group_key, rows in self._group_rows_map().items():
            if row_id not in {getattr(row, "row_id", None) for row in rows}:
                continue
            self._expanded_groups.add(group_key)
            self.rebuild()
            row_index = self._row_lookup.get(row_id)
            if row_index is not None:
                return self.index(row_index, max(0, min(column, self.columnCount() - 1)))
        return QModelIndex()

    def group_summary_by_key(self, group_key: str) -> GroupDisplayRow | None:
        index = self._group_lookup.get(group_key)
        if index is None:
            return None
        entry = self._entries[index]
        return entry.group

    def _group_rows_map(self) -> dict[str, list[object]]:
        rows = self._visible_rows_in_proxy_order()
        grouped_rows: dict[str, list[object]] = {}
        for row in rows:
            group_key = self._group_key_for_row(row)
            if group_key:
                grouped_rows.setdefault(group_key, []).append(row)
        return {key: self._sorted_group_rows(value) for key, value in grouped_rows.items()}

    def _visible_rows_in_proxy_order(self) -> list[object]:
        rows: list[object] = []
        for proxy_row in range(self._source_proxy.rowCount()):
            proxy_index = self._source_proxy.index(proxy_row, 0)
            row = proxy_index.data(Qt.UserRole)
            if row is not None:
                rows.append(row)
        return rows

    def _group_key_for_row(self, row) -> str | None:
        if getattr(row, "status", "unmatched") == "review" and getattr(row, "review_group_id", None):
            return f"review:{row.review_group_id}"
        if getattr(row, "match_type", "none") == "group" and getattr(row, "group_id", None):
            return f"matched:{row.group_id}"
        return None

    def _sorted_group_rows(self, rows: list[object]) -> list[object]:
        def sort_key(row):
            if getattr(row, "status", "unmatched") == "review":
                order = getattr(row, "review_group_order", 0)
            else:
                order = getattr(row, "group_order", 0)
            row_date = TransactionsFilterProxyModel._row_date(row) or date.min
            return (order, row_date, getattr(row, "excel_row", 0))

        return sorted(rows, key=sort_key)

    def _build_group_row(self, group_key: str, rows: list[object]) -> GroupDisplayRow:
        meta = self._group_meta.get(group_key)
        first_row = rows[0]
        label = meta.label if meta is not None else (
            getattr(first_row, "group_id", None)
            or getattr(first_row, "review_group_id", None)
            or group_key
        )
        current_count = len(rows)
        if meta is None:
            counterpart_count = current_count
        else:
            counterpart_count = meta.bank_count if self._grid_kind == "system" else meta.system_count
        summary_text = self._group_summary_text(
            rows,
            meta.rule_code if meta is not None else getattr(first_row, "rule_code", "none"),
        )
        display_values = [""] * (len(self._headers) - 1)
        if display_values:
            display_values[0] = self._group_date_text(rows)
        code_column = self._group_code_column()
        if 0 <= code_column < len(display_values):
            display_values[code_column] = label
        summary_column = self._summary_text_column()
        if 0 <= summary_column < len(display_values):
            display_values[summary_column] = summary_text
        current_side_label = self._grid_side_label()
        counterpart_side_label = self._counterpart_side_label()
        tooltip = (
            f"{label}\n"
            f"{summary_text}\n"
            f"{current_count} {current_side_label} = {counterpart_count} {counterpart_side_label}"
        )
        return GroupDisplayRow(
            group_key=group_key,
            group_label=label,
            status=meta.status if meta is not None else getattr(first_row, "status", "unmatched"),
            match_type=meta.match_type if meta is not None else getattr(first_row, "match_type", "none"),
            rule_code=meta.rule_code if meta is not None else getattr(first_row, "rule_code", "none"),
            child_row_ids=[getattr(row, "row_id", "") for row in rows],
            display_values=display_values,
            tooltip=tooltip,
        )

    def _display_values_for_entry(self, entry: DisplayEntry) -> list[str]:
        if entry.row_kind == "group" and entry.group is not None:
            return entry.group.display_values
        if entry.row is not None:
            return entry.row.display_values
        return []

    def _summary_text_column(self) -> int:
        if self._grid_kind == "bank":
            return 6
        return 2

    def _group_code_column(self) -> int:
        if self._grid_kind == "bank":
            return 2
        return 1

    def _grid_side_label(self) -> str:
        labels = {
            "vi": {"system": "hệ thống", "bank": "sao kê"},
            "en": {"system": "system", "bank": "statement"},
            "zh": {"system": "系统", "bank": "流水"},
        }
        return labels.get(self._language, labels["vi"])[self._grid_kind]

    def _counterpart_side_label(self) -> str:
        return self._grid_side_label_for("bank" if self._grid_kind == "system" else "system")

    def _grid_side_label_for(self, side: str) -> str:
        labels = {
            "vi": {"system": "hệ thống", "bank": "sao kê"},
            "en": {"system": "system", "bank": "statement"},
            "zh": {"system": "系统", "bank": "流水"},
        }
        return labels.get(self._language, labels["vi"])[side]

    def _group_kind_text(self, rule_code: str, status: str) -> str:
        labels = {
            "vi": {
                "tax_vat_group": "Phí/VAT",
                "bank_composite_split": "Chi + phí/thuế",
                "review": "Nhóm n-n cần kiểm tra",
                "default": "Nhóm giao dịch",
            },
            "en": {
                "tax_vat_group": "Fee/VAT",
                "bank_composite_split": "Debit + fee/tax",
                "review": "n-n review group",
                "default": "Grouped transactions",
            },
            "zh": {
                "tax_vat_group": "费用/VAT",
                "bank_composite_split": "支出 + 手续费/税",
                "review": "n-n 复核组",
                "default": "交易分组",
            },
        }
        language_labels = labels.get(self._language, labels["vi"])
        if status == "review":
            return language_labels["review"]
        return language_labels.get(rule_code, language_labels["default"])

    def _group_summary_text(self, rows: list[object], rule_code: str) -> str:
        prefix = self._primary_reference_prefix(rows, rule_code)
        base_text = reference_prefix_summary_text(self._language, prefix)
        return f"{base_text} ({len(rows)})"

    def _primary_reference_prefix(self, rows: list[object], rule_code: str) -> str:
        priority = ("FT", "TT", "LD", "HB", "ST", "SK")
        prefix_scores = {prefix: 0 for prefix in priority}
        for row in rows:
            row_prefixes = set(getattr(row, "reference_prefixes", set()) or set())
            for prefix in priority:
                if prefix in row_prefixes:
                    prefix_scores[prefix] += 1
        best_prefix = max(priority, key=lambda prefix: (prefix_scores[prefix], -priority.index(prefix)))
        if prefix_scores[best_prefix] > 0:
            return best_prefix
        if rule_code == "tax_vat_group":
            return "HB"
        return "OTHER"

    def _group_date_text(self, rows: list[object]) -> str:
        dates = [TransactionsFilterProxyModel._row_date(row) for row in rows]
        filtered_dates = [item for item in dates if item is not None]
        if not filtered_dates:
            return ""
        start = min(filtered_dates)
        end = max(filtered_dates)
        return start.strftime("%Y-%m-%d") if start == end else f"{start:%Y-%m-%d} ～ {end:%Y-%m-%d}"

    def _child_tint(self, group_key: str, row) -> QColor:
        if group_key.startswith("review:"):
            color = review_group_color_for_row(row) or QColor("#fff7d6")
        else:
            color = group_color_for_row(row) or QColor("#eef6ff")
        return color

    def _is_numeric_column(self, display_column: int) -> bool:
        source_column = display_column - 1
        if source_column < 0:
            return False
        source_model = self._source_proxy.sourceModel()
        if source_model is None:
            return False
        numeric_columns = getattr(source_model, "_numeric_columns", set())
        return source_column in numeric_columns


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
