from __future__ import annotations

import logging
from datetime import datetime
import sys
import threading
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


def install_exception_hooks() -> None:
    logger = logging.getLogger("app.runtime")

    def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.exception(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    def _handle_thread_exception(args: threading.ExceptHookArgs) -> None:
        logger.exception(
            "Unhandled thread exception in %s",
            args.thread.name if args.thread else "unknown-thread",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = _handle_exception
    threading.excepthook = _handle_thread_exception


def install_qt_message_logging() -> None:
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        return

    logger = logging.getLogger("app.qt")
    previous_handler = qInstallMessageHandler(None)

    def _qt_message_handler(message_type, context, message) -> None:
        file_name = getattr(context, "file", "") or ""
        line_number = getattr(context, "line", 0) or 0
        category = getattr(context, "category", "") or ""
        location = f"{file_name}:{line_number}" if file_name else ""
        prefix = " | ".join(part for part in (category, location) if part)
        formatted_message = f"{prefix} | {message}" if prefix else message

        if message_type == QtMsgType.QtDebugMsg:
            level = logging.DEBUG
        elif message_type == QtMsgType.QtInfoMsg:
            level = logging.INFO
        elif message_type == QtMsgType.QtWarningMsg:
            level = logging.WARNING
        elif message_type == QtMsgType.QtCriticalMsg:
            level = logging.ERROR
        else:
            level = logging.CRITICAL
        logger.log(level, formatted_message)

        if previous_handler is not None:
            previous_handler(message_type, context, message)

    qInstallMessageHandler(_qt_message_handler)
