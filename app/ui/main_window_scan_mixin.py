from __future__ import annotations

from datetime import date
import logging
from pathlib import Path

from PySide6.QtCore import QDate, Qt, QThread, Slot
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from app.i18n import tr
from app.models import ReconciliationResult
from app.services.excel_loader import detect_excel_file_kind
from app.services.utils import format_vnd
from app.ui.config import BANK_GRID_HEADERS
from app.ui.table_models import (
    TransactionsDisplayModel,
    TransactionsFilterProxyModel,
    TransactionsTableModel,
    build_group_meta,
)
from app.ui.workers import ScanWorker

logger = logging.getLogger(__name__)


class MainWindowScanMixin:
    def _choose_file(self, file_type: str) -> None:
        title = tr(self.current_language, "choose_file")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            title,
            str(Path.cwd()),
            "Excel Files (*.xls *.xlsx)",
        )
        if not file_path:
            return
        file_name = Path(file_path).name
        if file_type == "system":
            self._selected_system_path = file_path
            self.system_path_edit.setText(file_name)
            self.system_path_edit.setToolTip(file_path)
        else:
            self._selected_bank_path = file_path
            self.bank_path_edit.setText(file_name)
            self.bank_path_edit.setToolTip(file_path)
        logger.info("Đã chọn file %s: %s", file_type, file_path)

    def _validate_selected_files(self, system_path: str, bank_path: str) -> str | None:
        system_kind, system_reason = detect_excel_file_kind(system_path)
        bank_kind, bank_reason = detect_excel_file_kind(bank_path)
        logger.info(
            "Kiem tra file truoc khi do. system_kind=%s | bank_kind=%s | system_reason=%s | bank_reason=%s",
            system_kind,
            bank_kind,
            system_reason,
            bank_reason,
        )
        system_name = Path(system_path).name
        bank_name = Path(bank_path).name

        if system_kind == "bank" and bank_kind == "system":
            return self._file_validation_text("swapped", system_name=system_name, bank_name=bank_name)
        if system_kind == "bank":
            return self._file_validation_text("system_is_bank", name=system_name)
        if system_kind != "system":
            return self._file_validation_text("invalid_system", name=system_name)
        if bank_kind == "system":
            return self._file_validation_text("bank_is_system", name=bank_name)
        if bank_kind != "bank":
            return self._file_validation_text("invalid_bank", name=bank_name)
        return None

    def _file_validation_text(self, key: str, **kwargs: str) -> str:
        messages = {
            "vi": {
                "swapped": (
                    "Bạn đang chọn ngược 2 file.\n"
                    "- Ô File hệ thống đang là file sao kê ngân hàng: {system_name}\n"
                    "- Ô File sao kê đang là file hệ thống: {bank_name}\n"
                    "Vui lòng đổi lại đúng vị trí rồi dò lại."
                ),
                "system_is_bank": (
                    "Ô File hệ thống đang chọn file sao kê ngân hàng: {name}\n"
                    "Vui lòng chuyển file này sang ô Sao kê, hoặc chọn lại đúng file hệ thống."
                ),
                "invalid_system": (
                    "File hệ thống không đúng mẫu: {name}\n"
                    "Vui lòng chọn đúng file giao dịch hệ thống (.xls)."
                ),
                "bank_is_system": (
                    "Ô File sao kê đang chọn file hệ thống: {name}\n"
                    "Vui lòng chuyển file này sang ô Hệ thống, hoặc chọn lại đúng file sao kê."
                ),
                "invalid_bank": (
                    "File sao kê không đúng mẫu: {name}\n"
                    "Vui lòng chọn đúng file sao kê ngân hàng (.xlsx)."
                ),
            },
            "en": {
                "swapped": (
                    "The two files are selected in the wrong slots.\n"
                    "- The System file is actually a bank statement: {system_name}\n"
                    "- The Statement file is actually a system file: {bank_name}\n"
                    "Please switch them and try again."
                ),
                "system_is_bank": (
                    "The System slot currently contains a bank statement file: {name}\n"
                    "Please move this file to the Statement slot, or choose the correct system file."
                ),
                "invalid_system": (
                    "The selected System file does not match the expected template: {name}\n"
                    "Please choose the correct system transaction file (.xls)."
                ),
                "bank_is_system": (
                    "The Statement slot currently contains a system file: {name}\n"
                    "Please move this file to the System slot, or choose the correct statement file."
                ),
                "invalid_bank": (
                    "The selected Statement file does not match the expected template: {name}\n"
                    "Please choose the correct bank statement file (.xlsx)."
                ),
            },
            "zh": {
                "swapped": (
                    "两个文件放反了。\n"
                    "- 系统文件栏位现在是银行流水: {system_name}\n"
                    "- 流水文件栏位现在是系统文件: {bank_name}\n"
                    "请调换后再重试。"
                ),
                "system_is_bank": (
                    "系统文件栏位现在选的是银行流水: {name}\n"
                    "请将该文件放到流水栏位，或重新选择正确的系统文件。"
                ),
                "invalid_system": (
                    "所选的系统文件不符合预期模板: {name}\n"
                    "请选择正确的系统交易文件 (.xls)。"
                ),
                "bank_is_system": (
                    "流水文件栏位现在选的是系统文件: {name}\n"
                    "请将该文件放到系统栏位，或重新选择正确的流水文件。"
                ),
                "invalid_bank": (
                    "所选的流水文件不符合预期模板: {name}\n"
                    "请选择正确的银行流水文件 (.xlsx)。"
                ),
            },
        }
        language_messages = messages.get(self.current_language, messages["vi"])
        template = language_messages.get(key, messages["vi"][key])
        return template.format(**kwargs)

    def _handle_scan_requested(self) -> None:
        system_path = self._selected_system_path.strip()
        bank_path = self._selected_bank_path.strip()
        if system_path and bank_path:
            validation_message = self._validate_selected_files(system_path, bank_path)
            if validation_message:
                logger.warning(
                    "Chan thao tac do vi chon sai file. system_file=%s | bank_file=%s | message=%s",
                    system_path,
                    bank_path,
                    validation_message.replace("\n", " | "),
                )
                QMessageBox.warning(
                    self,
                    tr(self.current_language, "app_title"),
                    validation_message,
                )
                return
        self._start_scan()

    def _start_scan(self) -> None:
        system_path = self._selected_system_path.strip()
        bank_path = self._selected_bank_path.strip()
        if not system_path or not bank_path:
            logger.warning("Người dùng bấm dò nhưng chưa chọn đủ 2 file.")
            QMessageBox.warning(
                self,
                tr(self.current_language, "app_title"),
                tr(self.current_language, "select_files_first"),
            )
            return
        logger.info(
            "Bắt đầu dò từ giao diện. system_file=%s | bank_file=%s",
            system_path,
            bank_path,
        )
        self._scan_in_progress = True
        self._filter_apply_scheduled = False
        if self._filter_overlay_active:
            self.overlay.hide()
            self._filter_overlay_active = False
        self._update_locked_state(True)
        self._show_results_page()
        self.overlay.set_mode("scan")
        self.overlay.set_badge(tr(self.current_language, "loading_badge"))
        self.overlay.set_hint(tr(self.current_language, "loading_hint"))
        self.overlay.set_message(tr(self.current_language, "loading_title"))
        self.overlay.show()
        self.scan_button.setEnabled(False)
        QApplication.processEvents()

        self._scan_thread = QThread(self)
        self._scan_worker = ScanWorker(system_path, bank_path)
        self._scan_worker.moveToThread(self._scan_thread)
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._handle_scan_finished_queued, Qt.QueuedConnection)
        self._scan_worker.failed.connect(self._handle_scan_failed_queued, Qt.QueuedConnection)
        self._scan_worker.finished.connect(self._scan_thread.quit, Qt.QueuedConnection)
        self._scan_worker.failed.connect(self._scan_thread.quit, Qt.QueuedConnection)
        self._scan_thread.finished.connect(self._handle_scan_cleanup_queued, Qt.QueuedConnection)
        self._scan_thread.start()

    @Slot(object)
    def _scan_finished(self, result: ReconciliationResult) -> None:
        self._scan_in_progress = False
        self.current_result = result
        self.history_store.add_result(result)
        self._bind_result_to_grids(result)
        self._fill_metadata(result)
        self._refresh_history()
        self._update_locked_state(False)
        self._show_results_page()
        self.overlay.hide()
        self.scan_button.setEnabled(True)
        logger.info(
            "Dò hoàn tất trên giao diện. matched=%s | review=%s | unmatched=%s",
            result.summary.matched_system,
            result.summary.review_system,
            result.summary.unmatched_system,
        )

    @Slot(str)
    def _scan_failed(self, message: str) -> None:
        self._scan_in_progress = False
        self.overlay.hide()
        self.scan_button.setEnabled(True)
        self._update_locked_state(True)
        self._show_startup_page()
        logger.error("Dò thất bại trên giao diện: %s", message)
        QMessageBox.critical(
            self,
            tr(self.current_language, "app_title"),
            f"{tr(self.current_language, 'scan_failed')}\n{message}",
        )

    @Slot()
    def _cleanup_scan_thread(self) -> None:
        self._scan_in_progress = False
        if self._scan_worker:
            self._scan_worker.deleteLater()
            self._scan_worker = None
        if self._scan_thread:
            self._scan_thread.deleteLater()
            self._scan_thread = None

    def _bind_result_to_grids(self, result: ReconciliationResult) -> None:
        self.system_model = TransactionsTableModel(result.system_headers, result.system_rows, self.current_language)
        self.bank_model = TransactionsTableModel(BANK_GRID_HEADERS, result.bank_rows, self.current_language)
        self.system_proxy = TransactionsFilterProxyModel()
        self.bank_proxy = TransactionsFilterProxyModel()
        self.system_proxy.setSourceModel(self.system_model)
        self.bank_proxy.setSourceModel(self.bank_model)
        self.system_proxy.setSortRole(Qt.UserRole + 2)
        self.bank_proxy.setSortRole(Qt.UserRole + 2)
        group_meta = build_group_meta(result.system_rows, result.bank_rows)
        self.system_display_model = TransactionsDisplayModel(
            result.system_headers,
            self.system_proxy,
            language=self.current_language,
            grid_kind="system",
            group_meta=group_meta,
        )
        self.bank_display_model = TransactionsDisplayModel(
            BANK_GRID_HEADERS,
            self.bank_proxy,
            language=self.current_language,
            grid_kind="bank",
            group_meta=group_meta,
        )
        self.system_grid.table.setModel(self.system_display_model)
        self.bank_grid.table.setModel(self.bank_display_model)
        self.system_grid.table.sortByColumn(1, Qt.AscendingOrder)
        self.bank_grid.table.sortByColumn(1, Qt.AscendingOrder)
        self._set_active_grid_mode("bank")
        self._configure_date_filters(result)
        self._populate_search_columns()
        self._apply_filters()
        self._apply_grid_column_widths()
        self._update_summary()
        self._update_row_counts()
        logger.info(
            "Đã bind dữ liệu vào lưới. system_rows=%s | bank_rows=%s",
            len(result.system_rows),
            len(result.bank_rows),
        )

    def _fill_metadata(self, result: ReconciliationResult) -> None:
        metadata = result.metadata
        period_text = ""
        if metadata.from_date and metadata.to_date:
            period_text = f"{metadata.from_date:%Y-%m-%d} ～ {metadata.to_date:%Y-%m-%d}"
        values = {
            "meta_bank_name": metadata.bank_name_vi or metadata.bank_name_en,
            "meta_tax_code": metadata.tax_code,
            "meta_period": period_text,
            "meta_account_number": metadata.account_number,
            "meta_account_name": metadata.account_name,
            "meta_currency": metadata.currency,
            "meta_account_type": metadata.account_type,
            "meta_opening_balance": format_vnd(metadata.opening_balance),
            "meta_actual_balance": format_vnd(metadata.actual_balance),
            "meta_closing_balance": format_vnd(metadata.closing_balance),
            "meta_total_debits": format_vnd(abs(metadata.total_debits or 0)),
            "meta_total_credits": format_vnd(abs(metadata.total_credits or 0)),
            "meta_total_fees": format_vnd(abs(metadata.total_fees or 0)),
            "meta_total_vat": format_vnd(abs(metadata.total_vat or 0)),
            "meta_total_debit_tx": format_vnd(metadata.total_debit_transactions),
            "meta_total_credit_tx": format_vnd(metadata.total_credit_transactions),
        }
        for key, label in self.metric_values.items():
            label.setText(values.get(key) or "-")

    def _configure_date_filters(self, result: ReconciliationResult) -> None:
        available_dates = self._all_result_dates(result)
        if not available_dates:
            return
        self._date_filter_active = False
        min_date = min(available_dates)
        max_date = max(available_dates)
        min_qdate = QDate(min_date.year, min_date.month, min_date.day)
        max_qdate = QDate(max_date.year, max_date.month, max_date.day)
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.blockSignals(True)
            widget.setMinimumDate(min_qdate)
            widget.setMaximumDate(max_qdate)
        self.date_from_edit.setDate(min_qdate)
        self.date_to_edit.setDate(max_qdate)
        for widget in (self.date_from_edit, self.date_to_edit):
            widget.blockSignals(False)

    def _reset_date_filter(self) -> None:
        if self.current_result is None:
            return
        self._date_filter_active = False
        self._configure_date_filters(self.current_result)
        self._schedule_filters(with_loading=True)

    def _on_date_filter_changed(self) -> None:
        if self.current_result is None:
            return
        self._date_filter_active = True
        self._schedule_filters(with_loading=True)

    def _all_result_dates(self, result: ReconciliationResult) -> list[date]:
        values: list[date] = []
        for row in result.system_rows:
            if row.voucher_date is not None:
                values.append(row.voucher_date)
        for row in result.bank_rows:
            if row.transaction_date is not None:
                values.append(row.transaction_date)
            elif row.requesting_datetime is not None:
                values.append(row.requesting_datetime.date())
        return values
