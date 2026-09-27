"""
Backward Compatibility Layer: excel_exporter.py
===============================================
Redirects to the new modular package: modules.analyzer.excel_exporter
"""

from modules.analyzer.excel_exporter import export_to_target_excel

__all__ = ["export_to_target_excel"]
