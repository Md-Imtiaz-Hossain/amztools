"""
Module 1: Entrypoint - Streamlit Application UI Frame & Navigation Hub
========================================================================
Purpose:
    Renders the outer Streamlit application frame, including global branding,
    sidebar navigation, module status indicators, and view dispatching.

Architecture:
    - Configures page title, icon, and wide responsive layout.
    - Renders the global sidebar allowing seamless switching between:
        1. 📊 Module 2: Analyze & Prepare Data (Wholesale catalog analysis & 52-column export)
        2. ☁️ Module 3: Upload Data to Cloudflare D1 (Database upload pipeline)
        3. 🗄️ Module 4: Database CRUD Operations (Fetch, view, filter, edit, delete from D1)
    - Dispatches execution to the corresponding module's UI controller.

Planned Workflow:
    - Step 1: Render top-level layout and navigation header.
    - Step 2: Query AppRouter for active module view.
    - Step 3: Render active module view:
        - If Module 2: Invoke modules.analyzer.ui.render_analyzer_ui()
        - If Module 3: Invoke modules.uploader.ui.render_uploader_ui()
        - If Module 4: Invoke modules.crud.ui.render_crud_ui()
"""

import streamlit as st
from .router import AppRouter, ModuleView
from .session_bridge import sync_session_credentials, clear_all_credentials

# Lazy / conditional imports for module UI renderers
# (Each module implements its own self-contained Streamlit UI view)


def render_entrypoint_app():
    """
    Main application entrypoint rendering function.
    Coordinates page setup, sidebar navigation, and module dispatching.
    """
    # 1. Global Page Configuration
    st.set_page_config(
        page_title="Amazon Wholesale Suite & Cloudflare D1 Pipeline",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # 2. Ephemeral Browser Session Sync (Zero disk writes, purged on tab close)
    sync_session_credentials()

    # 3. Initialize Navigation Router
    router = AppRouter(session_state=st.session_state)

    # 4. Render Top Navigation Bar & Sidebar
    st.sidebar.title("🚀 Amazon Wholesale Suite")
    st.sidebar.markdown(
        "**Multi-Module Pipeline**\n"
        "1. Ingest & Analyze Wholesale Catalogs\n"
        "2. Upload Standardized Output to Cloudflare D1\n"
        "3. Manage & Query Stored Catalog Records"
    )
    st.sidebar.markdown("---")

    # Navigation Selection
    module_options = {
        ModuleView.ANALYZER.value: "📊 Module 2: Analyze & Prepare Data",
        ModuleView.UPLOADER.value: "☁️ Module 3: Upload to Cloudflare D1",
        ModuleView.CRUD.value: "🗄️ Module 4: Database CRUD & Viewer",
    }

    current_module = router.get_active_module()
    selected_module_key = st.sidebar.radio(
        "Select Active Module:",
        options=list(module_options.keys()),
        format_func=lambda k: module_options[k],
        index=list(module_options.keys()).index(current_module.value),
    )

    # Update router state if changed
    if selected_module_key != current_module.value:
        router.navigate_to(ModuleView(selected_module_key))
        current_module = ModuleView(selected_module_key)

    st.sidebar.markdown("---")
    st.sidebar.markdown("🔒 **Browser Session Storage**")
    st.sidebar.caption("Ephemeral tab storage active. Keys exist only in this browser tab and vanish when closed. Zero disk writes.")
    if st.sidebar.button(
        "🧹 Wipe All Keys",
        key="global_wipe_keys_btn",
        use_container_width=True,
        help="Immediately purge all API credentials and database tokens from browser memory",
    ):
        clear_all_credentials()
        st.sidebar.success("All credentials erased!")
        st.rerun()

    st.sidebar.caption("v2.0.0 • Cloudflare D1 + Amazon SP-API Ready")

    # 4. Dispatch to Selected Module View
    if current_module == ModuleView.ANALYZER:
        # Module 2: Analyze and Prepare Data (Current feature and all code)
        from modules.analyzer.ui import render_analyzer_ui
        render_analyzer_ui()

    elif current_module == ModuleView.UPLOADER:
        # Module 3: Upload to Cloudflare Database D1
        from modules.uploader.ui import render_uploader_ui
        render_uploader_ui()

    elif current_module == ModuleView.CRUD:
        # Module 4: Database CRUD Operation & Viewer
        from modules.crud.ui import render_crud_ui
        render_crud_ui()
