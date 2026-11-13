import unittest
import pandas as pd

from modules.analyzer.file_loader import detect_catalog_columns, detect_auxiliary_columns
from modules.analyzer.report_generator import generate_analysis_report, export_analysis_report_excel
from modules.analyzer.sp_api_client import _select_best_catalog_item


class TestReportGenerator(unittest.TestCase):
    def test_detect_catalog_and_auxiliary_columns_moira_format(self):
        df = pd.DataFrame({
            "ProductId": ["1173096", "1172743"],
            "Manufacture Name": ["Moira", "Moira"],
            "Lead time": ["3 days", "3 days"],
            "UPC": ["840222307835", "840222300294"],
            "Title": ["Set & Correct Powder", "Diamond Daze Liquid Shadow (010 Stardom)"],
            "Case size (price is per unit, NOT per case size)": ["48", "72"],
            "Wholesale Price (over $500 purchase). First order only required min $350 & at least 3 different items": ["7.50", "3.23"],
            "Amazon Link for Reference - This is for your convenience ONLY": [
                "https://www.amazon.com/dp/B0CFZ6M6P4",
                "https://www.amazon.com/dp/B09RQ997NR",
            ],
        })
        upc_idx, cost_idx = detect_catalog_columns(df)
        self.assertEqual(df.columns[upc_idx], "UPC")
        self.assertIn("Wholesale Price", df.columns[cost_idx])

        aux = detect_auxiliary_columns(df, df.columns[upc_idx], df.columns[cost_idx])
        self.assertEqual(aux["title_col"], "Title")
        self.assertEqual(aux["sku_col"], "ProductId")
        self.assertIn("Amazon Link", aux["ref_link_col"])

    def test_select_best_catalog_item_prefers_matching_shade_and_ref_asin(self):
        items = [
            {
                "asin": "B0CL5LQD5W",
                "summaries": [{"itemName": "Moira Lip Appeal Waterproof Liner (011, Dolly)", "packageQuantity": 1}],
                "salesRanks": [{"displayGroupRanks": [{"rank": 15000}]}],
            },
            {
                "asin": "B0CL5KNVV4",
                "summaries": [{"itemName": "Moira Lip Appeal Waterproof Liner (013, Lala)", "packageQuantity": 1}],
                "salesRanks": [{"displayGroupRanks": [{"rank": 45000}]}],
            },
        ]
        # Should pick 013 Lala over lower-BSR 011 Dolly when supplier title has 013 Lala
        chosen = _select_best_catalog_item(items, user_title="Lip Appeal Waterproof Liner (013 Lala)")
        self.assertEqual(chosen["asin"], "B0CL5KNVV4")

    def test_generate_analysis_report_reconciles_all_statuses(self):
        supplier_df = pd.DataFrame({
            "ProductId": ["SKU1", "SKU2", "SKU3", "SKU4", "SKU5"],
            "UPC": ["840222307835", "840222313621", "840222399999", "840222388888", "840222377777"],
            "Title": ["Item 1 Profitable", "Item 2 Negative ROI", "Item 3 Not Found", "Item 4 Unlisted", "Item 5 Missing"],
            "Wholesale Price": ["7.50", "1.88", "2.50", "3.00", "4.00"],
        })
        results_df = pd.DataFrame([
            {
                "ASIN": "B0CFZ6M6P4",
                "Product ID": "840222307835",
                "Title": "Item 1 Profitable",
                "Cost": 7.50,
                "Sell Price": 20.00,
                "Profit ($)": 3.73,
                "ROI (%)": 0.497,
                "Sales Rank": 12000,
                "Category": "Beauty & Personal Care",
                "Selling Restriction": "approval required",
            },
            {
                "ASIN": "B0G1SSR7WB",
                "Product ID": "840222313621",
                "Title": "Item 2 Negative ROI",
                "Cost": 1.88,
                "Sell Price": 5.00,
                "Profit ($)": -0.48,
                "ROI (%)": -0.255,
                "Sales Rank": 45000,
                "Category": "Beauty & Personal Care",
                "Selling Restriction": "approval required",
            },
            {
                "ASIN": "NOT_FOUND",
                "Product ID": "840222399999",
                "Title": "Item 3 Not Found",
                "Cost": 2.50,
                "Sell Price": None,
                "Profit ($)": None,
                "ROI (%)": None,
                "Sales Rank": None,
                "Category": "Unknown",
                "Selling Restriction": "not eligible",
            },
            {
                "ASIN": "B0UNLISTED1",
                "Product ID": "840222388888",
                "Title": "Item 4 Unlisted",
                "Cost": 3.00,
                "Sell Price": None,
                "Profit ($)": None,
                "ROI (%)": None,
                "Sales Rank": 95000,
                "Category": "Beauty & Personal Care",
                "Selling Restriction": "approval required",
            },
        ])
        # Simulate UI filter excluding negative ROI (filtered_df only has row 0)
        filtered_df = results_df.iloc[[0]].copy()

        report = generate_analysis_report(
            results_df=results_df,
            supplier_df=supplier_df,
            upc_col="UPC",
            cost_col="Wholesale Price",
            filtered_df=filtered_df,
            active_filters={"min_roi": 0},
        )
        summary = report["summary"]
        self.assertEqual(summary["original_rows"], 5)
        self.assertEqual(summary["analyzed_rows"], 4)
        self.assertEqual(summary["profitable_rows"], 1)
        self.assertEqual(summary["negative_roi_rows"], 1)
        self.assertEqual(summary["not_found_rows"], 1)
        self.assertEqual(summary["no_price_rows"], 1)
        self.assertEqual(summary["missing_from_run_rows"], 1)
        self.assertEqual(summary["excluded_by_filter_rows"], 2)

        xlsx_bytes = export_analysis_report_excel(report)
        self.assertTrue(len(xlsx_bytes) > 1000)


if __name__ == "__main__":
    unittest.main()
