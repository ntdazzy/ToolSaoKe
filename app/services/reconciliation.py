from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import re

from app.models import (
    BankTransaction,
    ReconciliationResult,
    ReconciliationSummary,
    SystemTransaction,
)
from app.services.excel_loader import load_bank_transactions, load_system_transactions
from app.services.utils import normalize_text, text_similarity


MINIMUM_MATCH_SCORE = 50
GREEN_THRESHOLD = 82
SAFETY_GAP = 12
logger = logging.getLogger(__name__)


@dataclass
class PairScore:
    score: int
    reasons: list[str]
    date_gap: int
    unique_group: bool
    has_reference: bool
    text_score: float
    mutual_closest: bool = False


class ReconciliationService:
    def run(self, system_path: str, bank_path: str) -> ReconciliationResult:
        logger.info(
            "Bắt đầu đối soát. system_file=%s | bank_file=%s",
            system_path,
            bank_path,
        )
        system_headers, system_rows = load_system_transactions(system_path)
        bank_headers, bank_rows, metadata = load_bank_transactions(bank_path)
        logger.info(
            "Đã nạp dữ liệu đối soát. system_rows=%s | bank_rows=%s",
            len(system_rows),
            len(bank_rows),
        )
        self._match_transactions(system_rows, bank_rows)
        self._match_tax_aggregates(system_rows, bank_rows)
        summary = self._build_summary(system_rows, bank_rows)
        logger.info(
            "Đối soát xong. matched_system=%s | review_system=%s | unmatched_system=%s | matched_bank=%s | review_bank=%s | unmatched_bank=%s",
            summary.matched_system,
            summary.review_system,
            summary.unmatched_system,
            summary.matched_bank,
            summary.review_bank,
            summary.unmatched_bank,
        )
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
        logger.debug(
            "Tạo nhóm đối soát theo hướng giao dịch và số tiền. system_groups=%s | bank_groups=%s",
            len(system_groups),
            len(bank_groups),
        )

        for group_key in sorted(set(system_groups) | set(bank_groups)):
            left_group = system_groups.get(group_key, [])
            right_group = bank_groups.get(group_key, [])
            if not left_group or not right_group:
                if left_group or right_group:
                    logger.debug(
                        "Bỏ qua nhóm không có dữ liệu đối ứng. key=%s | system_count=%s | bank_count=%s",
                        group_key,
                        len(left_group),
                        len(right_group),
                    )
                continue
            candidate_map: dict[tuple[str, str], PairScore] = {}
            pair_scores: dict[tuple[str, str], PairScore] = {}
            per_system_scores: dict[str, list[int]] = defaultdict(list)
            per_bank_scores: dict[str, list[int]] = defaultdict(list)
            system_lookup = {row.row_id: row for row in left_group}
            bank_lookup = {row.row_id: row for row in right_group}
            for system_row in left_group:
                for bank_row in right_group:
                    pair = self._score_pair(system_row, bank_row, len(left_group), len(right_group))
                    pair_scores[(system_row.row_id, bank_row.row_id)] = pair
            closest_system_gap = self._closest_date_gaps_by_system(pair_scores)
            closest_bank_gap = self._closest_date_gaps_by_bank(pair_scores)
            for key, pair in pair_scores.items():
                system_id, bank_id = key
                pair.mutual_closest = self._is_mutual_closest_date_pair(
                    pair,
                    closest_system_gap.get(system_id),
                    closest_bank_gap.get(bank_id),
                )
                if pair.mutual_closest:
                    pair.score += 8
                    pair.reasons.append("Ngày giao dịch là cặp gần nhất hai chiều")
                if not self._should_keep_candidate(pair):
                    continue
                candidate_map[key] = pair
                per_system_scores[system_id].append(pair.score)
                per_bank_scores[bank_id].append(pair.score)
            logger.debug(
                "Nhóm %s có %s ứng viên hợp lệ. system_count=%s | bank_count=%s",
                group_key,
                len(candidate_map),
                len(left_group),
                len(right_group),
            )
            ordered_pairs = sorted(
                candidate_map.items(),
                key=lambda item: self._pair_priority(item[1]),
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
                    or (pair.mutual_closest and pair.date_gap <= 1 and system_gap >= 6 and bank_gap >= 6)
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
                logger.debug(
                    "Ghép cặp thành công. status=%s | system_row=%s | bank_row=%s | score=%s | amount=%s | reasons=%s",
                    status,
                    system_row.excel_row,
                    bank_row.excel_row,
                    pair.score,
                    system_row.amount,
                    " | ".join(pair.reasons),
                )

    def _match_tax_aggregates(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> None:
        unmatched_system_rows = [
            row for row in system_rows if row.status == "unmatched" and row.direction == "expense"
        ]
        unmatched_tax_bank_rows = [
            row
            for row in bank_rows
            if row.status == "unmatched" and row.direction == "expense" and abs(getattr(row, "vat", 0)) > 0
        ]
        if not unmatched_system_rows or not unmatched_tax_bank_rows:
            return

        bank_groups: dict[tuple[object, str], list[BankTransaction]] = defaultdict(list)
        for bank_row in unmatched_tax_bank_rows:
            bank_groups[(self._bank_effective_date(bank_row), self._tax_group_key(bank_row))].append(bank_row)

        matched_system_ids: set[str] = set()
        matched_group_count = 0
        for (group_date, _group_text), group_rows in bank_groups.items():
            total_amount = sum(row.amount for row in group_rows)
            if total_amount <= 0:
                continue
            exact_candidates = [
                row
                for row in unmatched_system_rows
                if row.row_id not in matched_system_ids
                and row.amount == total_amount
                and row.voucher_date is not None
                and group_date is not None
                and row.voucher_date == group_date
            ]
            if len(exact_candidates) == 1:
                self._mark_tax_group_match(exact_candidates[0], group_rows, "matched")
                matched_system_ids.add(exact_candidates[0].row_id)
                matched_group_count += 1
                continue

            near_candidates = [
                row
                for row in unmatched_system_rows
                if row.row_id not in matched_system_ids
                and row.amount == total_amount
                and row.voucher_date is not None
                and group_date is not None
                and abs((row.voucher_date - group_date).days) <= 1
            ]
            if len(near_candidates) == 1:
                self._mark_tax_group_match(near_candidates[0], group_rows, "review")
                matched_system_ids.add(near_candidates[0].row_id)
                matched_group_count += 1

        if matched_group_count:
            logger.info(
                "Đã ghép bổ sung %s nhóm thuế/VAT sau vòng đối soát chính.",
                matched_group_count,
            )

    def _mark_tax_group_match(
        self,
        system_row: SystemTransaction,
        bank_rows: list[BankTransaction],
        status: str,
    ) -> None:
        total_amount = sum(row.amount for row in bank_rows)
        first_bank_row = min(bank_rows, key=lambda row: row.excel_row)
        group_date = self._bank_effective_date(first_bank_row)
        reason = (
            f"Ghép gom {len(bank_rows)} dòng sao kê có VAT thành 1 dòng chi hệ thống"
            f" (ngày {group_date}, tổng {total_amount:,.0f})"
        )
        confidence = 92 if status == "matched" else 76
        system_row.status = status
        system_row.confidence = confidence
        system_row.match_reason = reason
        system_row.has_tax = True
        system_row.matched_bank_id = first_bank_row.row_id
        system_row.matched_bank_row = first_bank_row.excel_row
        shared_prefixes = set(system_row.reference_prefixes)
        for bank_row in bank_rows:
            bank_row.status = status
            bank_row.confidence = confidence
            bank_row.match_reason = reason
            bank_row.matched_system_id = system_row.row_id
            bank_row.matched_system_row = system_row.excel_row
            shared_prefixes |= bank_row.reference_prefixes
        system_row.reference_prefixes = shared_prefixes
        for bank_row in bank_rows:
            bank_row.reference_prefixes = shared_prefixes

    @staticmethod
    def _bank_effective_date(bank_row: BankTransaction):
        if bank_row.transaction_date is not None:
            return bank_row.transaction_date
        if bank_row.requesting_datetime is not None:
            return bank_row.requesting_datetime.date()
        return None

    @staticmethod
    def _tax_group_key(bank_row: BankTransaction) -> str:
        combined = normalize_text(f"{bank_row.description} {bank_row.remitter_account_name}")
        combined = re.sub(r"\b\d+\b", " ", combined)
        combined = re.sub(r"\s+", " ", combined).strip()
        return combined or "tax-group"

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
            score += 24
            reasons.append("Ngày giao dịch trùng ngày")
        elif date_gap == 1:
            score += 18
            reasons.append("Ngày giao dịch lệch 1 ngày")
        elif date_gap <= 3:
            score += 12
            reasons.append("Ngày giao dịch gần nhau")
        elif date_gap <= 7:
            score += 6
            reasons.append("Ngày giao dịch có thể chấp nhận")
        elif date_gap <= 15:
            score += 2
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
            score += 10
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
        bank_date = bank_row.transaction_date
        if bank_date is None and bank_row.requesting_datetime is not None:
            bank_date = bank_row.requesting_datetime.date()
        if system_row.voucher_date is None or bank_date is None:
            return 99
        return abs((system_row.voucher_date - bank_date).days)

    @staticmethod
    def _closest_date_gaps_by_system(pair_scores: dict[tuple[str, str], PairScore]) -> dict[str, int]:
        gaps: dict[str, int] = {}
        for (system_id, _bank_id), pair in pair_scores.items():
            current_gap = gaps.get(system_id, 999)
            if pair.date_gap < current_gap:
                gaps[system_id] = pair.date_gap
        return gaps

    @staticmethod
    def _closest_date_gaps_by_bank(pair_scores: dict[tuple[str, str], PairScore]) -> dict[str, int]:
        gaps: dict[str, int] = {}
        for (_system_id, bank_id), pair in pair_scores.items():
            current_gap = gaps.get(bank_id, 999)
            if pair.date_gap < current_gap:
                gaps[bank_id] = pair.date_gap
        return gaps

    @staticmethod
    def _is_mutual_closest_date_pair(
        pair: PairScore,
        system_gap: int | None,
        bank_gap: int | None,
    ) -> bool:
        return (
            pair.date_gap <= 3
            and system_gap is not None
            and bank_gap is not None
            and pair.date_gap == system_gap
            and pair.date_gap == bank_gap
        )

    @staticmethod
    def _should_keep_candidate(pair: PairScore) -> bool:
        return (
            pair.score >= MINIMUM_MATCH_SCORE
            or pair.date_gap == 0
            or pair.date_gap == 1
            or pair.mutual_closest
            or (pair.unique_group and pair.date_gap <= 7)
        )

    @staticmethod
    def _pair_priority(pair: PairScore) -> tuple[int, int, int, int, int, int, float]:
        return (
            1 if pair.has_reference else 0,
            1 if pair.date_gap == 0 else 0,
            1 if pair.date_gap <= 1 else 0,
            1 if pair.mutual_closest else 0,
            -pair.date_gap,
            pair.score,
            pair.text_score,
        )

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
