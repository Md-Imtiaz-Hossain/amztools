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
        self.assertEqual(r["analyzing_software_name"], "InternalAMZ")

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

    def test_build_insert_sql(self):
        service = D1UploaderService(client=None)
        sample_record = {
            "asin": "B0BDHWDR12",
            "wholesaler_company_name": "Acme Supplies",
            "title": "AirPods Pro",
            "cost": 175.0,
            "sell_price": 249.0,
        }
        sql = service.build_insert_sql(sample_record)
        self.assertIn("INSERT INTO wholesale_products", sql)
        self.assertNotIn("ON CONFLICT", sql)

    def test_duplicate_asins_integrity_tracking(self):
        records = [
            {"asin": "B001", "wholesaler_company_name": "Acme", "product_id": "UPC1"},
            {"asin": "B001", "wholesaler_company_name": "Acme", "product_id": "UPC2"}, # Dup ASIN
            {"asin": "B002", "wholesaler_company_name": "Acme", "product_id": "UPC3"},
            {"asin": "B003", "wholesaler_company_name": "Acme", "product_id": "UPC4"},
            {"asin": "B003", "wholesaler_company_name": "Acme", "product_id": "UPC5"}, # Dup ASIN
            {"asin": "", "wholesaler_company_name": "Acme", "product_id": "UPC6"},     # Missing ASIN
        ]
        integrity = validate_record_integrity(records)
        self.assertEqual(integrity["total_records"], 6)
        self.assertEqual(integrity["valid_count"], 5)
        self.assertEqual(integrity["missing_asin_count"], 1)
        self.assertEqual(integrity["unique_asin_count"], 3)
        self.assertEqual(integrity["duplicate_asin_count"], 2)


    def test_pre_parsed_passthrough(self):
        records = [
            {"asin": f"B0000000{i:02d}", "wholesaler_company_name": "Test Co", "cost": 10.0}
            for i in range(10)
        ]
        res = parse_and_validate_analysis_file(records)
        self.assertIs(res, records)

    def test_slot_based_upload_and_notifications(self):
        # Generate 1,250 records
        mock_records = [
            {
                "asin": f"B{i:09d}",
                "product_id": f"UPC{i:010d}",
                "title": f"Product #{i}",
                "cost": 15.0,
                "sell_price": 25.0,
                "profit": 5.0,
                "wholesaler_company_name": "Mega Wholesale",
                "analyzing_software_name": "InternalAMZ",
            }
            for i in range(1, 1251)
        ]

        received_slots = []
        def slot_cb(slot_info):
            received_slots.append(slot_info)

        service = D1UploaderService(client=None)
        report = service.upload_dataset(
            dataset_source=mock_records,
            slot_callback=slot_cb,
            slot_size=500,
            batch_size=50,
            auto_init_schema=False,
        )

        self.assertTrue(report["success"])
        self.assertEqual(report["total_processed"], 1250)
        self.assertEqual(report["uploaded_count"], 1250)
        self.assertEqual(report["total_slots"], 3)
        self.assertEqual(len(received_slots), 3)

        # Slot 1: Rows 1 to 500
        s1 = received_slots[0]
        self.assertEqual(s1["slot_number"], 1)
        self.assertEqual(s1["start_row"], 1)
        self.assertEqual(s1["end_row"], 500)
        self.assertEqual(s1["slot_uploaded"], 500)
        self.assertEqual(s1["cumulative_uploaded"], 500)
        self.assertIn("Excel rows 1 to 500", s1["message"])

        # Slot 2: Rows 501 to 1000
        s2 = received_slots[1]
        self.assertEqual(s2["slot_number"], 2)
        self.assertEqual(s2["start_row"], 501)
        self.assertEqual(s2["end_row"], 1000)
        self.assertEqual(s2["slot_uploaded"], 500)
        self.assertEqual(s2["cumulative_uploaded"], 1000)
        self.assertIn("Excel rows 501 to 1000", s2["message"])

        # Slot 3: Rows 1001 to 1250 (remaining 250)
        s3 = received_slots[2]
        self.assertEqual(s3["slot_number"], 3)
        self.assertEqual(s3["start_row"], 1001)
        self.assertEqual(s3["end_row"], 1250)
        self.assertEqual(s3["slot_uploaded"], 250)
        self.assertEqual(s3["cumulative_uploaded"], 1250)
        self.assertIn("Excel rows 1001 to 1250", s3["message"])


if __name__ == "__main__":
    unittest.main()

