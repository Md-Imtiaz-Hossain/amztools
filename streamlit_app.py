"""
Amazon Wholesale Catalog Analyzer & Cloudflare D1 Pipeline
===========================================================
Root Streamlit Entrypoint Module
--------------------------------
This is the primary user-facing entrypoint for running the Streamlit web application.
It delegates to Module 1 (modules.entrypoint), which orchestrates navigation between:
- Module 2: 📊 Analyze & Prepare Data (Wholesale catalog analysis & 52-column export)
- Module 3: ☁️ Upload Data to Cloudflare D1 (Database upload pipeline)
- Module 4: 🗄️ Database CRUD Operations (Fetch, view, filter, edit, delete from D1)

Usage:
    streamlit run streamlit_app.py
"""

import sys
import os

# Ensure project root directory is on the Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from modules.entrypoint.ui import render_entrypoint_app

if __name__ == "__main__":
    render_entrypoint_app()
else:
    # When executed by Streamlit runner
    render_entrypoint_app()