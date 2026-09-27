"""
Module 1: Application Entrypoint & Navigation Coordinator
=========================================================
This module serves as the primary gateway into the multi-module application.
It orchestrates page routing, manages global session state across modules,
and renders the main user interface container.

Sub-components:
- router: Navigation router and module state coordinator.
- ui: Streamlit dashboard entrypoint and multi-module layout manager.
"""

from .router import AppRouter, ModuleView

try:
    from .ui import render_entrypoint_app
except ImportError:
    render_entrypoint_app = None

__all__ = ["AppRouter", "ModuleView", "render_entrypoint_app"]
