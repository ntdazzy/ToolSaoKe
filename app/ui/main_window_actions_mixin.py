from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox, QTableWidgetItem

from app.i18n import tr
from app.services.exporter import export_system_rows
from app.ui.config import BANK_GRID_HEADERS
from app.ui.dialogs import HistoryDialog, PairDialog
from app.ui.widgets import FrozenTableView

logger = logging.getLogger(__name__)


class MainWindowActionsMixin:
    def _refresh_history_headers(self) -> None:
        self.history_table.setHorizontalHeaderLabels(
            [
                tr(self.current_language, "history_time"),
                tr(self.current_language, "history_system"),
                tr(self.current_language, "history_bank"),
                tr(self.current_language, "history_result"),
            ]
        )

    def _refresh_history(self) -> None:
        records = self.history_store.list_recent()
        self._history_records = list(records)
        self._refresh_history_headers()
        self.history_table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            scanned_at = record["scanned_at"].replace("T", " ")
            summary = f"{record['matched_system']} | {record['review_system']} | {record['unmatched_system']}"
            items = [
                scanned_at,
                Path(str(record["system_file"])).name,
                Path(str(record["bank_file"])).name,
                summary,
            ]
            for column_index, value in enumerate(items):
                item = QTableWidgetItem(value)
                self.history_table.setItem(row_index, column_index, item)
        self.history_table.resizeColumnsToContents()
        self.history_table.horizontalHeader().setStretchLastSection(True)
        logger.debug("Đã tải lịch sử lên giao diện. rows=%s", len(records))

    def _open_history_dialog(self) -> None:
        dialog = HistoryDialog(self.current_language, self._history_records, self)
        dialog.exec()

    def _swap_grids(self) -> None:
        target_mode = "bank" if self._active_grid_mode == "system" else "system"
        self._set_active_grid_mode(target_mode)
        logger.info("Đã chuyển lưới đang xem sang %s", target_mode)

    def _open_pair(self, source: str, row) -> None:
        if self.current_result is None:
            return
        logger.info(
            "Mở popup chi tiết đối ứng. source=%s | excel_row=%s | status=%s",
            source,
            getattr(row, "excel_row", None),
            getattr(row, "status", None),
        )
        if getattr(row, "match_type", "none") == "group" and getattr(row, "group_id", None):
            system_rows, bank_rows = self._group_rows(row.group_id)
            if source == "system" and not system_rows:
                system_rows = [row]
            if source == "bank" and not bank_rows:
                bank_rows = [row]
            if source == "system" and bank_rows:
                self._focus_counterpart_rows(
                    self.bank_model,
                    self.bank_proxy,
                    self.bank_grid.table,
                    [bank_row.row_id for bank_row in bank_rows],
                )
            elif source == "bank" and system_rows:
                self._focus_counterpart_rows(
                    self.system_model,
                    self.system_proxy,
                    self.system_grid.table,
                    [system_row.row_id for system_row in system_rows],
                )
            dialog = PairDialog(
                self.current_language,
                tr(self.current_language, "paired_system"),
                self.current_result.system_headers,
                system_rows,
                tr(self.current_language, "paired_bank"),
                BANK_GRID_HEADERS,
                bank_rows,
                self,
            )
            dialog.exec()
            return
        if source == "system":
            system_rows = [row]
            bank_rows = self._review_or_matched_bank_rows(row)
            self._focus_counterpart_rows(
                self.bank_model,
                self.bank_proxy,
                self.bank_grid.table,
                [bank_row.row_id for bank_row in bank_rows],
            )
        else:
            bank_rows = [row]
            system_rows = self._review_or_matched_system_rows(row)
            self._focus_counterpart_rows(
                self.system_model,
                self.system_proxy,
                self.system_grid.table,
                [system_row.row_id for system_row in system_rows],
            )
        dialog = PairDialog(
            self.current_language,
            tr(self.current_language, "paired_system"),
            self.current_result.system_headers,
            system_rows,
            tr(self.current_language, "paired_bank"),
            BANK_GRID_HEADERS,
            bank_rows,
            self,
        )
        dialog.exec()

    def _focus_counterpart_rows(self, model, proxy, table: FrozenTableView, row_ids: list[str]) -> None:
        if not model or not proxy or not row_ids:
            return
        source_row = model.row_index_by_id(row_ids[0])
        if source_row is None:
            return
        target_column = 1 if model.columnCount() > 1 else 0
        source_index = model.index(source_row, target_column)
        proxy_index = proxy.mapFromSource(source_index)
        if not proxy_index.isValid():
            return
        table.select_proxy_index(proxy_index)

    def _system_row_by_id(self, row_id: str | None):
        if not self.system_model or row_id is None:
            return None
        index = self.system_model.row_index_by_id(row_id)
        return self.system_model.row_object(index) if index is not None else None

    def _bank_row_by_id(self, row_id: str | None):
        if not self.bank_model or row_id is None:
            return None
        index = self.bank_model.row_index_by_id(row_id)
        return self.bank_model.row_object(index) if index is not None else None

    def _review_or_matched_bank_rows(self, row) -> list[object]:
        matched_row = self._bank_row_by_id(getattr(row, "matched_bank_id", None))
        if matched_row is not None:
            return [matched_row]
        review_ids = list(getattr(row, "review_bank_ids", []) or [])
        review_rows = [self._bank_row_by_id(row_id) for row_id in review_ids]
        return [candidate for candidate in review_rows if candidate is not None]

    def _review_or_matched_system_rows(self, row) -> list[object]:
        matched_row = self._system_row_by_id(getattr(row, "matched_system_id", None))
        if matched_row is not None:
            return [matched_row]
        review_ids = list(getattr(row, "review_system_ids", []) or [])
        review_rows = [self._system_row_by_id(row_id) for row_id in review_ids]
        return [candidate for candidate in review_rows if candidate is not None]

    def _group_rows(self, group_id: str) -> tuple[list[object], list[object]]:
        if self.current_result is None:
            return [], []
        system_rows = sorted(
            [row for row in self.current_result.system_rows if getattr(row, "group_id", None) == group_id],
            key=lambda row: (getattr(row, "group_order", 0), getattr(row, "excel_row", 0)),
        )
        bank_rows = sorted(
            [row for row in self.current_result.bank_rows if getattr(row, "group_id", None) == group_id],
            key=lambda row: (getattr(row, "group_order", 0), getattr(row, "excel_row", 0)),
        )
        return system_rows, bank_rows

    def _export_unmatched(self) -> None:
        if not self.current_result:
            return
        rows_to_export = self._visible_rows_for_active_grid()
        if not rows_to_export:
            logger.warning("Không có dữ liệu để xuất theo bộ lọc hiện tại.")
            QMessageBox.information(
                self,
                tr(self.current_language, "app_title"),
                self._no_rows_to_export_message(),
            )
            return
        status_mode = self._current_status_mode()
        highlight_unmatched = status_mode == "all"
        default_path = self._default_export_path()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr(self.current_language, "save_dialog_title"),
            str(default_path),
            "Excel Files (*.xlsx)",
        )
        if not file_path:
            logger.info("Người dùng hủy thao tác xuất Excel.")
            return
        try:
            headers = self._active_headers_for_export()
            sheet_name = self._active_export_sheet_name()
            attached_statement_path = (
                self.current_result.bank_file
                if self.attach_statement_checkbox.isChecked()
                else None
            )
            logger.info(
                "Bắt đầu xuất Excel từ giao diện. grid=%s | output=%s | rows=%s | highlight_unmatched=%s | attach_statement=%s",
                self._active_grid_mode,
                file_path,
                len(rows_to_export),
                highlight_unmatched,
                bool(attached_statement_path),
            )
            export_system_rows(
                headers,
                rows_to_export,
                file_path,
                highlight_unmatched=highlight_unmatched,
                sheet_name=sheet_name,
                attached_statement_path=attached_statement_path,
            )
        except ValueError:
            QMessageBox.information(
                self,
                tr(self.current_language, "app_title"),
                self._no_rows_to_export_message(),
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("Xuất Excel thất bại: %s", exc)
            QMessageBox.critical(
                self,
                tr(self.current_language, "app_title"),
                f"{tr(self.current_language, 'export_failed')}\n{exc}",
            )
            return
        logger.info("Xuất Excel thành công. output=%s", file_path)
        QMessageBox.information(
            self,
            tr(self.current_language, "app_title"),
            tr(self.current_language, "export_success"),
        )

    def _active_model_and_proxy(self):
        if self._active_grid_mode == "bank":
            return self.bank_model, self.bank_proxy
        return self.system_model, self.system_proxy

    def _visible_rows_for_active_grid(self) -> list[object]:
        model, proxy = self._active_model_and_proxy()
        if not model or not proxy:
            return []
        rows: list[object] = []
        for proxy_row in range(proxy.rowCount()):
            proxy_index = proxy.index(proxy_row, 0)
            source_index = proxy.mapToSource(proxy_index)
            if not source_index.isValid():
                continue
            rows.append(model.row_object(source_index.row()))
        return rows

    def _active_headers_for_export(self) -> list[str]:
        if self._active_grid_mode == "bank":
            return list(self.current_result.bank_headers) if self.current_result else BANK_GRID_HEADERS
        return list(self.current_result.system_headers) if self.current_result else []

    def _active_export_sheet_name(self) -> str:
        return "SaoKe_Xuat" if self._active_grid_mode == "bank" else "HeThong_Xuat"

    def _export_button_label(self) -> str:
        labels = {
            "vi": "Xuất Excel",
            "en": "Export Excel",
            "zh": "导出 Excel",
        }
        return labels.get(self.current_language, labels["vi"])

    def _default_export_path(self) -> Path:
        if self.current_result:
            selected_file = self.current_result.bank_file if self._active_grid_mode == "bank" else self.current_result.system_file
            if selected_file:
                selected_path = Path(selected_file)
                if selected_path.suffix.lower() == ".xlsx":
                    return selected_path.with_name(f"{selected_path.stem}_Xuat.xlsx")
                if selected_path.suffix:
                    return selected_path.with_suffix(".xlsx")
                return selected_path.with_name(f"{selected_path.name}_Xuat.xlsx")
        default_name = "sao_ke_xuat.xlsx" if self._active_grid_mode == "bank" else "he_thong_xuat.xlsx"
        return Path.cwd() / default_name

    def _no_rows_to_export_message(self) -> str:
        messages = {
            "vi": "Không có dữ liệu để xuất theo bộ lọc hiện tại.",
            "en": "There are no rows to export for the current filter.",
            "zh": "当前筛选条件下没有可导出的数据。",
        }
        return messages.get(self.current_language, messages["vi"])
