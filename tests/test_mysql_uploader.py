"""
Tests for Module 5: Upload Data to MySQL Remote Database.
"""

import io
import unittest
import pandas as pd
from modules.mysql_uploader.config import MySQLDatabaseConfig
from modules.mysql_uploader.uploader_service import MySQLUploaderService
from modules.mysql_crud.crud_service import MySQLCrudService
from modules.crud.models import ProductFilterCriteria
from modules.uploader.file_parser import parse_and_validate_analysis_file


class TestMySQLUploaderPipeline(unittest.TestCase):
    def test_mysql_database_config_validation(self):
        cfg_empty = MySQLDatabaseConfig()
        self.assertFalse(cfg_empty.is_valid())

        cfg_valid = MySQLDatabaseConfig(
            host="srv1570.hstgr.io",
            port=3306,
            database="u742113797_re_D2AKZzTX",
            user="u742113797_re_D2AKZzTX",
            password="test_password",
        )
        self.assertTrue(cfg_valid.is_valid())

    def test_build_mysql_insert_and_upsert_sql(self):
        service = MySQLUploaderService(client=None)
        sample = {
            "asin": "B0BDHWDR12",
            "wholesaler_company_name": "Acme Supplies",
            "cost": 175.0,
            "sell_price": 249.0,
            "profit": 32.5,
        }

        insert_sql = service.build_insert_sql(sample)
        self.assertIn("INSERT INTO wholesale_products", insert_sql)
        self.assertIn("VALUES (%s, %s, %s, %s, %s)", insert_sql)
        self.assertNotIn("ON DUPLICATE KEY UPDATE", insert_sql)

        upsert_sql = service.build_upsert_sql(sample)
        self.assertIn("INSERT INTO wholesale_products", upsert_sql)
        self.assertIn("VALUES (%s, %s, %s, %s, %s)", upsert_sql)
        self.assertIn("ON DUPLICATE KEY UPDATE", upsert_sql)
        self.assertIn("cost = VALUES(cost)", upsert_sql)
        self.assertIn("updated_at = CURRENT_TIMESTAMP", upsert_sql)

    def test_mysql_slot_based_upload_and_notifications(self):
        df = pd.DataFrame(
            [
                {
                    "ASIN": f"B00000{i:04d}",
                    "Wholesaller Company Name": "Hostinger Supplier LLC",
                    "Cost": "$10.00",
                    "Sell Price": "$25.00",
                    "Profit ($)": "$5.00",
                }
                for i in range(60)
            ]
        )

        executed_batches = []

        class MockMySQLClient:
            def init_database_schema(self, force=False):
                return True, "MySQL Schema OK"

            def clear_table(self, wholesaler_company_name=None):
                return True, "Cleared"

            def execute_batch(self, batch_payload):
                executed_batches.append(batch_payload)
                return {"success": True, "total_changes": len(batch_payload)}

        service = MySQLUploaderService(client=MockMySQLClient())
        slot_notifications = []

        report = service.upload_dataset(
            dataset_source=df,
            slot_callback=lambda info: slot_notifications.append(info),
            slot_size=25,
            batch_size=15,
            upload_mode="insert",
        )

        self.assertTrue(report["success"])
        self.assertEqual(report["uploaded_count"], 60)
        self.assertEqual(report["total_slots"], 3)
        self.assertEqual(report["completed_slots"], 3)
        self.assertEqual(len(slot_notifications), 3)
        self.assertEqual(slot_notifications[0]["start_row"], 1)
        self.assertEqual(slot_notifications[0]["end_row"], 25)
        self.assertEqual(slot_notifications[1]["start_row"], 26)
        self.assertEqual(slot_notifications[1]["end_row"], 50)
        self.assertEqual(slot_notifications[2]["start_row"], 51)
        self.assertEqual(slot_notifications[2]["end_row"], 60)
        self.assertGreater(len(executed_batches), 0)

    def test_mysql_crud_service_operations(self):
        executed_queries = []

        class MockMySQLClient:
            def execute_query(self, sql, params=None):
                executed_queries.append((sql, params))
                if "COUNT(*) AS total_products" in sql:
                    return {
                        "success": True,
                        "results": [
                            {
                                "total_products": 42,
                                "total_wholesalers": 3,
                                "profitable_leads": 30,
                                "avg_roi": 0.45,
                                "top_profit": 18.75,
                            }
                        ],
                    }
                if "COUNT(*)" in sql:
                    return {"success": True, "results": [{"total_count": 42}]}
                return {
                    "success": True,
                    "results": [
                        {
                            "id": 1,
                            "asin": "B0CSF57LJ9",
                            "wholesaler_company_name": "Medcare LLC",
                            "cost": 3.23,
                            "sell_price": 14.99,
                            "profit": 4.50,
                            "roi_pct": 1.39,
                        }
                    ],
                }

        svc = MySQLCrudService(MockMySQLClient())

        # 1. Fetch products with ASIN filter (uses %s placeholders and skips COUNT(*) on page 1 when < limit)
        criteria = ProductFilterCriteria(keyword="B0CSF57LJ9", page=1, page_size=25)
        res = svc.fetch_products(criteria)
        self.assertEqual(res.total_count, 1)
        self.assertEqual(len(executed_queries), 1)
        self.assertIn("(asin = %s OR parent_asin = %s)", executed_queries[0][0])

        # 2. Update product recalculates financials and uses %s placeholders
        executed_queries.clear()
        ok, msg = svc.update_product(
            asin="B0CSF57LJ9",
            wholesaler="Medcare LLC",
            updates={"cost": 4.00, "sell_price": 18.00},
            current_product=res.items[0],
        )
        self.assertTrue(ok)
        self.assertEqual(len(executed_queries), 1)
        self.assertIn("WHERE asin = %s AND wholesaler_company_name = %s", executed_queries[0][0])

        # 3. Create & Delete product
        executed_queries.clear()
        c_ok, _ = svc.create_product(
            {
                "asin": "B0BDHWDR12",
                "wholesaler_company_name": "Medcare LLC",
                "cost": 10.0,
                "sell_price": 25.0,
            }
        )
        self.assertTrue(c_ok)
        d_ok, _ = svc.delete_product("B0BDHWDR12", "Medcare LLC")
        self.assertTrue(d_ok)

        # 4. Statistics
        stats = svc.get_database_statistics()
        self.assertEqual(stats["total_products"], 42)
        self.assertEqual(stats["avg_roi_pct"], 45.0)

    def test_csv_with_unescaped_quotes_and_missing_asins_uploads_100_percent_rows(self):
        """
        Verify that CSV files with unescaped inch quotes (e.g. 12" Monitor, "Unclosed)
        or missing/NOT_FOUND ASINs do NOT lose or filter out any rows in Module 5.
        """
        csv_lines = ["ASIN,Product ID,Title,Cost,Sell Price,Wholesaller Company Name"]
        # Row 1: normal
        csv_lines.append('B000000001,012345678901,"Standard Item, Pack of 2",3.23,12.99,Medcare LLC')
        # Row 2: unescaped quote in title (would normally swallow subsequent rows until next quote!)
        csv_lines.append('B000000002,012345678902,Heavy Duty 12" Steel Pipe Wrench,8.50,24.99,Medcare LLC')
        # Rows 3..9: normal rows between two stray quotes
        for i in range(3, 10):
            csv_lines.append(f"B00000000{i},01234567890{i},Normal Product {i},4.00,15.00,Medcare LLC")
        # Row 10: another unescaped quote in title
        csv_lines.append('B000000010,012345678910,24" LED Monitor Stand,12.00,35.00,Medcare LLC')
        # Row 11: missing ASIN
        csv_lines.append(",012345678911,No ASIN Item,2.50,9.99,Medcare LLC")
        # Row 12: NOT_FOUND ASIN
        csv_lines.append("NOT_FOUND,012345678912,Unlisted Item,1.99,7.99,Medcare LLC")

        raw_csv = "\n".join(csv_lines).encode("utf-8")
        buf = io.BytesIO(raw_csv)
        buf.name = "external_catalog.csv"

        records = parse_and_validate_analysis_file(buf)
        self.assertEqual(len(records), 12, "Must read all 12 rows without swallowing rows between stray quotes")

        uploaded_batches = []

        class MockMySQLClient:
            def init_database_schema(self, force=False):
                return True, "OK"

            def ensure_columns_exist(self, cols):
                pass

            def execute_batch(self, batch_payload):
                uploaded_batches.extend(batch_payload)
                return {"success": True, "total_changes": len(batch_payload)}

        service = MySQLUploaderService(client=MockMySQLClient())
        report = service.upload_dataset(dataset_source=records, slot_size=50, batch_size=50)
        self.assertTrue(report["success"])
        self.assertEqual(report["total_processed"], 12)
        self.assertEqual(report["uploaded_count"], 12, "All 12 rows (including missing/NOT_FOUND ASIN) must be uploaded to MySQL")
        self.assertEqual(len(uploaded_batches), 12)


if __name__ == "__main__":
    unittest.main()
