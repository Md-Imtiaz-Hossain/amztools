"""
Tests for Module 2: Supplier Catalog File Ingestion.
"""

import io
import unittest
import pandas as pd
from modules.analyzer.file_loader import load_supplier_file, detect_catalog_columns


class TestFileLoader(unittest.TestCase):
    def test_load_csv_preserves_leading_zeros(self):
        csv_data = "UPC,Product Name,Cost\n012345678901,Test Widget,14.50\n009876543210,Test Gadget,22.00\n"
        buffer = io.StringIO(csv_data)
        buffer.name = "catalog.csv"

        df = load_supplier_file(buffer)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 2)
        # Leading zeroes must be preserved as strings
        self.assertEqual(df["UPC"].iloc[0], "012345678901")
        self.assertEqual(df["UPC"].iloc[1], "009876543210")

    def test_load_supplier_file_none(self):
        self.assertIsNone(load_supplier_file(None))

    def test_detect_catalog_columns_ignores_case_pack_and_case_price(self):
        """Ensure detect_catalog_columns picks Unit Price ($2.33/$3.23) over Case Pack/Case Price (144)."""
        df = pd.DataFrame({
            "Item #": ["MC-101", "MC-102"],
            "UPC Code": ["840222309280", "840222309297"],
            "Brand": ["Moira", "Moira"],
            "Case Pack": ["144", "144"],
            "Case Price": ["$335.52", "$465.12"],
            "Wholesale Price": ["$2.33", "$3.23"],
            "MSRP": ["$8.00", "$9.00"],
        })
        id_idx, cost_idx = detect_catalog_columns(df)
        self.assertEqual(df.columns[id_idx], "UPC Code")
        self.assertEqual(df.columns[cost_idx], "Wholesale Price")

    def test_promote_header_row_when_banner_rows_present(self):
        """Ensure supplier files with title/banner rows above the real header are auto-promoted."""
        csv_data = (
            "Medcare LLC Wholesale Catalog,,,\n"
            "Updated: November 2026,,,\n"
            "UPC,Brand,Title,Unit Cost\n"
            "840222309280,Moira,Chroma Light Shadow,3.23\n"
        )
        buffer = io.StringIO(csv_data)
        buffer.name = "medcare_catalog.csv"
        df = load_supplier_file(buffer)
        self.assertIn("UPC", df.columns)
        self.assertIn("Unit Cost", df.columns)
        self.assertEqual(df["UPC"].iloc[0], "840222309280")
        self.assertEqual(df["Unit Cost"].iloc[0], "3.23")


if __name__ == "__main__":
    unittest.main()
