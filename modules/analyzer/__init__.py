"""
Module 2: Analyze and Prepare Data Module
=========================================
Purpose:
    Core Amazon Wholesale Catalog analysis engine. Ingests supplier wholesale
    lists (CSV or Excel), queries Amazon SP-API (or simulates realistic market
    data in Demo mode), calculates comprehensive financial metrics (referral fees,
    FBA Pick & Pack fees, break-even sell price, net profit, margin, and ROI),
    and exports a standardized 52-column wholesale dataset.

Key Components:
    - config: Marketplace mappings and regional API endpoints.
    - file_loader: Robust supplier file parsing (CSV/Excel) with encoding handling.
    - analytics: Mathematical fee models, FBA sizing, referral tiers, and sales estimation.
    - sp_api_client: Live Amazon SP-API client, demo simulation engine, and target row builder.
    - excel_exporter: Formatted 52-column Excel workbook generator matching Target specifications.
    - ui: Streamlit user interface for running catalog analyses, filtering leads, and downloading reports.

Output:
    A standardized 52-column pandas DataFrame or Excel/CSV workbook, ready for ingestion
    into Module 3 (Upload to Cloudflare D1 Database).
"""

from .config import MARKETPLACE_MAP

try:
    from .file_loader import load_supplier_file
except ImportError:
    load_supplier_file = None
from .analytics import (
    clean_cost,
    calculate_referral_fee,
    calculate_fba_fee,
    estimate_monthly_sales,
    calculate_comprehensive_financials,
)
from .sp_api_client import (
    TARGET_COLUMNS,
    clean_identifier,
    fetch_amazon_item_data,
    build_full_target_row,
    test_lwa_connection,
)
try:
    from .excel_exporter import export_to_target_excel
except ImportError:
    export_to_target_excel = None

try:
    from .ui import render_analyzer_ui
except ImportError:
    render_analyzer_ui = None

__all__ = [
    "MARKETPLACE_MAP",
    "load_supplier_file",
    "clean_cost",
    "calculate_referral_fee",
    "calculate_fba_fee",
    "estimate_monthly_sales",
    "calculate_comprehensive_financials",
    "TARGET_COLUMNS",
    "clean_identifier",
    "fetch_amazon_item_data",
    "build_full_target_row",
    "test_lwa_connection",
    "export_to_target_excel",
    "render_analyzer_ui",
]
