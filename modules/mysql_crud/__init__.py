"""
Module 6: Remote MySQL Database CRUD Operations & Viewer
========================================================
Purpose:
    Provides complete Create, Read, Update, Delete (CRUD), filtering, search,
    KPI analytics, and Target Excel/CSV export capabilities for wholesale
    catalog records stored in a remote MySQL database (e.g., Hostinger MySQL).
"""

from .crud_service import MySQLCrudService
from .ui import render_mysql_crud_ui

__all__ = [
    "MySQLCrudService",
    "render_mysql_crud_ui",
]
