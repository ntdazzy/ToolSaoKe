from __future__ import annotations

import logging

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.i18n import tr
from app.ui.config import BANK_GRID_FIXED_WIDTHS, REFERENCE_FILTER_OPTIONS, SYSTEM_GRID_FIXED_WIDTHS

logger = logging.getLogger(__name__)


class MainWindowFilterMixin:
    def _populate_search_columns(self) -> None:
        for combo, model in (
            (self.system_grid.columns, self.system_model),
            (self.bank_grid.columns, self.bank_model),
        ):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(tr(self.current_language, "all_columns"), -1)
            if model:
                for index, header in enumerate(model._headers):
                    combo.addItem(header, index)
            combo.blockSignals(False)

    def _apply_grid_column_widths(self) -> None:
        self.system_grid.table.auto_fit_columns(
            SYSTEM_GRID_FIXED_WIDTHS,
            min_width=66,
            max_auto_width=132,
            padding=14,
        )
        self.bank_grid.table.auto_fit_columns(
            BANK_GRID_FIXED_WIDTHS,
            min_width=62,
            max_auto_width=170,
            padding=14,
        )

    def _apply_filters(self) -> None:
        if not self.system_proxy or not self.bank_proxy:
            if self._filter_overlay_active:
                self.overlay.hide()
                self._filter_overlay_active = False
            return
        status_mode = self._current_status_mode()
        flow_mode = next(mode for mode, button in self.flow_buttons.items() if button.isChecked())
        reference_mode = self.reference_filter_combo.currentData() or "all"
        use_date_filter = self._date_filter_active and self.date_from_edit.isEnabled()
        date_from = self.date_from_edit.date().toPython() if use_date_filter else None
        date_to = self.date_to_edit.date().toPython() if use_date_filter else None
        for proxy in (self.system_proxy, self.bank_proxy):
            proxy.set_status_mode(status_mode)
            proxy.set_flow_mode(flow_mode)
            proxy.set_reference_mode(str(reference_mode))
            proxy.set_date_range(date_from, date_to)
        self._filter_system_grid()
        self._filter_bank_grid()
        self._update_summary()
        self._update_row_counts()
        logger.debug(
            "Áp dụng bộ lọc. status=%s | flow=%s | reference=%s | system_visible=%s | bank_visible=%s",
            status_mode,
            flow_mode,
            reference_mode,
            self.system_proxy.rowCount() if self.system_proxy else 0,
            self.bank_proxy.rowCount() if self.bank_proxy else 0,
        )
        if self._filter_overlay_active:
            self.overlay.hide()
            self._filter_overlay_active = False

    def _schedule_filters(self, *, with_loading: bool = False) -> None:
        if getattr(self, "_scan_in_progress", False):
            if self._filter_overlay_active:
                self.overlay.hide()
                self._filter_overlay_active = False
            self._filter_apply_scheduled = False
            return
        if self._filter_apply_scheduled:
            self._filter_overlay_active = self._filter_overlay_active or with_loading
            return
        self._filter_apply_scheduled = True
        if with_loading and self.current_result is not None:
            self.overlay.set_mode("filter")
            self.overlay.set_badge("")
            self.overlay.set_hint("")
            self.overlay.set_message(self._filter_loading_text())
            self.overlay.show()
            self._filter_overlay_active = True
            QApplication.processEvents()
        QTimer.singleShot(0, self._run_scheduled_filters)

    def _run_scheduled_filters(self) -> None:
        self._filter_apply_scheduled = False
        if getattr(self, "_scan_in_progress", False):
            if self._filter_overlay_active:
                self.overlay.hide()
                self._filter_overlay_active = False
            return
        self._apply_filters()

    def _filter_system_grid(self) -> None:
        if not self.system_proxy:
            return
        current_data = self.system_grid.columns.currentData()
        self.system_proxy.set_search_column(-1 if current_data is None else int(current_data))
        self.system_proxy.set_search_text(self.system_grid.search.text())
        self._update_row_counts()
        logger.debug(
            "Lọc lưới hệ thống. column=%s | search=%s | visible=%s",
            current_data,
            self.system_grid.search.text(),
            self.system_proxy.rowCount(),
        )

    def _filter_bank_grid(self) -> None:
        if not self.bank_proxy:
            return
        current_data = self.bank_grid.columns.currentData()
        self.bank_proxy.set_search_column(-1 if current_data is None else int(current_data))
        self.bank_proxy.set_search_text(self.bank_grid.search.text())
        self._update_row_counts()
        logger.debug(
            "Lọc lưới sao kê. column=%s | search=%s | visible=%s",
            current_data,
            self.bank_grid.search.text(),
            self.bank_proxy.rowCount(),
        )

    def _sync_quick_search(self, text: str) -> None:
        for grid in (self.system_grid, self.bank_grid):
            grid.columns.blockSignals(True)
            grid.columns.setCurrentIndex(0)
            grid.columns.blockSignals(False)
            grid.search.blockSignals(True)
            grid.search.setText(text)
            grid.search.blockSignals(False)
        self._filter_system_grid()
        self._filter_bank_grid()

    def _update_summary(self) -> None:
        if not self.current_result:
            self.summary_grid_label.setText("")
            for button in self.summary_filter_buttons.values():
                button.setText("")
            return
        proxy = self.bank_proxy if self._active_grid_mode == "bank" else self.system_proxy
        grid_label = tr(self.current_language, "bank_grid") if self._active_grid_mode == "bank" else tr(self.current_language, "system_grid")
        exact, group, review, unmatched = self._status_breakdown(proxy)
        self.summary_grid_label.setText(grid_label)
        self.summary_filter_buttons["all"].setText(tr(self.current_language, "status_all"))
        self.summary_filter_buttons["matched_exact"].setText(f"{exact} {tr(self.current_language, 'matched_exact')}")
        self.summary_filter_buttons["matched_group"].setText(f"{group} {tr(self.current_language, 'status_matched_group')}")
        self.summary_filter_buttons["review"].setText(f"{review} {tr(self.current_language, 'review')}")
        self.summary_filter_buttons["unmatched"].setText(f"{unmatched} {tr(self.current_language, 'unmatched')}")

    def _status_breakdown(self, proxy) -> tuple[int, int, int, int]:
        if proxy is None:
            return 0, 0, 0, 0
        return (
            proxy.count_for_status_mode("matched_exact"),
            proxy.count_for_status_mode("matched_group"),
            proxy.count_for_status_mode("review"),
            proxy.count_for_status_mode("unmatched"),
        )

    def _update_row_counts(self) -> None:
        for grid, model, proxy in (
            (self.system_grid, self.system_model, self.system_proxy),
            (self.bank_grid, self.bank_model, self.bank_proxy),
        ):
            total = model.total_rows if model else 0
            visible = proxy.rowCount() if proxy else 0
            grid.count.setText(tr(self.current_language, "grid_rows", visible=visible, total=total))
        self.results_page.update_grid_heights(self._active_grid_mode, self.system_proxy, self.bank_proxy)

    def _populate_reference_filter_options(self) -> None:
        current_value = self.reference_filter_combo.currentData()
        self.reference_filter_combo.blockSignals(True)
        self.reference_filter_combo.clear()
        for value, key in REFERENCE_FILTER_OPTIONS:
            self.reference_filter_combo.addItem(tr(self.current_language, key), value)
        if current_value is None:
            current_value = "all"
        index = self.reference_filter_combo.findData(current_value)
        self.reference_filter_combo.setCurrentIndex(index if index >= 0 else 0)
        self.reference_filter_combo.blockSignals(False)

    def _set_active_grid_mode(self, mode: str) -> None:
        self._active_grid_mode = "bank" if mode == "bank" else "system"
        current_widget = self.bank_page if self._active_grid_mode == "bank" else self.system_page
        self.grid_stack.setCurrentWidget(current_widget)
        self._update_grid_toggle_button()
        self._update_summary()
        self._update_export_controls_state(self.current_result is None)
        self.results_page.update_grid_heights(self._active_grid_mode, self.system_proxy, self.bank_proxy)

    def _update_grid_toggle_button(self) -> None:
        labels = {
            "vi": {"system": "Xem sao kê", "bank": "Xem hệ thống"},
            "en": {"system": "View statement", "bank": "View system"},
            "zh": {"system": "查看流水", "bank": "查看系统"},
        }
        language_labels = labels.get(self.current_language, labels["vi"])
        self.swap_button.setText(language_labels[self._active_grid_mode])

    def _current_status_mode(self) -> str:
        return next(mode for mode, button in self.summary_filter_buttons.items() if button.isChecked())

    def _filter_loading_text(self) -> str:
        labels = {
            "vi": "Đang lọc...",
            "en": "Filtering...",
            "zh": "正在筛选...",
        }
        return labels.get(self.current_language, labels["vi"])

    def _quick_search_placeholder(self) -> str:
        labels = {
            "vi": "Tìm giao dịch liên quan",
            "en": "Search related transactions",
            "zh": "搜索相关交易",
        }
        return labels.get(self.current_language, labels["vi"])
