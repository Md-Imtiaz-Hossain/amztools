"""
Tests for Module 2: Target 52-Column Excel Exporter.
"""

import io
import unittest
import pandas as pd
import openpyxl
from modules.analyzer.excel_exporter import export_to_target_excel
from modules.analyzer.sp_api_client import TARGET_COLUMNS


class TestExcelExporter(unittest.TestCase):
    def test_export_to_target_excel(self):
        # Create minimal DataFrame with TARGET_COLUMNS
        row = {col: "Sample" for col in TARGET_COLUMNS}
        row["Cost"] = 15.00
        row["Sell Price"] = 29.99
        row["Profit ($)"] = 5.50
        row["ROI (%)"] = 0.3667
        row["Margin (%)"] = 0.1834
        row["Sales Rank"] = 12000

        df = pd.DataFrame([row])
        excel_bytes = export_to_target_excel(df)

        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)

        # Parse with openpyxl to verify worksheet structure
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        ws = wb.active
        self.assertIsNotNone(ws)
        # Header count must match
        header_vals = [cell.value for cell in ws[1]]
        self.assertEqual(len(header_vals), len(TARGET_COLUMNS))
        self.assertEqual(header_vals[0], TARGET_COLUMNS[0])


if __name__ == "__main__":
    unittest.main()
