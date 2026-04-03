from __future__ import annotations

import os
import sys
import logging

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.logging_utils import (
    get_log_file_path,
    install_exception_hooks,
    install_qt_message_logging,
)
from app.resource_utils import logo_image_path
from app.ui.main_window import MainWindow


def _configure_utf8() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _configure_utf8()
    install_exception_hooks()
    install_qt_message_logging()
    logger = logging.getLogger(__name__)
    logger.info("Khởi động ứng dụng. Log file: %s", get_log_file_path())
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    logo_path = logo_image_path()
    if logo_path.exists():
        app.setWindowIcon(QIcon(str(logo_path)))
    window = MainWindow()
    window.show()
    exit_code = app.exec()
    logger.info("Ứng dụng đóng với mã thoát %s", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
