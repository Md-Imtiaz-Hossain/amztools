"""
Tests for Module 2: Supplier Catalog File Ingestion.
"""

import io
import unittest
import pandas as pd
from modules.analyzer.file_loader import load_supplier_file


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


if __name__ == "__main__":
    unittest.main()
