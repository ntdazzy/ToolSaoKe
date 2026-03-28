from __future__ import annotations

import logging
from datetime import datetime
import sys
from pathlib import Path


class DailyFileHandler(logging.FileHandler):
    def __init__(self, logs_dir: Path) -> None:
        self.logs_dir = logs_dir
        self.current_date_key = ""
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        super().__init__(self._resolve_log_path(), encoding="utf-8", delay=True)

    def _today_key(self) -> str:
        return datetime.now().strftime("%Y%m%d")

    def _resolve_log_path(self) -> str:
        self.current_date_key = self._today_key()
        return str(self.logs_dir / f"{self.current_date_key}.log")

    def emit(self, record: logging.LogRecord) -> None:
        today_key = self._today_key()
        if today_key != self.current_date_key:
            self.acquire()
            try:
                if self.stream:
                    self.stream.close()
                    self.stream = None
                self.baseFilename = str(self.logs_dir / f"{today_key}.log")
                self.current_date_key = today_key
            finally:
                self.release()
        try:
            super().emit(record)
        except PermissionError:
            if self.stream is None:
                self.stream = self._open()
            super().emit(record)
        except OSError:
            if self.stream is None:
                self.stream = self._open()
            super().emit(record)


def get_app_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_log_file_path() -> Path:
    return get_logs_dir() / f"{datetime.now():%Y%m%d}.log"


def get_logs_dir() -> Path:
    return get_app_base_dir() / "data" / "logs"


def setup_logging() -> Path:
    log_file_path = get_log_file_path()
    logs_dir = get_logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    existing_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if isinstance(handler, DailyFileHandler)
        ),
        None,
    )
    if existing_handler is not None:
        return log_file_path

    file_handler = DailyFileHandler(logs_dir)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root_logger.addHandler(file_handler)
    logging.captureWarnings(True)
    logging.getLogger(__name__).info("Đã khởi tạo log file tại %s", log_file_path)
    return log_file_path
