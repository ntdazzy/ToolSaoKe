from __future__ import annotations

import sqlite3
from pathlib import Path

from app.models import ReconciliationResult


class HistoryStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reconciliation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scanned_at TEXT NOT NULL,
                    system_file TEXT NOT NULL,
                    bank_file TEXT NOT NULL,
                    total_system INTEGER NOT NULL,
                    total_bank INTEGER NOT NULL,
                    matched_system INTEGER NOT NULL,
                    review_system INTEGER NOT NULL,
                    unmatched_system INTEGER NOT NULL,
                    matched_bank INTEGER NOT NULL,
                    review_bank INTEGER NOT NULL,
                    unmatched_bank INTEGER NOT NULL
                )
                """
            )
            connection.commit()

    def add_result(self, result: ReconciliationResult) -> None:
        summary = result.summary
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO reconciliation_history (
                    scanned_at,
                    system_file,
                    bank_file,
                    total_system,
                    total_bank,
                    matched_system,
                    review_system,
                    unmatched_system,
                    matched_bank,
                    review_bank,
                    unmatched_bank
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.scanned_at.isoformat(timespec="seconds"),
                    result.system_file,
                    result.bank_file,
                    summary.total_system,
                    summary.total_bank,
                    summary.matched_system,
                    summary.review_system,
                    summary.unmatched_system,
                    summary.matched_bank,
                    summary.review_bank,
                    summary.unmatched_bank,
                ),
            )
            connection.commit()

    def list_recent(self, limit: int = 8) -> list[dict[str, object]]:
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT *
                FROM reconciliation_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
