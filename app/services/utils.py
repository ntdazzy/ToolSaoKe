from __future__ import annotations

import math
import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher


REFERENCE_PATTERNS = [
    r"\bFT[0-9A-Z.-]{8,}\b",
    r"\bTT[0-9A-Z.-]{8,}\b",
    r"\bLD[0-9A-Z.-]{8,}\b",
    r"\bST[0-9A-Z.-]{6,}\b",
    r"\bSK\d{8}-\d+\b",
    r"\bHB\.[0-9A-Z.-]+\b",
]

TAX_KEYWORDS = {
    "vat",
    "tax",
    "thue",
    "thuegtgt",
    "shui",
    "税",
    "thue/transaction",
}


def to_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def compact_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def remove_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str) -> str:
    lowered = remove_accents(value or "").lower()
    lowered = re.sub(r"[_/|]+", " ", lowered)
    lowered = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff.-]+", " ", lowered)
    return compact_spaces(lowered)


def tokenize(value: str) -> set[str]:
    text = normalize_text(value)
    return {
        token
        for token in text.split()
        if len(token) > 1 or any(char.isdigit() for char in token)
    }


def extract_reference_tokens(value: str) -> set[str]:
    tokens: set[str] = set()
    for pattern in REFERENCE_PATTERNS:
        tokens.update(match.upper() for match in re.findall(pattern, value.upper()))
    return tokens


def parse_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = to_text(value)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_datetime(value: object) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = to_text(value)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    date_only = parse_date(text)
    if date_only is None:
        return None
    return datetime.combine(date_only, datetime.min.time())


def parse_vnd_int(value: object) -> int:
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return 0
        return int(round(value))
    text = to_text(value)
    if not text:
        return 0
    negative = text.startswith("(") and text.endswith(")")
    cleaned = text.replace(",", "").replace(" ", "").replace("(", "").replace(")", "")
    cleaned = cleaned.replace("+", "")
    try:
        number = int(round(float(cleaned)))
    except ValueError:
        return 0
    return -number if negative else number


def format_vnd(value: int | None, blank_for_zero: bool = False) -> str:
    if value is None:
        return ""
    if value == 0 and blank_for_zero:
        return ""
    return f"{value:,.0f}"


def amount_to_display(value: object, blank_for_zero: bool = False) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, str):
        parsed = parse_vnd_int(value)
        if parsed == 0 and "0" not in value:
            return compact_spaces(value)
        return format_vnd(parsed, blank_for_zero=blank_for_zero)
    if isinstance(value, (int, float)):
        return format_vnd(parse_vnd_int(value), blank_for_zero=blank_for_zero)
    return compact_spaces(to_text(value))


def text_similarity(left: str, right: str) -> float:
    left_normalized = normalize_text(left)
    right_normalized = normalize_text(right)
    if not left_normalized or not right_normalized:
        return 0.0
    seq_ratio = SequenceMatcher(None, left_normalized, right_normalized).ratio()
    left_tokens = set(left_normalized.split())
    right_tokens = set(right_normalized.split())
    overlap = len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))
    return max(seq_ratio * 0.65 + overlap * 0.35, overlap)


def contains_tax_keywords(*values: str) -> bool:
    combined = " ".join(normalize_text(value) for value in values if value)
    return any(keyword in combined for keyword in TAX_KEYWORDS)


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_") or "output"
