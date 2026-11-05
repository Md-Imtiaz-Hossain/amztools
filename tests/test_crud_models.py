"""
Tests for Module 1 Router & Module 4 CRUD Models.
"""

import unittest
from modules.entrypoint.router import AppRouter, ModuleView
from modules.crud.models import (
    WholesaleProductModel,
    ProductFilterCriteria,
    PaginatedQueryResult,
)
from modules.crud.crud_service import D1CrudService


class TestRouterAndModels(unittest.TestCase):
    def test_app_router(self):
        state = {}
        router = AppRouter(session_state=state)
        self.assertEqual(router.get_active_module(), ModuleView.ANALYZER)

        router.navigate_to(ModuleView.UPLOADER)
        self.assertEqual(router.get_active_module(), ModuleView.UPLOADER)

        router.navigate_to(ModuleView.CRUD)
        self.assertEqual(router.get_active_module(), ModuleView.CRUD)

        router.navigate_to(ModuleView.MYSQL_UPLOADER)
        self.assertEqual(router.get_active_module(), ModuleView.MYSQL_UPLOADER)
        router.pass_data_to_mysql_uploader(["sample_row"])
        self.assertEqual(state.get("pending_mysql_upload"), ["sample_row"])


    def test_product_model_from_d1_row(self):
        row_dict = {
            "id": 1,
            "asin": "B0BDHWDR12",
            "title": "AirPods Pro",
            "favorite": 1,
            "cost": 175.0,
            "sell_price": 249.0,
            "profit": 32.50,
            "wholesaler_company_name": "Acme Supplies",
        }
        product = WholesaleProductModel.from_d1_row(row_dict)
        self.assertEqual(product.asin, "B0BDHWDR12")
        self.assertTrue(product.favorite)
        self.assertEqual(product.profit, 32.50)
        self.assertEqual(product.analyzing_software_name, "InternalAMZ")

        disp = product.to_display_row()
        self.assertEqual(disp["ASIN"], "B0BDHWDR12")
        self.assertEqual(disp["Favorite"], "⭐")
        self.assertEqual(disp["Analyzing Software Name"], "InternalAMZ")
        self.assertEqual(product.to_dict()["Analyzing Software Name"], "InternalAMZ")


    def test_product_filter_criteria(self):
        criteria = ProductFilterCriteria(
            keyword="AirPods",
            category="Electronics",
            min_profit=10.0,
            only_profitable=True,
        )
        self.assertEqual(criteria.keyword, "AirPods")
        self.assertEqual(criteria.category, "Electronics")
        self.assertEqual(criteria.min_profit, 10.0)
        self.assertTrue(criteria.only_profitable)

    def test_paginated_query_result(self):
        res = PaginatedQueryResult(items=[1, 2, 3], total_count=25, page=1, page_size=10)
        self.assertEqual(res.total_pages, 3)

    def test_crud_service_query_optimizations(self):
        executed = []

        class MockD1Client:
            def execute_query(self, sql, params=None):
                executed.append((sql, params))
                if "COUNT(*)" in sql:
                    return {"success": True, "results": [{"total_count": 120}]}
                return {
                    "success": True,
                    "results": [{"id": 1, "asin": "B0CSF57LJ9", "wholesaler_company_name": "Medcare LLC", "cost": 3.23}],
                }

        svc = D1CrudService(MockD1Client())

        # 1. Page 1 with returned items < page_size should skip COUNT(*) and use exact ASIN predicate
        criteria_p1 = ProductFilterCriteria(keyword="B0CSF57LJ9", page=1, page_size=25)
        res_p1 = svc.fetch_products(criteria_p1)
        self.assertEqual(res_p1.total_count, 1)
        self.assertEqual(len(executed), 1, "Should skip COUNT(*) when page 1 results < page_size")
        self.assertNotIn("SELECT *", executed[0][0], "Should select only DISPLAY_SQL_COLUMNS")
        self.assertIn("(asin = ? OR parent_asin = ?)", executed[0][0])

        # 2. Page 2 with known_total_count should skip COUNT(*)
        executed.clear()
        criteria_p2 = ProductFilterCriteria(page=2, page_size=25)
        res_p2 = svc.fetch_products(criteria_p2, known_total_count=120)
        self.assertEqual(res_p2.total_count, 120)
        self.assertEqual(len(executed), 1, "Should skip COUNT(*) when known_total_count is provided")

        # 3. toggle_favorite should execute only 1 UPDATE without pre-SELECT
        executed.clear()
        ok, _ = svc.toggle_favorite("B0CSF57LJ9", "Medcare LLC", False)
        self.assertTrue(ok)
        self.assertEqual(len(executed), 1, "toggle_favorite should not run a pre-SELECT")
        self.assertTrue(executed[0][0].startswith("UPDATE"))


if __name__ == "__main__":
    unittest.main()
