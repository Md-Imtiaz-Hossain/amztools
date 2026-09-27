"""
Backward Compatibility Layer: analytics.py
==========================================
Redirects to the new modular package: modules.analyzer.analytics
"""

from modules.analyzer.analytics import (
    clean_cost,
    calculate_referral_fee,
    calculate_fba_fee,
    estimate_monthly_sales,
    calculate_comprehensive_financials,
)

__all__ = [
    "clean_cost",
    "calculate_referral_fee",
    "calculate_fba_fee",
    "estimate_monthly_sales",
    "calculate_comprehensive_financials",
]