from __future__ import annotations

import sys
from pathlib import Path


def get_resource_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_path(*parts: str) -> Path:
    return get_resource_base_dir().joinpath(*parts)


def logo_image_path() -> Path:
    return resource_path("logo", "logo.jpg")
