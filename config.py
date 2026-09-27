"""
Backward Compatibility Layer: config.py
=======================================
Redirects to the new modular package: modules.analyzer.config
"""

from modules.analyzer.config import MARKETPLACE_MAP, Marketplaces

__all__ = ["MARKETPLACE_MAP", "Marketplaces"]