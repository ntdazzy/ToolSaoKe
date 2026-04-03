from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.i18n import tr
from app.resource_utils import logo_image_path
from app.services.utils import format_vnd
from app.ui.table_models import status_bucket_for_row


class PairDialog(QDialog):
    def __init__(
        self,
        language: str,
        system_title: str,
        system_headers: list[str],
        system_rows,
        bank_title: str,
        bank_headers: list[str],
        bank_rows,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        logo_path = logo_image_path()
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.language = language
        self.system_rows = list(system_rows or [])
        self.bank_rows = list(bank_rows or [])
        self.setWindowTitle(tr(language, "open_pair_title"))
        self.setObjectName("pairDialog")
        self.resize(1120, 720)
        self.setMinimumSize(980, 620)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(18)
        layout.addWidget(self._build_panel(system_title, system_headers, self.system_rows, self.bank_rows), 1)
        layout.addWidget(self._build_panel(bank_title, bank_headers, self.bank_rows, self.system_rows), 1)

    def _build_panel(self, title: str, headers: list[str], rows: list[object], counterpart_rows: list[object]) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        summary_label = QLabel(self._panel_summary_text(rows))
        summary_label.setObjectName("pairPanelSummary")
        summary_label.setVisible(bool(rows))
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        title_row.addWidget(summary_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        browser = QTextBrowser(panel)
        browser.setObjectName("pairDetailsBrowser")
        browser.setOpenExternalLinks(False)
        browser.setFrameShape(QFrame.NoFrame)
        browser.document().setDocumentMargin(0)
        browser.setHtml(self._build_details_html(headers, rows))
        browser.setStyleSheet(
            """
            QTextBrowser#pairDetailsBrowser,
            QTextBrowser#pairExplainBrowser {
                background: #fbfdff;
                border: 1px solid #dbe4f0;
                border-radius: 14px;
                padding: 8px;
            }
            """
        )
        layout.addLayout(title_row)
        layout.addWidget(browser, 1)

        if rows:
            toggle = QToolButton(panel)
            toggle.setCheckable(True)
            toggle.setChecked(False)
            toggle.setArrowType(Qt.RightArrow)
            toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            toggle.setText(self._label("explain_show"))
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setStyleSheet(
                """
                QToolButton {
                    border: none;
                    background: transparent;
                    color: #2563eb;
                    font-size: 12px;
                    font-weight: 600;
                    padding: 2px 0;
                }
                QToolButton:hover {
                    color: #1d4ed8;
                }
                """
            )

            explanation = QTextBrowser(panel)
            explanation.setObjectName("pairExplainBrowser")
            explanation.setOpenExternalLinks(False)
            explanation.setFrameShape(QFrame.NoFrame)
            explanation.document().setDocumentMargin(0)
            explanation.setVisible(False)
            explanation.setMaximumHeight(260)
            explanation.setHtml(self._build_explanation_html(rows, counterpart_rows))

            toggle.toggled.connect(
                lambda checked, button=toggle, widget=explanation: self._toggle_explanation(button, widget, checked)
            )
            layout.addWidget(toggle, alignment=Qt.AlignLeft)
            layout.addWidget(explanation)
        return panel

    def _build_details_html(self, headers: list[str], rows: list[object]) -> str:
        if not rows:
            return self._wrap_html(self._empty_state_html())
        html_sections = [self._group_summary_html(rows)]
        for index, row in enumerate(rows, start=1):
            details_rows = self._single_row_details(headers, row)
            if not details_rows:
                continue
            html_sections.append(self._row_card_html(index, row, details_rows))
        if len(html_sections) == 1:
            return self._wrap_html(self._empty_state_html())
        return self._wrap_html("".join(html_sections))

    def _single_row_details(self, headers: list[str], row) -> list[str]:
        rows: list[str] = []
        for header, value in zip(headers, row.display_values, strict=False):
            text = (value or "").strip()
            if text:
                rows.append(self._table_row(header, text))
        return rows

    def _build_explanation_html(self, current_rows: list[object], counterpart_rows: list[object]) -> str:
        first_row = current_rows[0]
        counterpart_first = counterpart_rows[0] if counterpart_rows else None
        counterpart_row = (
            getattr(first_row, "matched_bank_row", None)
            or getattr(first_row, "matched_system_row", None)
            or getattr(counterpart_first, "excel_row", None)
        )
        current_total = sum(getattr(row, "amount", 0) for row in current_rows)
        counterpart_total = sum(getattr(row, "amount", 0) for row in counterpart_rows)
        rows = [
            self._table_row(self._label("status_label"), tr(self.language, status_bucket_for_row(first_row))),
            self._table_row(self._label("match_type_label"), self._match_type_text(first_row)),
            self._table_row(
                self._label("group_id_label"),
                getattr(first_row, "group_id", None)
                or getattr(first_row, "review_group_id", None)
                or self._label("debug_none"),
            ),
            self._table_row(self._label("group_shape_label"), f"{len(current_rows)}-{len(counterpart_rows)}"),
            self._table_row(self._label("group_total_current"), format_vnd(current_total)),
            self._table_row(self._label("group_total_counterpart"), format_vnd(counterpart_total)),
            self._table_row(self._label("group_diff"), format_vnd(current_total - counterpart_total)),
            self._table_row(self._label("debug_confidence"), self._format_confidence(getattr(first_row, "confidence", 0))),
            self._table_row(self._label("debug_current_row"), self._rows_label(current_rows)),
            self._table_row(
                self._label("debug_counterpart_row"),
                self._rows_label(counterpart_rows) if counterpart_rows else (
                    str(counterpart_row) if counterpart_row else self._label("debug_none")
                ),
            ),
            self._table_row(self._label("debug_date_basis"), self._date_basis_label(getattr(first_row, "match_reason", ""))),
            self._table_row(
                self._label("debug_basis"),
                self._format_match_basis(getattr(first_row, "match_reason", "")),
                is_html=True,
            ),
        ]
        header = (
            "<div class='summary-card'>"
            f"<div class='summary-title'>{escape(self._label('group_summary'))}</div>"
            "<div class='summary-metrics'>"
            f"{self._metric_chip_html(self._label('group_shape_label'), f'{len(current_rows)}-{len(counterpart_rows)}')}"
            f"{self._metric_chip_html(self._label('group_total_current'), format_vnd(current_total))}"
            f"{self._metric_chip_html(self._label('group_total_counterpart'), format_vnd(counterpart_total))}"
            "</div>"
            "</div>"
        )
        return self._wrap_html(header + self._table_html(rows))

    def _table_html(self, rows: list[str]) -> str:
        return (
            "<table width='100%' cellspacing='0' cellpadding='0' class='detail-table'>"
            + "".join(rows)
            + "</table>"
        )

    def _table_row(self, label: str, value: str, *, is_html: bool = False) -> str:
        rendered = value if is_html else escape(value)
        return (
            "<tr>"
            "<td class='detail-label'>"
            f"{escape(label)}"
            "</td>"
            "<td class='detail-value'>"
            f"{rendered}"
            "</td>"
            "</tr>"
        )

    def _toggle_explanation(self, button: QToolButton, widget: QTextBrowser, checked: bool) -> None:
        widget.setVisible(checked)
        button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        button.setText(self._label("explain_hide") if checked else self._label("explain_show"))

    def _rows_label(self, rows: list[object]) -> str:
        if not rows:
            return self._label("debug_none")
        return ", ".join(str(getattr(row, "excel_row", "")) for row in rows if getattr(row, "excel_row", None))

    def _panel_summary_text(self, rows: list[object]) -> str:
        if not rows:
            return ""
        return f"{len(rows)} • {format_vnd(sum(getattr(row, 'amount', 0) for row in rows))}"

    def _group_summary_html(self, rows: list[object]) -> str:
        total = sum(getattr(row, "amount", 0) for row in rows)
        return (
            "<div class='summary-card'>"
            f"<div class='summary-title'>{escape(self._label('group_summary'))}</div>"
            "<div class='summary-metrics'>"
            f"{self._metric_chip_html(self._label('group_rows'), str(len(rows)))}"
            f"{self._metric_chip_html(self._label('group_total'), format_vnd(total))}"
            "</div>"
            "</div>"
        )

    def _row_card_html(self, index: int, row, details_rows: list[str]) -> str:
        return (
            "<section class='entry-card'>"
            "<div class='entry-header'>"
            f"<div class='entry-title'>{escape(self._row_heading(index, row))}</div>"
            f"<div class='entry-amount'>{escape(format_vnd(getattr(row, 'amount', 0)))}</div>"
            "</div>"
            f"{self._table_html(details_rows)}"
            "</section>"
        )

    @staticmethod
    def _metric_chip_html(label: str, value: str) -> str:
        return (
            "<div class='metric-chip'>"
            f"<span class='metric-label'>{escape(label)}</span>"
            f"<span class='metric-value'>{escape(value)}</span>"
            "</div>"
        )

    def _empty_state_html(self) -> str:
        return (
            "<div class='empty-state'>"
            f"<div class='empty-title'>{escape(tr(self.language, 'no_pair'))}</div>"
            "</div>"
        )

    def _wrap_html(self, body: str) -> str:
        return f"""
        <html>
          <head>
            <style>
              body {{
                margin: 0;
                padding: 0;
                background: transparent;
                color: #18212f;
                font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif;
                font-size: 13px;
              }}
              .summary-card {{
                margin-bottom: 12px;
                padding: 12px 14px;
                background: #f8fbff;
                border: 1px solid #dbe4f0;
                border-radius: 14px;
              }}
              .summary-title {{
                font-size: 12px;
                font-weight: 700;
                color: #0f172a;
                margin-bottom: 10px;
              }}
              .summary-metrics {{
                overflow: hidden;
              }}
              .metric-chip {{
                float: left;
                margin: 0 8px 8px 0;
                padding: 8px 10px;
                min-width: 112px;
                background: #ffffff;
                border: 1px solid #dbe4f0;
                border-radius: 12px;
              }}
              .metric-label {{
                display: block;
                font-size: 11px;
                color: #64748b;
                margin-bottom: 3px;
              }}
              .metric-value {{
                display: block;
                font-weight: 700;
                color: #0f172a;
              }}
              .entry-card {{
                margin-bottom: 14px;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                overflow: hidden;
                background: #ffffff;
              }}
              .entry-header {{
                padding: 10px 12px;
                background: linear-gradient(180deg, #f8fbff 0%, #f1f6fd 100%);
                border-bottom: 1px solid #e2e8f0;
              }}
              .entry-title {{
                font-weight: 700;
                color: #0f172a;
                line-height: 1.45;
              }}
              .entry-amount {{
                margin-top: 4px;
                font-size: 12px;
                font-weight: 700;
                color: #2563eb;
              }}
              .detail-table {{
                border-collapse: collapse;
                table-layout: fixed;
              }}
              .detail-label {{
                width: 34%;
                padding: 9px 12px;
                font-weight: 600;
                vertical-align: top;
                background: #f8fafc;
                border-bottom: 1px solid #e5e7eb;
                word-break: break-word;
              }}
              .detail-value {{
                padding: 9px 12px;
                vertical-align: top;
                border-bottom: 1px solid #e5e7eb;
                white-space: pre-wrap;
                word-break: break-word;
              }}
              .detail-table tr:last-child td {{
                border-bottom: none;
              }}
              .empty-state {{
                min-height: 120px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px dashed #dbe4f0;
                border-radius: 14px;
                background: #fbfdff;
              }}
              .empty-title {{
                color: #64748b;
                font-weight: 600;
              }}
              ul {{
                margin: 0;
                padding-left: 18px;
              }}
              li {{
                margin-bottom: 4px;
              }}
            </style>
          </head>
          <body>{body}</body>
        </html>
        """

    def _row_heading(self, index: int, row) -> str:
        return (
            f"{self._label('group_row')} {index} | "
            f"{self._label('debug_current_row')}: {getattr(row, 'excel_row', self._label('debug_none'))} | "
            f"{self._label('group_amount')}: {format_vnd(getattr(row, 'amount', 0))}"
        )

    def _match_type_text(self, row) -> str:
        match_type = getattr(row, "match_type", "none")
        if match_type == "group":
            if getattr(row, "rule_code", "none") == "bank_composite_split":
                return self._label("composite_group")
            return tr(self.language, "matched_group")
        if match_type == "exact":
            return tr(self.language, "matched_exact")
        if getattr(row, "status", "unmatched") == "review" and getattr(row, "review_group_id", None):
            return self._label("review_group")
        return self._label("debug_none")

    def _label(self, key: str) -> str:
        labels = {
            "vi": {
                "status_label": "Trạng thái",
                "match_type_label": "Kiểu khớp",
                "group_id_label": "Mã nhóm",
                "group_shape_label": "Cấu trúc nhóm",
                "group_total_current": "Tổng tiền bên này",
                "group_total_counterpart": "Tổng tiền bên kia",
                "group_diff": "Chênh lệch",
                "group_summary": "Tóm tắt nhóm giao dịch",
                "group_rows": "Số dòng",
                "group_total": "Tổng tiền",
                "group_row": "Dòng",
                "group_amount": "Số tiền",
                "review_group": "Nhóm cần kiểm tra",
                "composite_group": "Nhóm chi + phí/thuế",
                "debug_confidence": "Độ tin cậy",
                "debug_current_row": "Dòng hiện tại",
                "debug_counterpart_row": "Dòng đối ứng",
                "debug_date_basis": "Ngày dùng để dò",
                "debug_basis": "Căn cứ dò",
                "debug_date_transaction": "Ngày giao dịch",
                "debug_date_reference": "Ngày suy ra từ mã nội bộ",
                "debug_none": "Không có",
                "explain_show": "Xem giải thích cách dò",
                "explain_hide": "Ẩn giải thích cách dò",
            },
            "en": {
                "status_label": "Status",
                "match_type_label": "Match type",
                "group_id_label": "Group ID",
                "group_shape_label": "Group shape",
                "group_total_current": "This side total",
                "group_total_counterpart": "Other side total",
                "group_diff": "Difference",
                "group_summary": "Grouped transaction summary",
                "group_rows": "Rows",
                "group_total": "Total amount",
                "group_row": "Row",
                "group_amount": "Amount",
                "review_group": "Review group",
                "composite_group": "Debit + fee/tax group",
                "debug_confidence": "Confidence",
                "debug_current_row": "Current row",
                "debug_counterpart_row": "Matched row",
                "debug_date_basis": "Date used",
                "debug_basis": "Matching basis",
                "debug_date_transaction": "Transaction date",
                "debug_date_reference": "Date derived from internal code",
                "debug_none": "None",
                "explain_show": "Show reconciliation basis",
                "explain_hide": "Hide reconciliation basis",
            },
            "zh": {
                "status_label": "状态",
                "match_type_label": "匹配类型",
                "group_id_label": "组编号",
                "group_shape_label": "组结构",
                "group_total_current": "当前侧合计",
                "group_total_counterpart": "对侧合计",
                "group_diff": "差额",
                "group_summary": "组合交易摘要",
                "group_rows": "行数",
                "group_total": "总金额",
                "group_row": "行",
                "group_amount": "金额",
                "review_group": "待复核分组",
                "composite_group": "支出+手续费/税分组",
                "debug_confidence": "置信度",
                "debug_current_row": "当前行",
                "debug_counterpart_row": "对应行",
                "debug_date_basis": "使用日期",
                "debug_basis": "匹配依据",
                "debug_date_transaction": "交易日期",
                "debug_date_reference": "从内部编码推导的日期",
                "debug_none": "无",
                "explain_show": "查看对账依据",
                "explain_hide": "隐藏对账依据",
            },
        }
        return labels.get(self.language, labels["vi"]).get(key, key)

    def _format_confidence(self, confidence: int) -> str:
        if confidence <= 0:
            return self._label("debug_none")
        return f"{confidence}/100"

    def _format_match_basis(self, reason: str) -> str:
        if not reason:
            return self._label("debug_none")
        reasons = [segment.strip() for segment in reason.splitlines() if segment.strip()]
        if not reasons:
            return escape(self._label("debug_none"))
        return (
            "<ul style='margin:0;padding-left:18px'>"
            + "".join(f"<li style='margin:0 0 4px 0'>{escape(item)}</li>" for item in reasons)
            + "</ul>"
        )

    def _date_basis_label(self, reason: str) -> str:
        if "Ngày theo mã nội bộ" in reason:
            return self._label("debug_date_reference")
        if "Ngày giao dịch" in reason:
            return self._label("debug_date_transaction")
        return self._label("debug_none")


class HistoryDialog(QDialog):
    def __init__(self, language: str, records: list[dict], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        logo_path = logo_image_path()
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        self.language = language
        self.setWindowTitle(tr(language, "recent_history"))
        self.resize(920, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(tr(language, "recent_history"))
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        self.table = QTableWidget(0, 4, self)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False)
        self.table.setHorizontalHeaderLabels(
            [
                tr(language, "history_time"),
                tr(language, "history_system"),
                tr(language, "history_bank"),
                tr(language, "history_result"),
            ]
        )
        layout.addWidget(self.table)
        self._fill_rows(records)

    def _fill_rows(self, records: list[dict]) -> None:
        self.table.setRowCount(len(records))
        for row_index, record in enumerate(records):
            scanned_at = str(record.get("scanned_at", "")).replace("T", " ")
            summary = self._history_summary_text(record)
            values = [
                scanned_at,
                Path(str(record.get("system_file", ""))).name,
                Path(str(record.get("bank_file", ""))).name,
                summary,
            ]
            for column_index, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(int(Qt.AlignLeft | Qt.AlignVCenter))
                self.table.setItem(row_index, column_index, item)
        self.table.setWordWrap(True)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 170)
        self.table.setColumnWidth(2, 260)
        self.table.horizontalHeader().setStretchLastSection(True)

    def _history_summary_text(self, record: dict[str, object]) -> str:
        if self.language == "en":
            system_label, bank_label = "System", "Statement"
            matched_label, review_label, unmatched_label = "matched", "review", "unmatched"
        elif self.language == "zh":
            system_label, bank_label = "系统", "流水"
            matched_label, review_label, unmatched_label = "已匹配", "待复核", "未匹配"
        else:
            system_label, bank_label = "Hệ thống", "Sao kê"
            matched_label, review_label, unmatched_label = "khớp", "cần kiểm tra", "không khớp"
        return (
            f"{system_label}: {record.get('matched_system', 0)} {matched_label}, "
            f"{record.get('review_system', 0)} {review_label}, "
            f"{record.get('unmatched_system', 0)} {unmatched_label}\n"
            f"{bank_label}: {record.get('matched_bank', 0)} {matched_label}, "
            f"{record.get('review_bank', 0)} {review_label}, "
            f"{record.get('unmatched_bank', 0)} {unmatched_label}"
        )
