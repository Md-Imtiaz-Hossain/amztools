"""
Tests for Module 2: SP-API Client & Demo Simulation Engine.
"""

import unittest
from modules.analyzer.sp_api_client import (
    TARGET_COLUMNS,
    clean_identifier,
    fetch_amazon_item_data,
    build_full_target_row,
)


class TestSPApiClient(unittest.TestCase):
    def test_clean_identifier(self):
        # UPC with 12 digits
        cid, id_type = clean_identifier("019425205698")
        self.assertEqual(cid, "019425205698")
        self.assertEqual(id_type, "UPC")

        # EAN with 13 digits
        cid, id_type = clean_identifier("8809625241285")
        self.assertEqual(cid, "8809625241285")
        self.assertEqual(id_type, "EAN")

        # ASIN
        cid, id_type = clean_identifier("B0BDHWDR12")
        self.assertEqual(cid, "B0BDHWDR12")
        self.assertEqual(id_type, "ASIN")

        # Empty
        cid, id_type = clean_identifier("")
        self.assertEqual(cid, "")
        self.assertEqual(id_type, "UPC")

    def test_demo_mode_known_item(self):
        item = fetch_amazon_item_data(
            raw_identifier="019425205698",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=175.0,
        )
        self.assertEqual(item["asin"], "B0BDHWDR12")
        self.assertEqual(item["brand"], "Apple")
        self.assertEqual(item["category"], "Electronics")
        self.assertGreater(item["total_offers"], 0)

    def test_demo_mode_unlisted_item_simulation(self):
        # Any arbitrary UPC should deterministically produce valid simulation fields
        item = fetch_amazon_item_data(
            raw_identifier="999888777666",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=25.0,
        )
        self.assertTrue(item["asin"].startswith("B0"))
        self.assertIn(item["category"], [
            "Arts, Crafts & Sewing", "Beauty & Personal Care", "Electronics",
            "Cell Phones & Accessories", "Video Games", "Home & Kitchen"
        ])

    def test_build_full_target_row(self):
        item = fetch_amazon_item_data(
            raw_identifier="019425205698",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=175.0,
        )
        row = build_full_target_row(
            item_data=item,
            cost=175.0,
            wholesaler_company_name="Acme Wholesale",
        )
        self.assertEqual(row["ASIN"], "B0BDHWDR12")
        self.assertEqual(row["Wholesaller Company Name"], "Acme Wholesale")
        # Ensure all required target columns are present
        for col in TARGET_COLUMNS:
            self.assertIn(col, row)


if __name__ == "__main__":
    unittest.main()
