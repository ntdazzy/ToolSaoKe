"""Application package for the bank reconciliation desktop tool."""

from __future__ import annotations

import os
import sys


def _configure_utf8_stdio() -> None:
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except ValueError:
                continue


_configure_utf8_stdio()
