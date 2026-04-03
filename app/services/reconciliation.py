from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from functools import lru_cache
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
STRICT_STAGES = ("reference", "voucher_unique", "derived_unique")
FINAL_STAGE = "scored"
logger = logging.getLogger(__name__)


@dataclass
class PairScore:
    score: int
    reasons: list[str]
    date_gap: int
    date_source: str
    unique_group: bool
    has_reference: bool
    text_score: float
    mutual_closest: bool = False


class ReconciliationService:
    def run(self, system_path: str, bank_path: str) -> ReconciliationResult:
        logger.info(
            "Bắt đầu dò. system_file=%s | bank_file=%s",
            system_path,
            bank_path,
        )
        system_headers, system_rows = load_system_transactions(system_path)
        bank_headers, bank_rows, metadata = load_bank_transactions(bank_path)
        logger.info(
            "Đã nạp dữ liệu dò. system_rows=%s | bank_rows=%s",
            len(system_rows),
            len(bank_rows),
        )

        self._run_matching_cycles(system_rows, bank_rows)
        summary = self._build_summary(system_rows, bank_rows)
        logger.info(
            "Dò xong. matched_system=%s | review_system=%s | unmatched_system=%s | "
            "matched_bank=%s | review_bank=%s | unmatched_bank=%s",
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

    def _run_matching_cycles(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> None:
        self._group_sequence = 0
        iteration = 0
        while True:
            iteration += 1
            progress = 0
            for stage in STRICT_STAGES:
                progress += self._match_transactions_pass(system_rows, bank_rows, stage, allow_review=False)
            progress += self._match_tax_aggregates(system_rows, bank_rows)
            progress += self._match_bank_component_splits(system_rows, bank_rows)
            logger.debug("Vòng dò nghiêm ngặt %s hoàn tất. progress=%s", iteration, progress)
            if progress == 0:
                break

        final_progress = self._match_transactions_pass(system_rows, bank_rows, FINAL_STAGE, allow_review=True)
        review_progress = self._mark_remaining_review_candidates(system_rows, bank_rows)
        logger.debug(
            "Vòng dò cuối cho các ca còn lại hoàn tất. matched_progress=%s | review_progress=%s",
            final_progress,
            review_progress,
        )

    def _match_transactions_pass(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
        stage: str,
        *,
        allow_review: bool,
    ) -> int:
        system_groups: dict[tuple[str, int], list[SystemTransaction]] = defaultdict(list)
        bank_groups: dict[tuple[str, int], list[BankTransaction]] = defaultdict(list)

        for row in system_rows:
            if row.status == "unmatched" and row.amount > 0:
                system_groups[(row.direction, row.amount)].append(row)
        for row in bank_rows:
            if row.status == "unmatched" and row.amount > 0:
                bank_groups[(row.direction, row.amount)].append(row)

        matched_count = 0
        for group_key in sorted(set(system_groups) | set(bank_groups)):
            system_group = system_groups.get(group_key, [])
            bank_group = bank_groups.get(group_key, [])
            if not system_group or not bank_group:
                continue
            if stage == FINAL_STAGE and len(system_group) > 1 and len(bank_group) > 1:
                logger.debug(
                    "Bỏ qua nhóm n-n ở vòng cuối để tránh auto-match rủi ro. "
                    "direction=%s | amount=%s | system_rows=%s | bank_rows=%s",
                    group_key[0],
                    group_key[1],
                    len(system_group),
                    len(bank_group),
                )
                continue

            candidate_map, per_system_scores, per_bank_scores = self._build_stage_candidates(
                system_group,
                bank_group,
                stage,
            )
            if not candidate_map:
                continue

            system_lookup = {row.row_id: row for row in system_group}
            bank_lookup = {row.row_id: row for row in bank_group}
            selected_pairs = self._optimal_pairings(system_group, bank_group, candidate_map)

            for system_id, bank_id in selected_pairs:
                pair = candidate_map[(system_id, bank_id)]
                system_row = system_lookup[system_id]
                bank_row = bank_lookup[bank_id]
                status = self._resolve_status(
                    pair,
                    stage,
                    allow_review,
                    self._best_gap(per_system_scores.get(system_id, []), pair.score),
                    self._best_gap(per_bank_scores.get(bank_id, []), pair.score),
                )
                self._apply_pair(system_row, bank_row, pair, status)
                matched_count += 1

        logger.debug("Pass %s ghép thêm %s cặp.", stage, matched_count)
        return matched_count

    def _build_stage_candidates(
        self,
        system_group: list[SystemTransaction],
        bank_group: list[BankTransaction],
        stage: str,
    ) -> tuple[
        dict[tuple[str, str], PairScore],
        dict[str, list[int]],
        dict[str, list[int]],
    ]:
        pair_scores: dict[tuple[str, str], PairScore] = {}
        for system_row in system_group:
            for bank_row in bank_group:
                pair = self._score_pair(system_row, bank_row, len(system_group), len(bank_group))
                pair_scores[(system_row.row_id, bank_row.row_id)] = pair

        closest_system_gap = self._closest_date_stats_by_system(pair_scores)
        closest_bank_gap = self._closest_date_stats_by_bank(pair_scores)

        candidate_map: dict[tuple[str, str], PairScore] = {}
        per_system_scores: dict[str, list[int]] = defaultdict(list)
        per_bank_scores: dict[str, list[int]] = defaultdict(list)
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
            if not self._candidate_allowed_for_stage(pair, stage):
                continue
            candidate_map[key] = pair
            per_system_scores[system_id].append(pair.score)
            per_bank_scores[bank_id].append(pair.score)
        return candidate_map, per_system_scores, per_bank_scores

    @staticmethod
    def _candidate_allowed_for_stage(pair: PairScore, stage: str) -> bool:
        if stage == "reference":
            return pair.has_reference
        if stage == "voucher_unique":
            return pair.date_gap == 0 and pair.date_source == "voucher" and (
                pair.unique_group or pair.mutual_closest
            )
        if stage == "derived_unique":
            return pair.date_gap == 0 and pair.date_source == "reference" and (
                pair.unique_group or pair.mutual_closest
            )
        if stage == FINAL_STAGE:
            return (
                pair.score >= MINIMUM_MATCH_SCORE
                or pair.date_gap == 0
                or pair.date_gap == 1
                or pair.mutual_closest
                or (pair.unique_group and pair.date_gap <= 7)
            )
        return False

    def _resolve_status(
        self,
        pair: PairScore,
        stage: str,
        allow_review: bool,
        system_gap: int,
        bank_gap: int,
    ) -> str:
        if not allow_review:
            return "matched"

        confident = (
            pair.has_reference
            or (pair.unique_group and pair.date_gap <= 1)
            or (pair.unique_group and pair.date_gap <= 3 and pair.text_score >= 0.45)
            or (pair.mutual_closest and pair.date_gap <= 1 and system_gap >= 6 and bank_gap >= 6)
            or (pair.score >= GREEN_THRESHOLD and system_gap >= SAFETY_GAP and bank_gap >= SAFETY_GAP)
        )
        if stage == FINAL_STAGE and confident:
            return "matched"
        return "review"

    def _apply_pair(
        self,
        system_row: SystemTransaction,
        bank_row: BankTransaction,
        pair: PairScore,
        status: str,
    ) -> None:
        bank_has_vat = abs(getattr(bank_row, "vat", 0)) > 0
        system_row.status = status
        bank_row.status = status
        system_row.match_type = "exact"
        bank_row.match_type = "exact"
        system_row.rule_code = "exact"
        bank_row.rule_code = "exact"
        system_row.group_id = None
        bank_row.group_id = None
        system_row.group_order = 0
        bank_row.group_order = 0
        system_row.review_group_id = None
        bank_row.review_group_id = None
        system_row.review_group_order = 0
        bank_row.review_group_order = 0
        system_row.confidence = pair.score
        bank_row.confidence = pair.score
        system_row.match_reason = "\n".join(pair.reasons)
        bank_row.match_reason = "\n".join(pair.reasons)
        system_row.matched_bank_id = bank_row.row_id
        bank_row.matched_system_id = system_row.row_id
        system_row.matched_bank_row = bank_row.excel_row
        bank_row.matched_system_row = system_row.excel_row
        system_row.review_bank_ids = []
        system_row.review_bank_rows = []
        bank_row.review_system_ids = []
        bank_row.review_system_rows = []
        system_row.has_tax = system_row.has_tax or bank_row.has_tax
        system_row.matched_tax = system_row.matched_tax or bank_has_vat
        bank_row.matched_tax = bank_row.matched_tax or bank_has_vat
        shared_prefixes = system_row.reference_prefixes | bank_row.reference_prefixes
        system_row.reference_prefixes = shared_prefixes
        bank_row.reference_prefixes = shared_prefixes
        logger.debug(
            "Ghép cặp thành công. status=%s | system_row=%s | bank_row=%s | score=%s | reasons=%s",
            status,
            system_row.excel_row,
            bank_row.excel_row,
            pair.score,
            " | ".join(pair.reasons),
        )

    def _match_tax_aggregates(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> int:
        unmatched_system_rows = [
            row for row in system_rows if row.status == "unmatched" and row.direction == "expense"
        ]
        unmatched_tax_bank_rows = [
            row
            for row in bank_rows
            if row.status == "unmatched" and row.direction == "expense" and abs(getattr(row, "vat", 0)) > 0
        ]
        if not unmatched_system_rows or not unmatched_tax_bank_rows:
            return 0

        bank_groups: dict[tuple[date | None, str], list[BankTransaction]] = defaultdict(list)
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
                self._mark_tax_group_match(near_candidates[0], group_rows, "matched")
                matched_system_ids.add(near_candidates[0].row_id)
                matched_group_count += 1

        if matched_group_count:
            logger.info(
                "Đã ghép bổ sung %s nhóm thuế/VAT sau vòng dò nghiêm ngặt.",
                matched_group_count,
            )
        return matched_group_count

    def _match_bank_component_splits(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> int:
        unmatched_system_rows = [
            row
            for row in system_rows
            if row.status == "unmatched" and row.direction == "expense" and row.amount > 0
        ]
        unmatched_bank_rows = [
            row
            for row in bank_rows
            if row.status == "unmatched"
            and row.direction == "expense"
            and len(self._bank_component_values(row)) >= 2
        ]
        if not unmatched_system_rows or not unmatched_bank_rows:
            return 0

        matched_system_ids: set[str] = set()
        matched_bank_ids: set[str] = set()
        matched_group_count = 0

        for bank_row in sorted(
            unmatched_bank_rows,
            key=lambda row: (self._bank_effective_date(row) or date.min, row.excel_row),
        ):
            if bank_row.row_id in matched_bank_ids or bank_row.status != "unmatched":
                continue
            component_values = self._bank_component_values(bank_row)
            if len(component_values) < 2:
                continue

            candidate_system_rows = [
                row
                for row in unmatched_system_rows
                if row.row_id not in matched_system_ids
                and row.status == "unmatched"
                and self._composite_component_candidate_allowed(row, bank_row)
            ]
            if not candidate_system_rows:
                continue

            matches = self._find_composite_system_matches(candidate_system_rows, component_values)
            if len(matches) != 1:
                continue

            selected_rows = matches[0]
            self._mark_bank_component_group_match(bank_row, selected_rows, component_values)
            matched_bank_ids.add(bank_row.row_id)
            matched_system_ids.update(row.row_id for row in selected_rows)
            matched_group_count += 1

        if matched_group_count:
            logger.info(
                "ÄÃ£ ghÃ©p bá»• sung %s nhÃ³m sao kÃª composite chi+phÃ­(+VAT) vá» há»‡ thá»‘ng.",
                matched_group_count,
            )
        return matched_group_count

    @staticmethod
    def _bank_component_values(bank_row: BankTransaction) -> list[tuple[str, int]]:
        component_values: list[tuple[str, int]] = []
        if bank_row.debit:
            component_values.append(("debit", abs(bank_row.debit)))
        if bank_row.fee:
            component_values.append(("fee", abs(bank_row.fee)))
        if bank_row.vat:
            component_values.append(("vat", abs(bank_row.vat)))
        return component_values

    def _find_composite_system_matches(
        self,
        candidate_system_rows: list[SystemTransaction],
        component_values: list[tuple[str, int]],
    ) -> list[list[SystemTransaction]]:
        unique_matches: dict[tuple[str, ...], list[SystemTransaction]] = {}
        for partition_totals in self._component_partitions(component_values):
            for matched_rows in self._collect_partition_matches(candidate_system_rows, partition_totals):
                row_ids = tuple(sorted(row.row_id for row in matched_rows))
                unique_matches.setdefault(
                    row_ids,
                    sorted(matched_rows, key=self._review_group_sort_key),
                )
        return list(unique_matches.values())

    def _collect_partition_matches(
        self,
        candidate_system_rows: list[SystemTransaction],
        partition_totals: tuple[int, ...],
    ) -> list[list[SystemTransaction]]:
        ordered_totals = tuple(sorted(partition_totals, reverse=True))
        amount_map: dict[int, list[SystemTransaction]] = defaultdict(list)
        for row in candidate_system_rows:
            amount_map[row.amount].append(row)
        for rows in amount_map.values():
            rows.sort(key=self._review_group_sort_key)

        matches: list[list[SystemTransaction]] = []

        def backtrack(position: int, used_ids: set[str], current_rows: list[SystemTransaction]) -> None:
            if position >= len(ordered_totals):
                matches.append(list(current_rows))
                return
            target_amount = ordered_totals[position]
            for row in amount_map.get(target_amount, []):
                if row.row_id in used_ids:
                    continue
                used_ids.add(row.row_id)
                current_rows.append(row)
                backtrack(position + 1, used_ids, current_rows)
                current_rows.pop()
                used_ids.remove(row.row_id)

        backtrack(0, set(), [])
        return matches

    @staticmethod
    def _component_partitions(component_values: list[tuple[str, int]]) -> list[tuple[int, ...]]:
        values = [value for _name, value in component_values if value > 0]
        if len(values) < 2:
            return []
        if len(values) == 2:
            return [tuple(sorted(values, reverse=True))]
        a, b, c = values
        partitions = {
            tuple(sorted((a, b, c), reverse=True)),
            tuple(sorted((a + b, c), reverse=True)),
            tuple(sorted((a + c, b), reverse=True)),
            tuple(sorted((b + c, a), reverse=True)),
        }
        return sorted(partitions, key=lambda item: (len(item), item), reverse=True)

    def _composite_component_candidate_allowed(
        self,
        system_row: SystemTransaction,
        bank_row: BankTransaction,
    ) -> bool:
        date_gap, _source = self._date_gap_info(system_row, bank_row)
        return date_gap <= 7

    def _mark_bank_component_group_match(
        self,
        bank_row: BankTransaction,
        system_rows: list[SystemTransaction],
        component_values: list[tuple[str, int]],
    ) -> None:
        group_id = self._next_group_id("cmp")
        ordered_system_rows = sorted(system_rows, key=self._review_group_sort_key)
        component_text = self._composite_component_text(component_values)
        confidence = 90
        reason = (
            f"GhÃ©p 1 dÃ²ng sao kÃª cÃ³ {component_text} thÃ nh {len(ordered_system_rows)} dÃ²ng há»‡ thá»‘ng"
            f" (tá»•ng {bank_row.amount:,.0f})"
        )

        bank_row.status = "matched"
        bank_row.match_type = "group"
        bank_row.rule_code = "bank_composite_split"
        bank_row.group_id = group_id
        bank_row.group_order = 1
        bank_row.review_group_id = None
        bank_row.review_group_order = 0
        bank_row.confidence = confidence
        bank_row.match_reason = reason
        bank_row.matched_system_id = ordered_system_rows[0].row_id
        bank_row.matched_system_row = ordered_system_rows[0].excel_row
        bank_row.review_system_ids = []
        bank_row.review_system_rows = []

        shared_prefixes = set(bank_row.reference_prefixes)
        for order, system_row in enumerate(ordered_system_rows, start=1):
            system_row.status = "matched"
            system_row.match_type = "group"
            system_row.rule_code = "bank_composite_split"
            system_row.group_id = group_id
            system_row.group_order = order
            system_row.review_group_id = None
            system_row.review_group_order = 0
            system_row.confidence = confidence
            system_row.match_reason = reason
            system_row.matched_bank_id = bank_row.row_id
            system_row.matched_bank_row = bank_row.excel_row
            system_row.review_bank_ids = []
            system_row.review_bank_rows = []
            shared_prefixes |= system_row.reference_prefixes

        bank_row.reference_prefixes = shared_prefixes
        for system_row in ordered_system_rows:
            system_row.reference_prefixes = shared_prefixes

    @staticmethod
    def _composite_component_text(component_values: list[tuple[str, int]]) -> str:
        component_labels = {
            "debit": "chi",
            "fee": "phÃ­",
            "vat": "thuáº¿",
        }
        return " + ".join(
            f"{component_labels.get(name, name)} {value:,.0f}"
            for name, value in component_values
            if value > 0
        )

    def _mark_remaining_review_candidates(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> int:
        system_groups: dict[tuple[str, int], list[SystemTransaction]] = defaultdict(list)
        bank_groups: dict[tuple[str, int], list[BankTransaction]] = defaultdict(list)

        for row in system_rows:
            if row.status == "unmatched" and row.amount > 0:
                system_groups[(row.direction, row.amount)].append(row)
        for row in bank_rows:
            if row.status == "unmatched" and row.amount > 0:
                bank_groups[(row.direction, row.amount)].append(row)

        changed = 0
        grouped_review_count = 0
        for group_key in sorted(set(system_groups) & set(bank_groups)):
            system_group = system_groups[group_key]
            bank_group = bank_groups[group_key]
            if not system_group or not bank_group:
                continue

            pair_scores: dict[tuple[str, str], PairScore] = {}
            for system_row in system_group:
                for bank_row in bank_group:
                    pair_scores[(system_row.row_id, bank_row.row_id)] = self._score_pair(
                        system_row,
                        bank_row,
                        len(system_group),
                        len(bank_group),
                    )

            same_day_by_system: dict[str, int] = defaultdict(int)
            same_day_by_bank: dict[str, int] = defaultdict(int)
            for (system_id, bank_id), pair in pair_scores.items():
                if pair.date_gap == 0:
                    same_day_by_system[system_id] += 1
                    same_day_by_bank[bank_id] += 1

            system_candidates: dict[str, list[tuple[BankTransaction, PairScore]]] = defaultdict(list)
            bank_candidates: dict[str, list[tuple[SystemTransaction, PairScore]]] = defaultdict(list)
            system_lookup = {row.row_id: row for row in system_group}
            bank_lookup = {row.row_id: row for row in bank_group}
            for (system_id, bank_id), pair in pair_scores.items():
                if not self._review_candidate_allowed(
                    pair,
                    same_day_by_system.get(system_id, 0),
                    same_day_by_bank.get(bank_id, 0),
                ):
                    continue
                system_candidates[system_id].append((bank_lookup[bank_id], pair))
                bank_candidates[bank_id].append((system_lookup[system_id], pair))

            for system_id, candidates in system_candidates.items():
                changed += self._apply_review_candidates(
                    system_lookup[system_id],
                    candidates,
                    counterpart_label="sao kê",
                )
            for bank_id, candidates in bank_candidates.items():
                changed += self._apply_review_candidates(
                    bank_lookup[bank_id],
                    candidates,
                    counterpart_label="hệ thống",
                )

            grouped_review_count += self._assign_review_groups(
                system_group,
                bank_group,
                system_candidates,
                bank_candidates,
            )

        if changed:
            logger.info(
                "Đã chuyển %s dòng còn lại sang trạng thái review vì có ứng viên hợp lý.",
                changed,
            )
        if grouped_review_count:
            logger.info("Đã gom %s nhóm n-n trong phần cần kiểm tra.", grouped_review_count)
        return changed

    @staticmethod
    def _review_candidate_allowed(pair: PairScore, system_same_day_count: int, bank_same_day_count: int) -> bool:
        if pair.has_reference:
            return True
        if pair.date_gap == 0:
            return True
        if pair.date_gap <= 1 and pair.text_score >= 0.3:
            return True
        if pair.date_gap <= 3 and pair.text_score >= 0.45:
            return True
        if pair.mutual_closest and pair.date_gap <= 1:
            return True
        return False

    def _apply_review_candidates(self, row, candidates: list[tuple[object, PairScore]], *, counterpart_label: str) -> int:
        if row.status != "unmatched" or not candidates:
            return 0
        ordered = sorted(
            candidates,
            key=lambda item: self._pair_priority(item[1]),
            reverse=True,
        )
        preview = ", ".join(str(getattr(candidate, "excel_row", "")) for candidate, _pair in ordered[:3] if getattr(candidate, "excel_row", None))
        top_pair = ordered[0][1]
        row.status = "review"
        row.match_type = "none"
        row.rule_code = "review_candidate"
        row.group_id = None
        row.group_order = 0
        row.review_group_id = None
        row.review_group_order = 0
        row.confidence = min(max(top_pair.score, 55), 79)
        counterpart_ids = [getattr(candidate, "row_id", "") for candidate, _pair in ordered if getattr(candidate, "row_id", "")]
        counterpart_rows = [getattr(candidate, "excel_row", 0) for candidate, _pair in ordered if getattr(candidate, "excel_row", None)]
        if hasattr(row, "matched_bank_id"):
            row.matched_bank_id = None
            row.matched_bank_row = None
            row.review_bank_ids = counterpart_ids
            row.review_bank_rows = counterpart_rows
        if hasattr(row, "matched_system_id"):
            row.matched_system_id = None
            row.matched_system_row = None
            row.review_system_ids = counterpart_ids
            row.review_system_rows = counterpart_rows
        reason_lines = [
            f"Có {len(ordered)} ứng viên {counterpart_label} cùng chiều và cùng số tiền.",
            *top_pair.reasons[:3],
        ]
        if preview:
            reason_lines.append(f"Dòng ứng viên {counterpart_label}: {preview}")
        row.match_reason = "\n".join(reason_lines)
        return 1

    def _assign_review_groups(
        self,
        system_group: list[SystemTransaction],
        bank_group: list[BankTransaction],
        system_candidates: dict[str, list[tuple[BankTransaction, PairScore]]],
        bank_candidates: dict[str, list[tuple[SystemTransaction, PairScore]]],
    ) -> int:
        system_edges: dict[str, set[str]] = {}
        bank_edges: dict[str, set[str]] = {}

        for system_row in system_group:
            if system_row.status != "review":
                continue
            bank_ids = {
                candidate.row_id
                for candidate, _pair in system_candidates.get(system_row.row_id, [])
                if getattr(candidate, "status", "unmatched") == "review"
            }
            if bank_ids:
                system_edges[system_row.row_id] = bank_ids

        for bank_row in bank_group:
            if bank_row.status != "review":
                continue
            system_ids = {
                candidate.row_id
                for candidate, _pair in bank_candidates.get(bank_row.row_id, [])
                if getattr(candidate, "status", "unmatched") == "review"
            }
            if system_ids:
                bank_edges[bank_row.row_id] = system_ids

        if not system_edges or not bank_edges:
            return 0

        system_lookup = {row.row_id: row for row in system_group}
        bank_lookup = {row.row_id: row for row in bank_group}
        visited_system: set[str] = set()
        visited_bank: set[str] = set()
        assigned_groups = 0

        for seed_system_id in sorted(system_edges):
            if seed_system_id in visited_system:
                continue

            component_system_ids: set[str] = set()
            component_bank_ids: set[str] = set()
            queue: list[tuple[str, str]] = [("system", seed_system_id)]

            while queue:
                side, row_id = queue.pop()
                if side == "system":
                    if row_id in visited_system:
                        continue
                    visited_system.add(row_id)
                    component_system_ids.add(row_id)
                    for bank_id in sorted(system_edges.get(row_id, set())):
                        if bank_id not in component_bank_ids:
                            queue.append(("bank", bank_id))
                else:
                    if row_id in visited_bank:
                        continue
                    visited_bank.add(row_id)
                    component_bank_ids.add(row_id)
                    for system_id in sorted(bank_edges.get(row_id, set())):
                        if system_id not in component_system_ids:
                            queue.append(("system", system_id))

            if len(component_system_ids) <= 1 or len(component_bank_ids) <= 1:
                continue
            if len(component_system_ids) != len(component_bank_ids):
                continue

            component_system_rows = [
                system_lookup[row_id]
                for row_id in component_system_ids
                if row_id in system_lookup
            ]
            component_bank_rows = [
                bank_lookup[row_id]
                for row_id in component_bank_ids
                if row_id in bank_lookup
            ]
            if len(component_system_rows) != len(component_system_ids):
                continue
            if len(component_bank_rows) != len(component_bank_ids):
                continue

            self._mark_review_group(component_system_rows, component_bank_rows)
            assigned_groups += 1

        return assigned_groups

    def _mark_review_group(
        self,
        system_rows: list[SystemTransaction],
        bank_rows: list[BankTransaction],
    ) -> None:
        review_group_id = self._next_group_id("r")
        ordered_system_rows = sorted(system_rows, key=self._review_group_sort_key)
        ordered_bank_rows = sorted(bank_rows, key=self._review_group_sort_key)
        system_ids = [row.row_id for row in ordered_system_rows]
        bank_ids = [row.row_id for row in ordered_bank_rows]
        system_excel_rows = [row.excel_row for row in ordered_system_rows]
        bank_excel_rows = [row.excel_row for row in ordered_bank_rows]
        reason_line = (
            f"Thuộc nhóm cần kiểm tra {review_group_id} "
            f"({len(ordered_system_rows)}-{len(ordered_bank_rows)})"
        )

        for order, row in enumerate(ordered_system_rows, start=1):
            row.rule_code = "review_nn_group"
            row.review_group_id = review_group_id
            row.review_group_order = order
            row.review_bank_ids = list(bank_ids)
            row.review_bank_rows = list(bank_excel_rows)
            row.match_reason = self._prepend_reason_line(row.match_reason, reason_line)

        for order, row in enumerate(ordered_bank_rows, start=1):
            row.rule_code = "review_nn_group"
            row.review_group_id = review_group_id
            row.review_group_order = order
            row.review_system_ids = list(system_ids)
            row.review_system_rows = list(system_excel_rows)
            row.match_reason = self._prepend_reason_line(row.match_reason, reason_line)

    def _review_group_sort_key(self, row) -> tuple[date, int]:
        row_date = getattr(row, "voucher_date", None)
        if row_date is None:
            row_date = self._bank_effective_date(row)
        return (row_date or date.min, getattr(row, "excel_row", 0))

    @staticmethod
    def _prepend_reason_line(existing_reason: str, line: str) -> str:
        parts = [segment.strip() for segment in (existing_reason or "").splitlines() if segment.strip()]
        if line in parts:
            return existing_reason
        return "\n".join([line, *parts])

    def _mark_tax_group_match(
        self,
        system_row: SystemTransaction,
        bank_rows: list[BankTransaction],
        status: str,
    ) -> None:
        group_id = self._next_group_id("vat")
        total_amount = sum(row.amount for row in bank_rows)
        first_bank_row = min(bank_rows, key=lambda row: row.excel_row)
        group_date = self._bank_effective_date(first_bank_row)
        reason = (
            f"Ghép gom {len(bank_rows)} dòng sao kê có VAT thành 1 dòng chi hệ thống"
            f" (ngày {group_date}, tổng {total_amount:,.0f})"
        )
        confidence = 92 if status == "matched" else 76
        system_row.status = status
        system_row.match_type = "group"
        system_row.rule_code = "tax_vat_group"
        system_row.group_id = group_id
        system_row.group_order = 0
        system_row.review_group_id = None
        system_row.review_group_order = 0
        system_row.confidence = confidence
        system_row.match_reason = reason
        system_row.has_tax = True
        system_row.matched_tax = True
        system_row.matched_bank_id = first_bank_row.row_id
        system_row.matched_bank_row = first_bank_row.excel_row
        system_row.review_bank_ids = []
        system_row.review_bank_rows = []
        shared_prefixes = set(system_row.reference_prefixes)
        for order, bank_row in enumerate(sorted(bank_rows, key=lambda row: row.excel_row), start=1):
            bank_row.status = status
            bank_row.match_type = "group"
            bank_row.rule_code = "tax_vat_group"
            bank_row.group_id = group_id
            bank_row.group_order = order
            bank_row.review_group_id = None
            bank_row.review_group_order = 0
            bank_row.confidence = confidence
            bank_row.match_reason = reason
            bank_row.matched_tax = True
            bank_row.matched_system_id = system_row.row_id
            bank_row.matched_system_row = system_row.excel_row
            bank_row.review_system_ids = []
            bank_row.review_system_rows = []
            shared_prefixes |= bank_row.reference_prefixes
        system_row.reference_prefixes = shared_prefixes
        for bank_row in bank_rows:
            bank_row.reference_prefixes = shared_prefixes

    def _next_group_id(self, prefix: str) -> str:
        self._group_sequence += 1
        return f"{prefix.upper()}-{self._group_sequence:04d}"

    @staticmethod
    def _bank_effective_date(bank_row: BankTransaction) -> date | None:
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

        date_gap, date_source = self._date_gap_info(system_row, bank_row)
        if date_gap == 0:
            score += 24
            reasons.append(self._date_reason(date_source, "same"))
        elif date_gap == 1:
            score += 18
            reasons.append(self._date_reason(date_source, "near_1"))
        elif date_gap <= 3:
            score += 12
            reasons.append(self._date_reason(date_source, "near"))
        elif date_gap <= 7:
            score += 6
            reasons.append(self._date_reason(date_source, "acceptable"))
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
            date_source=date_source,
            unique_group=unique_group,
            has_reference=bool(reference_overlap),
            text_score=text_score,
        )

    @classmethod
    def _date_gap_info(cls, system_row: SystemTransaction, bank_row: BankTransaction) -> tuple[int, str]:
        bank_date = cls._bank_effective_date(bank_row)
        if bank_date is None:
            return 99, "missing"
        candidates: list[tuple[int, str]] = []
        if system_row.voucher_date is not None:
            candidates.append((abs((system_row.voucher_date - bank_date).days), "voucher"))
        for reference_date in cls._system_reference_dates(system_row):
            candidates.append((abs((reference_date - bank_date).days), "reference"))
        if not candidates:
            return 99, "missing"
        return min(candidates, key=lambda item: (item[0], 0 if item[1] == "voucher" else 1))

    @staticmethod
    def _date_reason(source: str, level: str) -> str:
        if source == "reference":
            labels = {
                "same": "Ngày theo mã nội bộ trùng ngày",
                "near_1": "Ngày theo mã nội bộ lệch 1 ngày",
                "near": "Ngày theo mã nội bộ gần nhau",
                "acceptable": "Ngày theo mã nội bộ có thể chấp nhận",
            }
        else:
            labels = {
                "same": "Ngày giao dịch trùng ngày",
                "near_1": "Ngày giao dịch lệch 1 ngày",
                "near": "Ngày giao dịch gần nhau",
                "acceptable": "Ngày giao dịch có thể chấp nhận",
            }
        return labels[level]

    @staticmethod
    def _system_reference_dates(system_row: SystemTransaction) -> set[date]:
        dates: set[date] = set()
        for token in system_row.reference_tokens:
            match = re.match(r"SK(\d{8})-\d+$", token)
            if not match:
                continue
            try:
                dates.add(datetime.strptime(match.group(1), "%Y%m%d").date())
            except ValueError:
                continue
        return dates

    @staticmethod
    def _closest_date_stats_by_system(pair_scores: dict[tuple[str, str], PairScore]) -> dict[str, tuple[int, int]]:
        gaps: dict[str, tuple[int, int]] = {}
        for (system_id, _bank_id), pair in pair_scores.items():
            current = gaps.get(system_id)
            if current is None or pair.date_gap < current[0]:
                gaps[system_id] = (pair.date_gap, 1)
            elif pair.date_gap == current[0]:
                gaps[system_id] = (current[0], current[1] + 1)
        return gaps

    @staticmethod
    def _closest_date_stats_by_bank(pair_scores: dict[tuple[str, str], PairScore]) -> dict[str, tuple[int, int]]:
        gaps: dict[str, tuple[int, int]] = {}
        for (_system_id, bank_id), pair in pair_scores.items():
            current = gaps.get(bank_id)
            if current is None or pair.date_gap < current[0]:
                gaps[bank_id] = (pair.date_gap, 1)
            elif pair.date_gap == current[0]:
                gaps[bank_id] = (current[0], current[1] + 1)
        return gaps

    @staticmethod
    def _is_mutual_closest_date_pair(
        pair: PairScore,
        system_gap: tuple[int, int] | None,
        bank_gap: tuple[int, int] | None,
    ) -> bool:
        return (
            pair.date_gap <= 3
            and system_gap is not None
            and bank_gap is not None
            and pair.date_gap == system_gap[0]
            and pair.date_gap == bank_gap[0]
            and system_gap[1] == 1
            and bank_gap[1] == 1
        )

    def _optimal_pairings(
        self,
        system_group: list[SystemTransaction],
        bank_group: list[BankTransaction],
        candidate_map: dict[tuple[str, str], PairScore],
    ) -> list[tuple[str, str]]:
        if not candidate_map:
            return []

        transpose = len(system_group) > len(bank_group)
        primary_ids = [row.row_id for row in (bank_group if transpose else system_group)]
        secondary_ids = [row.row_id for row in (system_group if transpose else bank_group)]
        secondary_index = {row_id: index for index, row_id in enumerate(secondary_ids)}
        options_by_primary: dict[str, list[tuple[int, str, str, PairScore]]] = defaultdict(list)

        for (system_id, bank_id), pair in candidate_map.items():
            primary_id = bank_id if transpose else system_id
            secondary_id = system_id if transpose else bank_id
            options_by_primary[primary_id].append((secondary_index[secondary_id], system_id, bank_id, pair))

        for options in options_by_primary.values():
            options.sort(key=lambda item: self._pair_priority(item[3]), reverse=True)

        @lru_cache(maxsize=None)
        def solve(position: int, used_mask: int) -> tuple[int, int, int, tuple[tuple[str, str], ...]]:
            if position >= len(primary_ids):
                return (0, 0, 0, ())

            best = solve(position + 1, used_mask)
            primary_id = primary_ids[position]
            for secondary_pos, system_id, bank_id, pair in options_by_primary.get(primary_id, []):
                if used_mask & (1 << secondary_pos):
                    continue
                tail = solve(position + 1, used_mask | (1 << secondary_pos))
                candidate = (
                    tail[0] + pair.score,
                    tail[1] + 1,
                    tail[2] + self._pair_tie_score(pair),
                    ((system_id, bank_id),) + tail[3],
                )
                if candidate[:3] > best[:3]:
                    best = candidate
            return best

        return list(solve(0, 0)[3])

    def _pair_tie_score(self, pair: PairScore) -> int:
        priority = self._pair_priority(pair)
        return (
            (1_000_000 if priority[0] else 0)
            + (100_000 if priority[1] else 0)
            + (10_000 if priority[2] else 0)
            + (1_000 if priority[3] else 0)
            + max(0, 200 - pair.date_gap)
            + max(0, pair.score) * 5
            + int(pair.text_score * 100)
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
