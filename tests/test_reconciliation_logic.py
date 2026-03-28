from __future__ import annotations

import logging
import unittest
from datetime import date, datetime

from app.models import BankTransaction, SystemTransaction
from app.services.reconciliation import ReconciliationService
from app.ui.table_models import TransactionsFilterProxyModel, TransactionsTableModel


logging.disable(logging.CRITICAL)


def make_system(
    *,
    row_id: str,
    excel_row: int,
    voucher_date: date,
    amount: int,
    direction: str,
    voucher_number: str = "",
    summary: str = "",
    counterpart_account: str = "",
    reference_tokens: set[str] | None = None,
    reference_prefixes: set[str] | None = None,
    has_tax: bool = False,
) -> SystemTransaction:
    amount_debit = amount if direction == "income" else 0
    amount_credit = amount if direction == "expense" else 0
    return SystemTransaction(
        row_id=row_id,
        excel_row=excel_row,
        display_values=[voucher_date.isoformat(), voucher_number, summary, counterpart_account, "", "", "", "", "", ""],
        voucher_date=voucher_date,
        voucher_number=voucher_number,
        summary=summary,
        counterpart_account=counterpart_account,
        amount_debit=amount_debit,
        amount_credit=amount_credit,
        direction=direction,
        amount=amount,
        balance=None,
        data_source="",
        normalized_text="",
        reference_tokens=reference_tokens or set(),
        reference_prefixes=reference_prefixes or set(),
        has_tax=has_tax,
    )


def make_bank(
    *,
    row_id: str,
    excel_row: int,
    transaction_date: date,
    amount: int,
    direction: str,
    reference_number: str = "",
    description: str = "",
    reference_tokens: set[str] | None = None,
    reference_prefixes: set[str] | None = None,
    debit: int = 0,
    credit: int = 0,
    fee: int = 0,
    vat: int = 0,
    has_tax: bool = False,
) -> BankTransaction:
    if direction == "income":
        credit = amount if not credit else credit
    else:
        if debit == 0 and fee == 0 and vat == 0:
            debit = -amount
    return BankTransaction(
        row_id=row_id,
        excel_row=excel_row,
        display_values=[
            f"{transaction_date.isoformat()} 00:00:00",
            transaction_date.isoformat(),
            reference_number,
            "",
            "",
            "",
            description,
            str(debit),
            str(credit),
            str(fee),
            str(vat),
            "",
        ],
        requesting_datetime=datetime.combine(transaction_date, datetime.min.time()),
        transaction_date=transaction_date,
        reference_number=reference_number,
        remitter_bank="",
        remitter_account_number="",
        remitter_account_name="",
        description=description,
        debit=debit,
        credit=credit,
        fee=fee,
        vat=vat,
        amount=amount,
        direction=direction,
        running_balance=None,
        normalized_text="",
        reference_tokens=reference_tokens or set(),
        reference_prefixes=reference_prefixes or set(),
        has_tax=has_tax,
    )


class ReconciliationLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = ReconciliationService()

    def test_reference_match_beats_same_amount_candidate(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 10),
                amount=450_000_000,
                direction="expense",
                voucher_number="记-0001",
                summary="SK20260310-0021",
                reference_tokens={"SK20260310-0021"},
                reference_prefixes={"SK"},
            ),
            make_system(
                row_id="sys-2",
                excel_row=2,
                voucher_date=date(2026, 3, 10),
                amount=450_000_000,
                direction="expense",
                voucher_number="记-0002",
                summary="No reference",
            ),
        ]
        bank_rows = [
            make_bank(
                row_id="bank-1",
                excel_row=10,
                transaction_date=date(2026, 3, 10),
                amount=450_000_000,
                direction="expense",
                reference_number="FT26069704396721",
                reference_tokens={"SK20260310-0021"},
                reference_prefixes={"SK", "FT"},
            )
        ]

        self.service._run_matching_cycles(system_rows, bank_rows)

        self.assertEqual(system_rows[0].status, "matched")
        self.assertEqual(system_rows[0].matched_bank_id, "bank-1")
        self.assertEqual(system_rows[1].status, "unmatched")
        self.assertEqual(bank_rows[0].matched_system_id, "sys-1")

    def test_ambiguous_same_amount_same_day_stays_review(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 10),
                amount=100_000_000,
                direction="expense",
                voucher_number="记-0001",
            ),
            make_system(
                row_id="sys-2",
                excel_row=2,
                voucher_date=date(2026, 3, 10),
                amount=100_000_000,
                direction="expense",
                voucher_number="记-0002",
            ),
        ]
        bank_rows = [
            make_bank(
                row_id="bank-1",
                excel_row=10,
                transaction_date=date(2026, 3, 10),
                amount=100_000_000,
                direction="expense",
                reference_number="FT1",
            ),
            make_bank(
                row_id="bank-2",
                excel_row=11,
                transaction_date=date(2026, 3, 10),
                amount=100_000_000,
                direction="expense",
                reference_number="FT2",
            ),
        ]

        self.service._run_matching_cycles(system_rows, bank_rows)

        self.assertTrue(all(row.status == "review" for row in system_rows))
        self.assertTrue(all(row.status == "review" for row in bank_rows))

    def test_tax_aggregate_matches_only_vat_group(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-tax",
                excel_row=72,
                voucher_date=date(2026, 3, 9),
                amount=880_000,
                direction="expense",
                voucher_number="记-0802",
                summary="支付手机短信费用",
            ),
            make_system(
                row_id="sys-other",
                excel_row=73,
                voucher_date=date(2026, 3, 9),
                amount=990_000,
                direction="expense",
                voucher_number="记-0803",
                summary="普通费用",
            ),
        ]
        bank_rows = [
            make_bank(
                row_id=f"bank-tax-{index}",
                excel_row=380 + index,
                transaction_date=date(2026, 3, 9),
                amount=110_000,
                direction="expense",
                reference_number=f"HB.{index}",
                description="Thu phi Homebanking",
                fee=-100_000,
                vat=-10_000,
                has_tax=True,
            )
            for index in range(1, 9)
        ]

        self.service._run_matching_cycles(system_rows, bank_rows)

        self.assertEqual(system_rows[0].status, "matched")
        self.assertTrue(system_rows[0].matched_tax)
        self.assertEqual(system_rows[1].status, "unmatched")
        self.assertFalse(system_rows[1].matched_tax)
        self.assertTrue(all(row.status == "matched" for row in bank_rows))
        self.assertTrue(all(row.matched_tax for row in bank_rows))

    def test_tax_filter_is_precise_for_system_and_bank(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 10),
                amount=100_000,
                direction="expense",
                voucher_number="记-0001",
                has_tax=True,
            ),
            make_system(
                row_id="sys-2",
                excel_row=2,
                voucher_date=date(2026, 3, 10),
                amount=100_000,
                direction="expense",
                voucher_number="记-0002",
            ),
        ]
        system_rows[0].status = "matched"
        system_rows[1].status = "matched"
        system_rows[1].matched_tax = True

        bank_rows = [
            make_bank(
                row_id="bank-1",
                excel_row=10,
                transaction_date=date(2026, 3, 10),
                amount=100_000,
                direction="expense",
                reference_number="HB.1",
                has_tax=True,
            ),
            make_bank(
                row_id="bank-2",
                excel_row=11,
                transaction_date=date(2026, 3, 10),
                amount=110_000,
                direction="expense",
                reference_number="HB.2",
                fee=-100_000,
                vat=-10_000,
                has_tax=True,
            ),
        ]
        bank_rows[0].status = "matched"
        bank_rows[1].status = "matched"

        system_model = TransactionsTableModel(["Ngay", "So"], system_rows)
        bank_model = TransactionsTableModel(["Ngay", "Ma", "VAT"], bank_rows)
        system_proxy = TransactionsFilterProxyModel()
        bank_proxy = TransactionsFilterProxyModel()
        system_proxy.setSourceModel(system_model)
        bank_proxy.setSourceModel(bank_model)

        system_proxy.set_flow_mode("tax")
        bank_proxy.set_flow_mode("tax")

        self.assertEqual(system_proxy.rowCount(), 1)
        self.assertEqual(bank_proxy.rowCount(), 1)

        system_row = system_proxy.index(0, 0).data(role=0)
        bank_row = bank_proxy.index(0, 0).data(role=0)
        self.assertEqual(system_row, system_rows[1].display_values[0])
        self.assertEqual(bank_row, bank_rows[1].display_values[0])

    def test_unique_same_amount_same_day_is_matched(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 10),
                amount=123_000_000,
                direction="expense",
                voucher_number="记-1001",
            )
        ]
        bank_rows = [
            make_bank(
                row_id="bank-1",
                excel_row=10,
                transaction_date=date(2026, 3, 10),
                amount=123_000_000,
                direction="expense",
                reference_number="FT-1001",
            )
        ]

        self.service._run_matching_cycles(system_rows, bank_rows)

        self.assertEqual(system_rows[0].status, "matched")
        self.assertEqual(bank_rows[0].status, "matched")

    def test_direction_mismatch_stays_unmatched(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 10),
                amount=123_000_000,
                direction="income",
                voucher_number="记-1001",
            )
        ]
        bank_rows = [
            make_bank(
                row_id="bank-1",
                excel_row=10,
                transaction_date=date(2026, 3, 10),
                amount=123_000_000,
                direction="expense",
                reference_number="FT-1001",
            )
        ]

        self.service._run_matching_cycles(system_rows, bank_rows)

        self.assertEqual(system_rows[0].status, "unmatched")
        self.assertEqual(bank_rows[0].status, "unmatched")

    def test_unique_far_date_stays_review_instead_of_matched(self) -> None:
        system_rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 17),
                amount=123_000_000,
                direction="expense",
                voucher_number="记-1001",
            )
        ]
        bank_rows = [
            make_bank(
                row_id="bank-1",
                excel_row=10,
                transaction_date=date(2026, 3, 10),
                amount=123_000_000,
                direction="expense",
                reference_number="FT-1001",
            )
        ]

        self.service._run_matching_cycles(system_rows, bank_rows)

        self.assertEqual(system_rows[0].status, "review")
        self.assertEqual(bank_rows[0].status, "review")

    def test_status_filter_separates_review_from_matched(self) -> None:
        rows = [
            make_system(
                row_id="sys-1",
                excel_row=1,
                voucher_date=date(2026, 3, 10),
                amount=10,
                direction="expense",
                voucher_number="记-1",
            ),
            make_system(
                row_id="sys-2",
                excel_row=2,
                voucher_date=date(2026, 3, 10),
                amount=20,
                direction="expense",
                voucher_number="记-2",
            ),
            make_system(
                row_id="sys-3",
                excel_row=3,
                voucher_date=date(2026, 3, 10),
                amount=30,
                direction="expense",
                voucher_number="记-3",
            ),
        ]
        rows[0].status = "matched"
        rows[1].status = "review"
        rows[2].status = "unmatched"

        model = TransactionsTableModel(["Ngay", "So"], rows)
        proxy = TransactionsFilterProxyModel()
        proxy.setSourceModel(model)

        proxy.set_status_mode("matched")
        self.assertEqual(proxy.rowCount(), 1)
        proxy.set_status_mode("review")
        self.assertEqual(proxy.rowCount(), 1)
        proxy.set_status_mode("unmatched")
        self.assertEqual(proxy.rowCount(), 1)
        proxy.set_status_mode("all")
        self.assertEqual(proxy.rowCount(), 3)


if __name__ == "__main__":
    unittest.main()
