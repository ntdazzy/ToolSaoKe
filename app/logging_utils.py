from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


class SafeRotatingFileHandler(RotatingFileHandler):
    def doRollover(self) -> None:  # type: ignore[override]
        try:
            super().doRollover()
        except PermissionError:
            # Another process may be holding the log file on Windows.
            # Keep writing to the current file instead of crashing logging.
            if self.stream is None:
                self.stream = self._open()
        except OSError:
            if self.stream is None:
                self.stream = self._open()


def get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_log_file_path() -> Path:
    return get_app_base_dir() / "data" / "logs" / "tool_doi_soat.log"


def setup_logging() -> Path:
    log_file_path = get_log_file_path()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    existing_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if isinstance(handler, RotatingFileHandler)
            and Path(getattr(handler, "baseFilename", "")) == log_file_path
        ),
        None,
    )
    if existing_handler is not None:
        return log_file_path

    file_handler = SafeRotatingFileHandler(
        log_file_path,
        maxBytes=3_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root_logger.addHandler(file_handler)
    logging.captureWarnings(True)
    logging.getLogger(__name__).info("Đã khởi tạo log file tại %s", log_file_path)
    return log_file_path
