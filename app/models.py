from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class BankMetadata:
    bank_name_vi: str = ""
    bank_name_en: str = ""
    tax_code: str = ""
    statement_title: str = ""
    from_date: date | None = None
    to_date: date | None = None
    account_number: str = ""
    account_name: str = ""
    currency: str = ""
    account_type: str = ""
    actual_balance: int | None = None
    opening_balance: int | None = None
    closing_balance: int | None = None
    total_debits: int | None = None
    total_credits: int | None = None
    total_fees: int | None = None
    total_vat: int | None = None
    total_debit_transactions: int | None = None
    total_credit_transactions: int | None = None


@dataclass
class SystemTransaction:
    row_id: str
    excel_row: int
    display_values: list[str]
    voucher_date: date | None
    voucher_number: str
    summary: str
    counterpart_account: str
    amount_debit: int
    amount_credit: int
    direction: str
    amount: int
    balance: int | None
    data_source: str
    normalized_text: str
    text_tokens: set[str] = field(default_factory=set)
    reference_tokens: set[str] = field(default_factory=set)
    reference_prefixes: set[str] = field(default_factory=set)
    has_tax: bool = False
    status: str = "unmatched"
    confidence: int = 0
    match_reason: str = ""
    matched_bank_id: str | None = None
    matched_bank_row: int | None = None


@dataclass
class BankTransaction:
    row_id: str
    excel_row: int
    display_values: list[str]
    requesting_datetime: datetime | None
    transaction_date: date | None
    reference_number: str
    remitter_bank: str
    remitter_account_number: str
    remitter_account_name: str
    description: str
    debit: int
    credit: int
    fee: int
    vat: int
    amount: int
    direction: str
    running_balance: int | None
    normalized_text: str
    text_tokens: set[str] = field(default_factory=set)
    reference_tokens: set[str] = field(default_factory=set)
    reference_prefixes: set[str] = field(default_factory=set)
    has_tax: bool = False
    status: str = "unmatched"
    confidence: int = 0
    match_reason: str = ""
    matched_system_id: str | None = None
    matched_system_row: int | None = None


@dataclass
class ReconciliationSummary:
    total_system: int
    total_bank: int
    matched_system: int
    review_system: int
    unmatched_system: int
    matched_bank: int
    review_bank: int
    unmatched_bank: int


@dataclass
class ReconciliationResult:
    scanned_at: datetime
    system_file: str
    bank_file: str
    system_headers: list[str]
    bank_headers: list[str]
    system_rows: list[SystemTransaction]
    bank_rows: list[BankTransaction]
    metadata: BankMetadata
    summary: ReconciliationSummary
