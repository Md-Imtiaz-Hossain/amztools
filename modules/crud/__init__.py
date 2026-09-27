"""
Module 4: Database CRUD Operations & Data Viewer Module
======================================================
Purpose:
    Enables full Create, Read, Update, and Delete (CRUD) operations on wholesale
    catalog records persisted in Cloudflare D1 database.
    Provides a rich interactive user interface for querying historical wholesale leads,
    filtering by performance metrics (Profit, ROI, Category, Wholesaler), modifying records,
    and managing the stored product database.

Components:
    - models: Data classes defining product records, filter parameters, and pagination structures.
    - crud_service: Business logic layer executing parameterized SQL queries against Cloudflare D1.
    - ui: Streamlit user interface featuring a live D1 data browser, KPI metrics, search, edit, and delete controls.
"""

from .models import WholesaleProductModel, ProductFilterCriteria, PaginatedQueryResult
from .crud_service import D1CrudService
try:
    from .ui import render_crud_ui
except ImportError:
    render_crud_ui = None

__all__ = [
    "WholesaleProductModel",
    "ProductFilterCriteria",
    "PaginatedQueryResult",
    "D1CrudService",
    "render_crud_ui",
]
