from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from app.services.reconciliation import ReconciliationService

logger = logging.getLogger(__name__)


class ScanWorker(QObject):
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, system_path: str, bank_path: str) -> None:
        super().__init__()
        self.system_path = system_path
        self.bank_path = bank_path

    @Slot()
    def run(self) -> None:
        try:
            logger.info(
                "Worker bắt đầu dò. system_file=%s | bank_file=%s",
                self.system_path,
                self.bank_path,
            )
            result = ReconciliationService().run(self.system_path, self.bank_path)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Worker dò lỗi: %s", exc)
            self.failed.emit(str(exc))
            return
        logger.info("Worker dò hoàn tất.")
        self.finished.emit(result)
