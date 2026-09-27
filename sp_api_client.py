"""
Backward Compatibility Layer: sp_api_client.py
==============================================
Redirects to the new modular package: modules.analyzer.sp_api_client
"""

from modules.analyzer.sp_api_client import (
    TARGET_COLUMNS,
    clean_identifier,
    fetch_amazon_item_data,
    build_full_target_row,
    test_lwa_connection,
)

__all__ = [
    "TARGET_COLUMNS",
    "clean_identifier",
    "fetch_amazon_item_data",
    "build_full_target_row",
    "test_lwa_connection",
]