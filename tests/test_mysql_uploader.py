"""
Tests for Module 5: Upload Data to MySQL Remote Database.
"""

import unittest
import pandas as pd
from modules.mysql_uploader.config import MySQLDatabaseConfig
from modules.mysql_uploader.uploader_service import MySQLUploaderService


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


if __name__ == "__main__":
    unittest.main()
