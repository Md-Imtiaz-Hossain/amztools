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


class TestRouterAndModels(unittest.TestCase):
    def test_app_router(self):
        state = {}
        router = AppRouter(session_state=state)
        self.assertEqual(router.get_active_module(), ModuleView.ANALYZER)

        router.navigate_to(ModuleView.UPLOADER)
        self.assertEqual(router.get_active_module(), ModuleView.UPLOADER)

        router.navigate_to(ModuleView.CRUD)
        self.assertEqual(router.get_active_module(), ModuleView.CRUD)

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

        disp = product.to_display_row()
        self.assertEqual(disp["ASIN"], "B0BDHWDR12")
        self.assertEqual(disp["Favorite"], "⭐")

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


if __name__ == "__main__":
    unittest.main()
