from __future__ import annotations


SYSTEM_GRID_FIXED_WIDTHS: dict[int, int] = {
    0: 34,
    3: 250,
    4: 170,
}

BANK_GRID_FIXED_WIDTHS: dict[int, int] = {
    0: 34,
    4: 138,
    5: 132,
    6: 160,
    7: 300,
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
        "Khớp: giao dịch đã có đối ứng an toàn.<br>"
        "Cần kiểm tra: tool tìm thấy ứng viên hợp lý nhưng chưa đủ chắc để tự chốt.<br>"
        "Chưa khớp: chưa tìm được đối ứng phù hợp, hoặc thuộc ca n-n không tự ghép."
    ),
    "en": (
        "<b>Status meaning</b><br>"
        "Matched: a safe counterpart was found.<br>"
        "Needs review: a plausible candidate exists, but the tool is not certain enough.<br>"
        "Unmatched: no safe counterpart was found, including unresolved n-n cases."
    ),
    "zh": (
        "<b>状态说明</b><br>"
        "已匹配：已找到安全的对应交易。<br>"
        "需要复核：存在合理候选，但证据不足以自动确认。<br>"
        "未匹配：尚未找到安全的对应交易，包括未能安全处理的 n-n 情况。"
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

FLOW_FILTER_OPTIONS: list[tuple[str, str]] = [
    ("all", "flow_all"),
    ("income", "flow_income"),
    ("expense", "flow_expense"),
    ("tax", "flow_tax"),
]

MATCH_KIND_FILTER_LABELS: dict[str, dict[str, str]] = {
    "vi": {
        "caption": "Kiểu đối chiếu",
        "all": "Tất cả kiểu",
        "exact": "Khớp lẻ",
        "tax_group": "Phí/VAT",
        "composite_group": "Chi + phí/thuế",
        "review_nn_group": "Nhóm",
    },
    "en": {
        "caption": "Match kind",
        "all": "All kinds",
        "exact": "Exact",
        "tax_group": "Fee/VAT",
        "composite_group": "Debit + fee/tax",
        "review_nn_group": "Groups",
    },
    "zh": {
        "caption": "对照类型",
        "all": "全部类型",
        "exact": "单笔匹配",
        "tax_group": "费用/VAT",
        "composite_group": "支出+费用/税",
        "review_nn_group": "分组",
    },
}

MATCH_KIND_FILTER_OPTIONS_BY_STATUS: dict[str, list[str]] = {
    "all": [
        "all",
        "exact",
        "tax_group",
        "composite_group",
        "review_nn_group",
    ],
    "matched": [
        "all",
        "exact",
        "tax_group",
        "composite_group",
    ],
    "review": [
        "all",
        "review_nn_group",
    ],
}

REFERENCE_PREFIX_SUMMARY_LABELS: dict[str, dict[str, str]] = {
    "vi": {
        "FT": "Chuyển khoản",
        "TT": "Nộp/Rút tiền",
        "LD": "Khoản vay",
        "HB": "Phí/VAT",
        "ST": "Chuyển khoản nội bộ",
        "SK": "Giao dịch dịch vụ",
        "OTHER": "Nhóm",
    },
    "en": {
        "FT": "Transfer",
        "TT": "Cash in/out",
        "LD": "Loan",
        "HB": "Fee/VAT",
        "ST": "Internal transfer",
        "SK": "Service",
        "OTHER": "Group",
    },
    "zh": {
        "FT": "转账",
        "TT": "存取现金",
        "LD": "贷款",
        "HB": "费用/VAT",
        "ST": "内部转账",
        "SK": "服务交易",
        "OTHER": "分组",
    },
}


def date_filter_text(language: str, key: str) -> str:
    language_labels = DATE_FILTER_LABELS.get(language, DATE_FILTER_LABELS["vi"])
    return language_labels[key]


def summary_help_tooltip(language: str) -> str:
    return SUMMARY_HELP_TOOLTIPS.get(language, SUMMARY_HELP_TOOLTIPS["vi"])


def match_kind_text(language: str, key: str) -> str:
    language_labels = MATCH_KIND_FILTER_LABELS.get(language, MATCH_KIND_FILTER_LABELS["vi"])
    return language_labels[key]


def match_kind_options_for_status(status_mode: str) -> list[str]:
    return list(MATCH_KIND_FILTER_OPTIONS_BY_STATUS.get(status_mode, []))


def reference_prefix_summary_text(language: str, prefix: str) -> str:
    language_labels = REFERENCE_PREFIX_SUMMARY_LABELS.get(language, REFERENCE_PREFIX_SUMMARY_LABELS["vi"])
    return language_labels.get(prefix, language_labels["OTHER"])
