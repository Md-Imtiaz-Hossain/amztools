"""
Module 1: Entrypoint - Application Router & Navigation Controller
==================================================================
Purpose:
    Maintains application routing state, registers available modules,
    and handles transitions between different operational phases:
    1. Module 2: Analyze & Prepare Data
    2. Module 3: Upload Data to Cloudflare D1 Database
    3. Module 4: Cloudflare D1 Database CRUD Operations & Viewer

Architecture:
    - ModuleView (Enum): Standardized identifiers for each module.
    - AppRouter (Class): State manager that determines which module's UI
      to invoke based on user selection or programmatic redirection
      (e.g., automatically suggesting uploading to D1 after Module 2 completes).

Planned Workflow:
    Step 1: User lands on Entrypoint (Home / Dashboard).
    Step 2: User runs Module 2 to analyze catalog and generate 52-column dataset.
    Step 3: User transitions to Module 3 to upload the generated file to Cloudflare D1.
    Step 4: User transitions to Module 4 to view, filter, edit, or delete items in Cloudflare D1.
"""

from enum import Enum
from typing import Optional, Dict, Any


class ModuleView(str, Enum):
    """
    Enumeration of available application modules.
    Each enum value represents a distinct page/view within the multi-module system.
    """
    ANALYZER = "analyzer"  # Module 2: Analyze and Prepare Data
    UPLOADER = "uploader"  # Module 3: Upload Data to Cloudflare D1 Database
    CRUD = "crud"          # Module 4: Database CRUD Operations & Data Viewer


class AppRouter:
    """
    Central routing controller for the application.

    Responsibilities:
    - Tracks the currently active module view.
    - Synchronizes navigation state with Streamlit session_state.
    - Handles cross-module data passing (e.g. passing Module 2 analysis output
      directly into Module 3's upload queue).
    - Coordinates application-wide lifecycle events.
    """

    def __init__(self, session_state: Optional[Dict[str, Any]] = None):
        """
        Initialize the router with the active session state context.

        Args:
            session_state: Optional dictionary or Streamlit session state object
                           used to persist current navigation and data state.
        """
        self.session_state = session_state if session_state is not None else {}
        self._init_router_state()

    def _init_router_state(self) -> None:
        """
        Initialize default routing parameters in the session state if not already set.
        """
        if "active_module" not in self.session_state:
            self.session_state["active_module"] = ModuleView.ANALYZER.value

    def get_active_module(self) -> ModuleView:
        """
        Retrieve the currently active module view.

        Returns:
            ModuleView: The active module enum value.
        """
        active_val = self.session_state.get("active_module", ModuleView.ANALYZER.value)
        try:
            return ModuleView(active_val)
        except ValueError:
            return ModuleView.ANALYZER

    def navigate_to(self, module: ModuleView) -> None:
        """
        Change the active view to the specified module.

        Args:
            module (ModuleView): The target module to navigate to.
        """
        self.session_state["active_module"] = module.value

    def pass_data_to_uploader(self, dataframe_or_filepath: Any) -> None:
        """
        Store Module 2 output data in session state so Module 3 (Uploader)
        can immediately access it without requiring manual file re-upload.

        Args:
            dataframe_or_filepath: Pandas DataFrame or path to exported Excel/CSV file.
        """
        self.session_state["pending_d1_upload"] = dataframe_or_filepath
