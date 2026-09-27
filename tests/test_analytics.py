"""
Tests for Module 2: Analytics & Fee Calculation Logic.
"""

import unittest
from modules.analyzer.analytics import (
    clean_cost,
    calculate_referral_fee,
    calculate_fba_fee,
    estimate_monthly_sales,
    calculate_comprehensive_financials,
)


class TestAnalytics(unittest.TestCase):
    def test_clean_cost(self):
        self.assertEqual(clean_cost("$12.50"), 12.50)
        self.assertEqual(clean_cost("€99.99"), 99.99)
        self.assertEqual(clean_cost("1,250.00"), 1250.00)
        self.assertEqual(clean_cost(None), 0.0)
        self.assertEqual(clean_cost("nan"), 0.0)
        self.assertEqual(clean_cost(""), 0.0)

    def test_calculate_referral_fee(self):
        # Beauty items <= $10 -> 8%
        fee_low = calculate_referral_fee(8.00, category="Beauty & Personal Care")
        self.assertEqual(fee_low, round(8.00 * 0.08, 2))

        # Beauty items > $10 -> 15%
        fee_high = calculate_referral_fee(50.00, category="Beauty & Personal Care")
        self.assertEqual(fee_high, round(50.00 * 0.15, 2))

        # Minimum floor fee is $0.30
        fee_floor = calculate_referral_fee(1.00, category="Beauty & Personal Care")
        self.assertEqual(fee_floor, 0.30)

        # None/Zero sell price
        self.assertIsNone(calculate_referral_fee(None))
        self.assertIsNone(calculate_referral_fee(0))

    def test_calculate_fba_fee(self):
        # Small standard item
        fee_small = calculate_fba_fee(weight_lb=0.5, dimensions_str="10 x 8 x 0.5", sell_price=25.0)
        self.assertIsNotNone(fee_small)
        self.assertGreater(fee_small, 0)

        # Low-price FBA eligibility (<= $10.00)
        fee_low_price = calculate_fba_fee(weight_lb=0.5, dimensions_str="10 x 8 x 0.5", sell_price=9.99)
        self.assertIsNotNone(fee_low_price)
        self.assertLess(fee_low_price, fee_small)

        # Zero or None sell price returns None
        self.assertIsNone(calculate_fba_fee(sell_price=None))

    def test_estimate_monthly_sales(self):
        # Rank 1 should yield high sales
        sales_top = estimate_monthly_sales(1, "Beauty & Personal Care")
        self.assertGreater(sales_top, 5000)

        # Very high rank should default to 5
        sales_low = estimate_monthly_sales(999999, "Beauty & Personal Care")
        self.assertEqual(sales_low, 5)

        # Missing or None rank returns 5
        self.assertEqual(estimate_monthly_sales(None, "Electronics"), 5)

    def test_calculate_comprehensive_financials(self):
        fin = calculate_comprehensive_financials(
            cost=20.00,
            sell_price=50.00,
            category="Beauty & Personal Care",
            weight_lb=0.8,
            dimensions_str="6 x 4 x 2",
            inbound_placement_fee=0.25,
            inbound_shipping=0.50,
        )
        self.assertEqual(fin["Sell Price"], 50.00)
        self.assertIsNotNone(fin["Profit"])
        self.assertGreater(fin["Profit"], 0)
        self.assertIsNotNone(fin["Margin"])
        self.assertIsNotNone(fin["ROI"])
        self.assertGreater(fin["Break Even Sell Price"], 20.00)


if __name__ == "__main__":
    unittest.main()
