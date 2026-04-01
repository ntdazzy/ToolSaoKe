from __future__ import annotations

from pathlib import Path
import unittest

from app.services.excel_loader import detect_excel_file_kind


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_EXPECTATIONS = {
    "202512": {
        "hệ thống 2025.12.xls": "system",
        "中原TRUNG NGUYEN TCB VND 0012 T12.2025.xlsx": "bank",
    },
    "202601": {
        "hệ thống tháng 1.xls": "system",
        "中原 TRUNG NGUYEN TCB VND 0012 T01.2026.xlsx": "bank",
    },
    "202602": {
        "hệ thống tháng 2.xls": "system",
        "中原TRUNG NGUYEN TCB VND 0012 02.2026.xlsx": "bank",
    },
    "202603": {
        "Hệ Thống.xls": "system",
        "TRANSACTION_HISTORY__1774658366122.xlsx": "bank",
    },
    "202603.1": {
        "hệ thống 0012.xls": "system",
        "TRANSACTION_HISTORY__1774918289898.xlsx": "bank",
    },
}


class ExcelFileKindTests(unittest.TestCase):
    def test_detect_excel_file_kind_accepts_sample_files(self) -> None:
        base_dir = REPO_ROOT / "file"
        for folder_name, expectations in SAMPLE_EXPECTATIONS.items():
            folder = base_dir / folder_name
            self.assertTrue(folder.exists(), f"Missing sample folder: {folder}")
            for file_name, expected_kind in expectations.items():
                path = folder / file_name
                self.assertTrue(path.exists(), f"Missing sample file: {path}")
                kind, reason = detect_excel_file_kind(str(path))
                self.assertEqual(
                    kind,
                    expected_kind,
                    f"Unexpected kind for {path}: kind={kind}, reason={reason}",
                )
                self.assertIsNone(reason, f"Unexpected reason for {path}: {reason}")


if __name__ == "__main__":
    unittest.main()
