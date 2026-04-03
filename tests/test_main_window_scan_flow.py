from __future__ import annotations

import os
import unittest
from datetime import date, datetime
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.models import (
    BankMetadata,
    BankTransaction,
    ReconciliationResult,
    ReconciliationSummary,
    SystemTransaction,
)
from app.ui.main_window import MainWindow
from app.ui.table_models import ROLE_GROUP_KEY, ROLE_ROW_KIND


def make_system_row() -> SystemTransaction:
    return SystemTransaction(
        row_id="sys-1",
        excel_row=1,
        display_values=["2026-03-10", "记-0001", "Thanh toan tien hang", "", "0", "100,000,000", "借", "", "", ""],
        voucher_date=date(2026, 3, 10),
        voucher_number="记-0001",
        summary="Thanh toan tien hang",
        counterpart_account="",
        amount_debit=0,
        amount_credit=100_000_000,
        direction="expense",
        amount=100_000_000,
        balance=None,
        data_source="",
        normalized_text="",
    )


def make_bank_row() -> BankTransaction:
    return BankTransaction(
        row_id="bank-1",
        excel_row=10,
        display_values=[
            "2026-03-10 10:30:00",
            "2026-03-10",
            "FT260000000001",
            "TECHCOMBANK",
            "19038873337776",
            "CTY TEST",
            "Thanh toan tien hang",
            "-100,000,000",
            "0",
            "0",
            "0",
            "1,000,000,000",
        ],
        requesting_datetime=datetime(2026, 3, 10, 10, 30, 0),
        transaction_date=date(2026, 3, 10),
        reference_number="FT260000000001",
        remitter_bank="TECHCOMBANK",
        remitter_account_number="19038873337776",
        remitter_account_name="CTY TEST",
        description="Thanh toan tien hang",
        debit=-100_000_000,
        credit=0,
        fee=0,
        vat=0,
        amount=100_000_000,
        direction="expense",
        running_balance=1_000_000_000,
        normalized_text="",
        reference_prefixes={"FT"},
    )


def make_result() -> ReconciliationResult:
    system_row = make_system_row()
    bank_row = make_bank_row()
    system_row.status = "matched"
    system_row.match_type = "exact"
    system_row.matched_bank_id = bank_row.row_id
    system_row.matched_bank_row = bank_row.excel_row
    bank_row.status = "matched"
    bank_row.match_type = "exact"
    bank_row.matched_system_id = system_row.row_id
    bank_row.matched_system_row = system_row.excel_row
    return ReconciliationResult(
        scanned_at=datetime(2026, 4, 1, 9, 0, 0),
        system_file="HeThong.xls",
        bank_file="SaoKe.xlsx",
        system_headers=["凭证日期", "凭证字号", "摘要", "对方科目", "金额借方", "金额贷方", "方向", "余额", "制单人", "数据来源"],
        bank_headers=["Ngày yêu cầu", "Ngày GD", "Mã GD"],
        system_rows=[system_row],
        bank_rows=[bank_row],
        metadata=BankMetadata(
            bank_name_vi="NGÂN HÀNG TEST",
            account_name="CTY TEST",
            account_number="19135065170012",
            currency="VND",
            account_type="Current Account",
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
            opening_balance=100_000_000,
            actual_balance=1_000_000_000,
            closing_balance=1_000_000_000,
            total_debits=100_000_000,
            total_credits=0,
            total_fees=0,
            total_vat=0,
            total_debit_transactions=1,
            total_credit_transactions=0,
        ),
        summary=ReconciliationSummary(
            total_system=1,
            total_bank=1,
            matched_system=1,
            review_system=0,
            unmatched_system=0,
            matched_bank=1,
            review_bank=0,
            unmatched_bank=0,
        ),
    )


def make_review_group_result() -> ReconciliationResult:
    system_row_1 = make_system_row()
    system_row_2 = make_system_row()
    system_row_1.row_id = "sys-1"
    system_row_2.row_id = "sys-2"
    system_row_1.excel_row = 1
    system_row_2.excel_row = 2
    system_row_1.voucher_date = date(2026, 3, 10)
    system_row_2.voucher_date = date(2026, 3, 11)
    system_row_1.display_values[0] = "2026-03-10"
    system_row_2.display_values[0] = "2026-03-11"
    system_row_1.status = "review"
    system_row_2.status = "review"
    system_row_1.review_group_id = "R-0001"
    system_row_2.review_group_id = "R-0001"
    system_row_1.review_group_order = 1
    system_row_2.review_group_order = 2
    system_row_1.review_bank_ids = ["bank-1", "bank-2"]
    system_row_2.review_bank_ids = ["bank-1", "bank-2"]

    bank_row_1 = make_bank_row()
    bank_row_2 = make_bank_row()
    bank_row_1.row_id = "bank-1"
    bank_row_2.row_id = "bank-2"
    bank_row_1.excel_row = 10
    bank_row_2.excel_row = 11
    bank_row_1.transaction_date = date(2026, 3, 10)
    bank_row_2.transaction_date = date(2026, 3, 11)
    bank_row_1.requesting_datetime = datetime(2026, 3, 10, 10, 30, 0)
    bank_row_2.requesting_datetime = datetime(2026, 3, 11, 10, 30, 0)
    bank_row_1.display_values[0] = "2026-03-10 10:30:00"
    bank_row_2.display_values[0] = "2026-03-11 10:30:00"
    bank_row_1.display_values[1] = "2026-03-10"
    bank_row_2.display_values[1] = "2026-03-11"
    bank_row_1.status = "review"
    bank_row_2.status = "review"
    bank_row_1.review_group_id = "R-0001"
    bank_row_2.review_group_id = "R-0001"
    bank_row_1.review_group_order = 1
    bank_row_2.review_group_order = 2
    bank_row_1.review_system_ids = ["sys-1", "sys-2"]
    bank_row_2.review_system_ids = ["sys-1", "sys-2"]

    return ReconciliationResult(
        scanned_at=datetime(2026, 4, 1, 9, 0, 0),
        system_file="HeThong.xls",
        bank_file="SaoKe.xlsx",
        system_headers=["凭证日期", "凭证字号", "摘要", "对方科目", "金额借方", "金额贷方", "方向", "余额", "制单人", "数据来源"],
        bank_headers=["Ngày yêu cầu", "Ngày GD", "Mã GD"],
        system_rows=[system_row_1, system_row_2],
        bank_rows=[bank_row_1, bank_row_2],
        metadata=BankMetadata(
            bank_name_vi="NGÂN HÀNG TEST",
            account_name="CTY TEST",
            account_number="19135065170012",
            currency="VND",
            account_type="Current Account",
            from_date=date(2026, 3, 1),
            to_date=date(2026, 3, 31),
        ),
        summary=ReconciliationSummary(
            total_system=2,
            total_bank=2,
            matched_system=0,
            review_system=2,
            unmatched_system=0,
            matched_bank=0,
            review_bank=2,
            unmatched_bank=0,
        ),
    )


class FakeSignal:
    def __init__(self) -> None:
        self.connections: list[tuple[object, object | None]] = []

    def connect(self, slot, connection_type=None) -> None:
        self.connections.append((slot, connection_type))


class FakeThread:
    def __init__(self, parent=None) -> None:
        self.parent = parent
        self.started = FakeSignal()
        self.finished = FakeSignal()
        self.start_called = False
        self.quit_called = False
        self.deleted = False

    def start(self) -> None:
        self.start_called = True

    def quit(self) -> None:
        self.quit_called = True

    def deleteLater(self) -> None:
        self.deleted = True


class FakeWorker:
    def __init__(self, system_path: str, bank_path: str) -> None:
        self.system_path = system_path
        self.bank_path = bank_path
        self.finished = FakeSignal()
        self.failed = FakeSignal()
        self.moved_to = None
        self.deleted = False

    def moveToThread(self, thread) -> None:
        self.moved_to = thread

    def run(self) -> None:
        return None

    def deleteLater(self) -> None:
        self.deleted = True


class MainWindowScanFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = MainWindow()
        self.window.history_store.add_result = Mock()
        self.window.show()
        self.process_events()

    def tearDown(self) -> None:
        self.window.close()
        self.process_events()

    @classmethod
    def process_events(cls) -> None:
        cls.app.processEvents()

    def test_startup_page_opens_in_compact_mode(self) -> None:
        self.assertIs(self.window.page_stack.currentWidget(), self.window.startup_page)
        self.assertTrue(self.window._compact_window_mode)
        self.assertEqual(self.window.minimumSize(), self.window.maximumSize())
        self.assertFalse(bool(self.window.windowFlags() & Qt.WindowMaximizeButtonHint))

    def test_scan_success_switches_to_results_and_restores_window_state(self) -> None:
        result = make_result()

        self.window._scan_in_progress = True
        self.window.overlay.set_mode("scan")
        self.window.overlay.show()
        self.process_events()

        self.window._scan_finished(result)
        self.process_events()

        self.assertIs(self.window.page_stack.currentWidget(), self.window.results_page)
        self.assertIs(self.window.system_display_model._source_proxy, self.window.system_proxy)
        self.assertIs(self.window.bank_display_model._source_proxy, self.window.bank_proxy)
        self.assertIs(self.window.system_grid.table.model(), self.window.system_display_model)
        self.assertIs(self.window.bank_grid.table.model(), self.window.bank_display_model)
        self.assertFalse(self.window._compact_window_mode)
        self.assertNotEqual(self.window.minimumSize(), self.window.maximumSize())
        self.assertTrue(bool(self.window.windowFlags() & Qt.WindowMaximizeButtonHint))
        self.assertFalse(self.window.overlay.isVisible())
        self.assertTrue(self.window.results_content.isVisible())
        self.assertTrue(self.window.metadata_card.isVisible())

    def test_scan_failure_returns_to_startup_and_hides_loading(self) -> None:
        self.window._scan_in_progress = True
        self.window.overlay.set_mode("scan")
        self.window.overlay.show()
        self.process_events()

        with patch("app.ui.main_window_scan_mixin.QMessageBox.critical") as critical:
            self.window._scan_failed("boom")
        self.process_events()

        self.assertIs(self.window.page_stack.currentWidget(), self.window.startup_page)
        self.assertTrue(self.window._compact_window_mode)
        self.assertEqual(self.window.minimumSize(), self.window.maximumSize())
        self.assertFalse(self.window.overlay.isVisible())
        self.assertTrue(self.window.scan_button.isEnabled())
        self.assertFalse(self.window.results_content.isVisible())
        critical.assert_called_once()

    def test_show_startup_page_restores_compact_mode_even_after_result_exists(self) -> None:
        self.window._scan_finished(make_result())
        self.process_events()

        self.window._show_startup_page()
        self.process_events()

        self.assertIs(self.window.page_stack.currentWidget(), self.window.startup_page)
        self.assertTrue(self.window._compact_window_mode)
        self.assertEqual(self.window.minimumSize(), self.window.maximumSize())
        self.assertFalse(bool(self.window.windowFlags() & Qt.WindowMaximizeButtonHint))

    def test_scan_start_uses_queued_connections_and_enters_scan_mode(self) -> None:
        self.window._selected_system_path = "C:/temp/system.xls"
        self.window._selected_bank_path = "C:/temp/bank.xlsx"

        with patch("app.ui.main_window_scan_mixin.QThread", FakeThread), patch(
            "app.ui.main_window_scan_mixin.ScanWorker",
            FakeWorker,
        ):
            self.window._start_scan()

        self.process_events()
        self.assertTrue(self.window._scan_in_progress)
        self.assertIs(self.window.page_stack.currentWidget(), self.window.results_page)
        self.assertEqual(self.window.overlay._mode, "scan")
        self.assertTrue(self.window.overlay.isVisible())
        self.assertFalse(self.window._compact_window_mode)
        self.assertTrue(bool(self.window.windowFlags() & Qt.WindowMaximizeButtonHint))
        self.assertTrue(self.window._scan_thread.start_called)
        self.assertIs(self.window._scan_worker.moved_to, self.window._scan_thread)
        self.assertIn((self.window._handle_scan_finished_queued, Qt.QueuedConnection), self.window._scan_worker.finished.connections)
        self.assertIn((self.window._handle_scan_failed_queued, Qt.QueuedConnection), self.window._scan_worker.failed.connections)
        self.assertIn((self.window._scan_thread.quit, Qt.QueuedConnection), self.window._scan_worker.finished.connections)
        self.assertIn((self.window._scan_thread.quit, Qt.QueuedConnection), self.window._scan_worker.failed.connections)
        self.assertIn((self.window._handle_scan_cleanup_queued, Qt.QueuedConnection), self.window._scan_thread.finished.connections)

    def test_open_pair_uses_review_group_rows_for_nn_review(self) -> None:
        self.window._scan_finished(make_review_group_result())
        self.process_events()

        bank_row = self.window.current_result.bank_rows[0]

        with patch("app.ui.main_window_actions_mixin.PairDialog") as dialog_cls:
            dialog = dialog_cls.return_value
            dialog.exec = Mock()
            self.window._open_pair("bank", bank_row)

        args = dialog_cls.call_args.args
        system_rows = args[3]
        bank_rows = args[6]
        self.assertEqual(len(system_rows), 2)
        self.assertEqual(len(bank_rows), 2)
        self.assertEqual([row.row_id for row in system_rows], ["sys-1", "sys-2"])
        self.assertEqual([row.row_id for row in bank_rows], ["bank-1", "bank-2"])

    def test_filter_loading_does_not_override_scan_overlay(self) -> None:
        self.window._scan_in_progress = True
        self.window.overlay.set_mode("scan")
        self.window.overlay.show()
        self.process_events()

        self.window._schedule_filters(with_loading=True)
        self.process_events()

        self.assertEqual(self.window.overlay._mode, "scan")
        self.assertFalse(self.window._filter_overlay_active)

    def test_match_kind_chips_follow_selected_status(self) -> None:
        self.window._scan_finished(make_result())
        self.process_events()

        self.assertFalse(self.window.match_kind_filter_group.isHidden())
        visible_modes = {mode for mode, button in self.window.match_kind_buttons.items() if not button.isHidden()}
        self.assertEqual(visible_modes, {"all", "exact", "tax_group", "composite_group", "review_nn_group"})

        self.window.summary_filter_buttons["matched"].click()
        self.process_events()

        visible_modes = {mode for mode, button in self.window.match_kind_buttons.items() if not button.isHidden()}
        self.assertEqual(visible_modes, {"all", "exact", "tax_group", "composite_group"})
        self.assertTrue(self.window.match_kind_buttons["all"].text().startswith("1 "))
        self.assertTrue(self.window.match_kind_buttons["exact"].text().startswith("1 "))

        self.window.summary_filter_buttons["unmatched"].click()
        self.process_events()
        self.assertFalse(self.window.match_kind_filter_group.isHidden())
        self.assertEqual(self.window.match_kind_opacity.opacity(), 0.0)

    def test_review_groups_render_as_collapsible_rows(self) -> None:
        self.window._scan_finished(make_review_group_result())
        self.process_events()

        self.window.summary_filter_buttons["all"].click()
        self.process_events()
        self.assertTrue(self.window.match_kind_buttons["review_nn_group"].text().startswith("1 "))

        self.window.match_kind_buttons["review_nn_group"].click()
        self.process_events()

        model = self.window.bank_grid.table.model()
        self.assertEqual(model.rowCount(), 1)
        self.assertEqual(model.index(0, 0).data(ROLE_ROW_KIND), "group")
        self.assertEqual(model.index(0, 0).data(ROLE_GROUP_KEY), "review:R-0001")
        self.assertEqual(model.index(0, 7).data(Qt.DisplayRole), "Chuyển khoản (2)")

        self.window._toggle_group_row("bank", model.index(0, 0).data(Qt.UserRole))
        self.process_events()

        model = self.window.bank_grid.table.model()
        self.assertEqual(model.rowCount(), 3)
        self.assertEqual(model.index(0, 0).data(ROLE_ROW_KIND), "group")
        self.assertEqual(model.index(1, 0).data(ROLE_ROW_KIND), "row")
        self.assertEqual(model.index(2, 0).data(ROLE_ROW_KIND), "row")

    def test_summary_status_counts_ignore_selected_match_kind(self) -> None:
        self.window._scan_finished(make_result())
        self.process_events()

        self.window.summary_filter_buttons["matched"].click()
        self.process_events()
        matched_text_before = self.window.summary_filter_buttons["matched"].text()

        self.window.match_kind_buttons["tax_group"].click()
        self.process_events()

        self.assertEqual(self.window.summary_filter_buttons["matched"].text(), matched_text_before)
        self.assertTrue(self.window.summary_filter_buttons["matched"].text().startswith("1 "))


if __name__ == "__main__":
    unittest.main()
