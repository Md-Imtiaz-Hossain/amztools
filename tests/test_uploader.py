"""
Tests for Module 3: Upload Pipeline & File Parser.
"""

import unittest
import pandas as pd
from modules.uploader.file_parser import (
    parse_and_validate_analysis_file,
    validate_record_integrity,
)
from modules.uploader.uploader_service import D1UploaderService


class TestUploaderPipeline(unittest.TestCase):
    def test_parse_and_validate_dataframe(self):
        sample_df = pd.DataFrame([
            {
                "ASIN": "B0BDHWDR12",
                "Product ID": "019425205698",
                "Title": "Apple AirPods Pro",
                "Cost": "$175.00",
                "Sell Price": "$249.00",
                "Profit ($)": "$32.50",
                "Wholesaller Company Name": "Acme Supplies",
            }
        ])

        records = parse_and_validate_analysis_file(sample_df)
        self.assertEqual(len(records), 1)
        r = records[0]
        self.assertEqual(r["asin"], "B0BDHWDR12")
        self.assertEqual(r["product_id"], "019425205698")
        self.assertEqual(r["cost"], 175.00)
        self.assertEqual(r["sell_price"], 249.00)
        self.assertEqual(r["profit"], 32.50)
        self.assertEqual(r["wholesaler_company_name"], "Acme Supplies")

    def test_validate_record_integrity(self):
        records = [
            {"asin": "B0BDHWDR12", "wholesaler_company_name": "Acme Supplies"},
            {"asin": "", "wholesaler_company_name": "Acme Supplies"},  # Missing ASIN
        ]
        summary = validate_record_integrity(records)
        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["valid_count"], 1)
        self.assertEqual(summary["missing_asin_count"], 1)
        self.assertTrue(summary["is_ready_for_upload"])

    def test_build_upsert_sql(self):
        service = D1UploaderService(client=None)
        sample_record = {
            "asin": "B0BDHWDR12",
            "wholesaler_company_name": "Acme Supplies",
            "title": "AirPods Pro",
            "cost": 175.0,
            "sell_price": 249.0,
        }
        sql = service.build_upsert_sql(sample_record)
        self.assertIn("INSERT INTO wholesale_products", sql)
        self.assertIn("ON CONFLICT(asin, wholesaler_company_name) DO UPDATE SET", sql)


if __name__ == "__main__":
    unittest.main()
