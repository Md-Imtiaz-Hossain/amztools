"""
Backward Compatibility Layer: file_loader.py
============================================
Redirects to the new modular package: modules.analyzer.file_loader
"""

from modules.analyzer.file_loader import load_supplier_file

__all__ = ["load_supplier_file"]