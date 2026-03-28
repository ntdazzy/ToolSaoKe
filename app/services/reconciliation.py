from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.models import (
    BankTransaction,
    ReconciliationResult,
    ReconciliationSummary,
    SystemTransaction,
)
from app.services.excel_loader import load_bank_transactions, load_system_transactions
from app.services.utils import text_similarity


MINIMUM_MATCH_SCORE = 55
GREEN_THRESHOLD = 82
SAFETY_GAP = 12


@dataclass
class PairScore:
    score: int
    reasons: list[str]
    date_gap: int
    unique_group: bool
    has_reference: bool
    text_score: float


class ReconciliationService:
    def run(self, system_path: str, bank_path: str) -> ReconciliationResult:
        system_headers, system_rows = load_system_transactions(system_path)
        bank_headers, bank_rows, metadata = load_bank_transactions(bank_path)
        self._match_transactions(system_rows, bank_rows)
        summary = self._build_summary(system_rows, bank_rows)
        return ReconciliationResult(
            scanned_at=datetime.now(),
            system_file=str(Path(system_path)),
            bank_file=str(Path(bank_path)),
            system_headers=system_headers,
            bank_headers=bank_headers,
            system_rows=system_rows,
            bank_rows=bank_rows,
            metadata=metadata,
            summary=summary,
        )

    def _match_transactions(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> None:
        system_groups: dict[tuple[str, int], list[SystemTransaction]] = defaultdict(list)
        bank_groups: dict[tuple[str, int], list[BankTransaction]] = defaultdict(list)
        for row in system_rows:
            if row.amount > 0:
                system_groups[(row.direction, row.amount)].append(row)
        for row in bank_rows:
            if row.amount > 0:
                bank_groups[(row.direction, row.amount)].append(row)

        for group_key in sorted(set(system_groups) | set(bank_groups)):
            left_group = system_groups.get(group_key, [])
            right_group = bank_groups.get(group_key, [])
            if not left_group or not right_group:
                continue
            candidate_map: dict[tuple[str, str], PairScore] = {}
            per_system_scores: dict[str, list[int]] = defaultdict(list)
            per_bank_scores: dict[str, list[int]] = defaultdict(list)
            system_lookup = {row.row_id: row for row in left_group}
            bank_lookup = {row.row_id: row for row in right_group}
            for system_row in left_group:
                for bank_row in right_group:
                    pair = self._score_pair(system_row, bank_row, len(left_group), len(right_group))
                    if pair.score < MINIMUM_MATCH_SCORE:
                        continue
                    candidate_map[(system_row.row_id, bank_row.row_id)] = pair
                    per_system_scores[system_row.row_id].append(pair.score)
                    per_bank_scores[bank_row.row_id].append(pair.score)
            ordered_pairs = sorted(
                candidate_map.items(),
                key=lambda item: item[1].score,
                reverse=True,
            )
            for (system_id, bank_id), pair in ordered_pairs:
                system_row = system_lookup[system_id]
                bank_row = bank_lookup[bank_id]
                if system_row.matched_bank_id or bank_row.matched_system_id:
                    continue
                system_gap = self._best_gap(per_system_scores.get(system_id, []), pair.score)
                bank_gap = self._best_gap(per_bank_scores.get(bank_id, []), pair.score)
                confident = (
                    pair.has_reference
                    or (pair.unique_group and pair.date_gap <= 1)
                    or (pair.unique_group and pair.date_gap <= 3 and pair.text_score >= 0.45)
                    or (pair.score >= GREEN_THRESHOLD and system_gap >= SAFETY_GAP and bank_gap >= SAFETY_GAP)
                )
                status = "matched" if confident else "review"
                system_row.status = status
                bank_row.status = status
                system_row.confidence = pair.score
                bank_row.confidence = pair.score
                system_row.match_reason = ", ".join(pair.reasons)
                bank_row.match_reason = ", ".join(pair.reasons)
                system_row.matched_bank_id = bank_row.row_id
                bank_row.matched_system_id = system_row.row_id
                system_row.matched_bank_row = bank_row.excel_row
                bank_row.matched_system_row = system_row.excel_row
                system_row.has_tax = system_row.has_tax or bank_row.has_tax
                shared_prefixes = system_row.reference_prefixes | bank_row.reference_prefixes
                system_row.reference_prefixes = shared_prefixes
                bank_row.reference_prefixes = shared_prefixes

    def _score_pair(
        self,
        system_row: SystemTransaction,
        bank_row: BankTransaction,
        system_group_size: int,
        bank_group_size: int,
    ) -> PairScore:
        score = 35
        reasons = ["Số tiền trùng khớp theo VND"]
        reference_overlap = system_row.reference_tokens & bank_row.reference_tokens
        if reference_overlap:
            score += 40
            reasons.append(f"Trùng mã tham chiếu: {', '.join(sorted(reference_overlap))}")
        date_gap = self._date_gap(system_row, bank_row)
        if date_gap == 0:
            score += 18
            reasons.append("Ngày giao dịch trùng ngày")
        elif date_gap == 1:
            score += 14
            reasons.append("Ngày giao dịch lệch 1 ngày")
        elif date_gap <= 3:
            score += 10
            reasons.append("Ngày giao dịch gần nhau")
        elif date_gap <= 7:
            score += 5
            reasons.append("Ngày giao dịch có thể chấp nhận")
        elif date_gap <= 15:
            score += 1
        text_score = text_similarity(
            f"{system_row.summary} {system_row.counterpart_account}",
            f"{bank_row.description} {bank_row.remitter_account_name} {bank_row.reference_number}",
        )
        if text_score >= 0.75:
            score += 18
            reasons.append("Mô tả đối ứng rất giống nhau")
        elif text_score >= 0.5:
            score += 12
            reasons.append("Mô tả đối ứng giống nhau")
        elif text_score >= 0.3:
            score += 6
            reasons.append("Mô tả đối ứng có điểm gần nhau")
        if system_row.has_tax and bank_row.has_tax:
            score += 8
            reasons.append("Cùng có dấu hiệu VAT/thuế")
        unique_group = system_group_size == 1 and bank_group_size == 1
        if unique_group:
            score += 8
            reasons.append("Nhóm số tiền này là duy nhất")
        if system_row.direction == "income" and "收款" in system_row.summary:
            score += 4
        if system_row.direction == "expense" and any(
            marker in system_row.summary for marker in ("支付", "付款", "利息", "取现金")
        ):
            score += 4
        return PairScore(
            score=score,
            reasons=reasons,
            date_gap=date_gap,
            unique_group=unique_group,
            has_reference=bool(reference_overlap),
            text_score=text_score,
        )

    @staticmethod
    def _date_gap(system_row: SystemTransaction, bank_row: BankTransaction) -> int:
        if system_row.voucher_date is None or bank_row.transaction_date is None:
            return 99
        return abs((system_row.voucher_date - bank_row.transaction_date).days)

    @staticmethod
    def _best_gap(scores: list[int], best_score: int) -> int:
        ordered = sorted(scores, reverse=True)
        if not ordered:
            return 0
        if len(ordered) == 1:
            return best_score
        return best_score - ordered[1]

    @staticmethod
    def _build_summary(
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> ReconciliationSummary:
        matched_system = sum(1 for row in system_rows if row.status == "matched")
        review_system = sum(1 for row in system_rows if row.status == "review")
        unmatched_system = sum(1 for row in system_rows if row.status == "unmatched")
        matched_bank = sum(1 for row in bank_rows if row.status == "matched")
        review_bank = sum(1 for row in bank_rows if row.status == "review")
        unmatched_bank = sum(1 for row in bank_rows if row.status == "unmatched")
        return ReconciliationSummary(
            total_system=len(system_rows),
            total_bank=len(bank_rows),
            matched_system=matched_system,
            review_system=review_system,
            unmatched_system=unmatched_system,
            matched_bank=matched_bank,
            review_bank=review_bank,
            unmatched_bank=unmatched_bank,
        )
