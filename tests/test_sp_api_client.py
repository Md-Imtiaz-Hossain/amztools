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

    def test_quick_search_by_asin(self):
        """Quick Search with only ASIN and Wholesale Price."""
        item = fetch_amazon_item_data(
            asin="B0BDHWDR12",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=120.0,
        )
        row = build_full_target_row(
            item_data=item,
            cost=120.0,
            wholesaler_company_name="Apex Global Distributors",
        )
        self.assertEqual(row["ASIN"], "B0BDHWDR12")
        self.assertEqual(row["Cost"], 120.0)
        self.assertGreater(row["Sell Price"], 0)
        self.assertEqual(len(row), len(TARGET_COLUMNS))
        for col in TARGET_COLUMNS:
            self.assertIn(col, row)

    def test_quick_search_by_upc(self):
        """Quick Search with only UPC and Wholesale Price."""
        item = fetch_amazon_item_data(
            upc="019425205698",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=145.0,
        )
        row = build_full_target_row(
            item_data=item,
            cost=145.0,
            wholesaler_company_name="Direct Wholesaler",
        )
        self.assertEqual(row["Product ID"], "019425205698")
        self.assertEqual(row["Cost"], 145.0)
        self.assertEqual(len(row), len(TARGET_COLUMNS))
        for col in TARGET_COLUMNS:
            self.assertIn(col, row)

    def test_quick_search_by_title(self):
        """Quick Search with only Title and Wholesale Price."""
        item = fetch_amazon_item_data(
            title="Premium Vitamin C Serum 2 fl oz",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=9.75,
        )
        row = build_full_target_row(
            item_data=item,
            cost=9.75,
            wholesaler_company_name="Nutra Wholesale Corp",
        )
        self.assertTrue(row["ASIN"].startswith("B0"))
        self.assertEqual(row["Title"], "Premium Vitamin C Serum 2 fl oz")
        self.assertEqual(row["Cost"], 9.75)
        self.assertEqual(len(row), len(TARGET_COLUMNS))
        for col in TARGET_COLUMNS:
            self.assertIn(col, row)

    def test_quick_search_multi_input(self):
        """Quick Search with UPC, ASIN, Title, and Wholesale Price all provided."""
        item = fetch_amazon_item_data(
            asin="B01N1S89M0",
            upc="794437466810",
            title="SheaMoisture Daily Hydration Conditioner 13 oz",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=5.50,
        )
        row = build_full_target_row(
            item_data=item,
            cost=5.50,
            wholesaler_company_name="Beauty Supply Warehouse",
        )
        self.assertEqual(row["ASIN"], "B01N1S89M0")
        self.assertEqual(row["Product ID"], "794437466810")
        self.assertEqual(row["Title"], "SheaMoisture Daily Hydration Conditioner 13 oz")
        self.assertEqual(row["Cost"], 5.50)
        self.assertEqual(row["Wholesaller Company Name"], "Beauty Supply Warehouse")
        self.assertEqual(len(row), len(TARGET_COLUMNS))

    def test_quick_search_matches_bulk_schema(self):
        """Verify that Quick Search DataFrame output exactly matches Bulk Search DataFrame schema."""
        import pandas as pd
        # Bulk search row
        bulk_item = fetch_amazon_item_data(
            raw_identifier="019425205698",
            credentials={},
            marketplace="US",
            is_demo=True,
            cost=175.0,
        )
        bulk_row = build_full_target_row(item_data=bulk_item, cost=175.0, wholesaler_company_name="Test")
        bulk_df = pd.DataFrame([bulk_row])

        # Quick search row
        quick_item = fetch_amazon_item_data(
            upc="794437466810",
            asin="B01N1S89M0",
            title="Custom Title",
            cost=12.0,
            credentials={},
            marketplace="US",
            is_demo=True,
        )
        quick_row = build_full_target_row(item_data=quick_item, cost=12.0, wholesaler_company_name="Test")
        quick_df = pd.DataFrame([quick_row])

        # Verify exact column list and order match
        self.assertEqual(list(quick_df.columns), list(bulk_df.columns))
        self.assertEqual(list(quick_df.columns), TARGET_COLUMNS)


if __name__ == "__main__":
    unittest.main()

