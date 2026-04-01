from __future__ import annotations

SYSTEM_GRID_FIXED_WIDTHS: dict[int, int] = {
    2: 250,
    3: 170,
}

BANK_GRID_FIXED_WIDTHS: dict[int, int] = {
    3: 138,
    4: 132,
    5: 160,
    6: 300,
}

BANK_GRID_HEADERS: list[str] = [
    "Ngày yêu cầu",
    "Ngày GD",
    "Mã GD",
    "NH đối tác",
    "TK đối tác",
    "Tên đối tác",
    "Diễn giải",
    "Chi",
    "Thu",
    "Phí",
    "Thuế",
    "Số dư",
]

DATE_FILTER_LABELS: dict[str, dict[str, str]] = {
    "vi": {
        "caption": "Ngày",
        "from": "Từ ngày",
        "to": "Đến ngày",
        "reset": "Tất cả ngày",
    },
    "en": {
        "caption": "Date",
        "from": "From",
        "to": "To",
        "reset": "All dates",
    },
    "zh": {
        "caption": "日期",
        "from": "从",
        "to": "到",
        "reset": "全部日期",
    },
}

SUMMARY_HELP_TOOLTIPS: dict[str, str] = {
    "vi": (
        "<b>Giải thích trạng thái</b><br>"
        "GD khớp: 1 giao dịch hệ thống khớp 1 giao dịch sao kê.<br>"
        "Phí/VAT đã khớp: chỉ áp dụng cho các dòng phí/VAT từ sao kê được gom về 1 dòng hệ thống.<br>"
        "Cần kiểm tra: tool có ứng viên hợp lý nhưng chưa đủ an toàn để chốt.<br>"
        "Chưa khớp: chưa tìm được đối ứng phù hợp, hoặc thuộc ca n-n không tự ghép."
    ),
    "en": (
        "<b>Status meaning</b><br>"
        "Matched: one system row matches one statement row.<br>"
        "Fee/VAT matched: statement fee/VAT rows that were merged into one system row.<br>"
        "Needs review: the tool found a plausible candidate but not enough proof.<br>"
        "Unmatched: no safe counterpart was found, including n-n cases."
    ),
    "zh": (
        "<b>状态说明</b><br>"
        "交易已匹配：系统与流水 1 对 1 对应。<br>"
        "费用/VAT 已匹配：仅显示流水费用/VAT 汇总到 1 条系统记录的情况。<br>"
        "需要复核：存在合理候选，但证据不足。<br>"
        "未匹配：尚未找到安全的对应交易，n-n 默认也归入此类。"
    ),
}

REFERENCE_FILTER_OPTIONS: list[tuple[str, str]] = [
    ("all", "reference_all"),
    ("FT", "reference_ft"),
    ("TT", "reference_tt"),
    ("ST", "reference_st"),
    ("SK", "reference_sk"),
    ("LD", "reference_ld"),
    ("HB", "reference_hb"),
]


def date_filter_text(language: str, key: str) -> str:
    language_labels = DATE_FILTER_LABELS.get(language, DATE_FILTER_LABELS["vi"])
    return language_labels[key]


def summary_help_tooltip(language: str) -> str:
    return SUMMARY_HELP_TOOLTIPS.get(language, SUMMARY_HELP_TOOLTIPS["vi"])
