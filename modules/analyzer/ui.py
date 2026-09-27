"""
Module 2: Analyze & Prepare Data - Streamlit User Interface
============================================================
Purpose:
    Renders the interactive Streamlit UI for Module 2.
    - Supplier file upload (CSV / Excel)
    - Wholesaler identification & configuration
    - SP-API Live credentials or Demo / Simulation mode
    - Fee adjustments (VAT, Inbound Shipping, Custom FBA / Referral fees)
    - Live progress bar & status updates
    - Analysis results summary cards (Items, Profitable Leads, Avg ROI, Top Profit)
    - Interactive filtering (profitable only, min ROI slider, min profit, category)
    - Target 52-Column Excel & CSV export
    - Direct handoff button to Module 3 (Upload to Cloudflare D1)
"""

import datetime
import os
import pandas as pd
import streamlit as st

from .config import MARKETPLACE_MAP
from .file_loader import load_supplier_file
from .analytics import clean_cost
from .sp_api_client import (
    clean_identifier,
    fetch_amazon_item_data,
    build_full_target_row,
    test_lwa_connection,
)
from .excel_exporter import export_to_target_excel


def render_analyzer_ui():
    """
    Renders the complete user interface for Module 2: Analyze & Prepare Data.
    All existing analysis workflows and features are encapsulated here.
    """
    st.header("📊 Module 2: Analyze & Prepare Data")
    st.markdown(
        "Upload supplier wholesale price lists (CSV or Excel) to evaluate Buy Box competition, FBA fees, "
        "referral fees, sales velocity, profit margins, and export reports in the **Target 52-Column Wholesale Format**."
    )

    # --- SIDEBAR CONFIGURATION FOR MODULE 2 ---
    st.sidebar.subheader("⚙️ Module 2 Settings")

    mode = st.sidebar.radio(
        "Execution Mode",
        ["🧪 Demo / Simulation Mode", "🟢 Live Amazon SP-API"],
        help="Demo mode simulates realistic Amazon catalog matches, pricing, BSR, and fees matching Target_Data_and_format.xlsx.",
        key="analyzer_execution_mode",
    )
    is_demo = "Demo" in mode

    client_id = ""
    client_secret = ""
    refresh_token = ""
    selected_marketplace = MARKETPLACE_MAP["US"]

    if not is_demo:
        st.sidebar.subheader("🔐 SP-API Credentials")
        client_id = st.sidebar.text_input("LWA Client ID", type="password", key="sp_client_id")
        client_secret = st.sidebar.text_input("LWA Client Secret", type="password", key="sp_client_secret")
        refresh_token = st.sidebar.text_input("Refresh Token (Atzr|...)", type="password", key="sp_refresh_token")

        market_choice = st.sidebar.selectbox("Marketplace", list(MARKETPLACE_MAP.keys()), key="sp_market_choice")
        selected_marketplace = MARKETPLACE_MAP.get(market_choice)

        if st.sidebar.button("Test SP-API Connection", key="sp_test_btn"):
            if client_id and client_secret and refresh_token:
                with st.sidebar.spinner("Testing connection..."):
                    success, msg = test_lwa_connection(client_id, client_secret, refresh_token)
                if success:
                    st.sidebar.success(msg)
                else:
                    st.sidebar.error(f"Connection failed: {msg}")
            else:
                st.sidebar.warning("Please provide Client ID, Secret, and Refresh Token.")

    st.sidebar.subheader("🏢 Wholesaler Info")
    wholesaler_input = st.sidebar.text_input(
        "Wholesaler Company Name*",
        value=st.session_state.get("wholesaler_company_name", ""),
        help="This company name is required and will be populated across all 52-column export rows.",
        key="wholesaler_name_input",
    )
    if wholesaler_input:
        st.session_state["wholesaler_company_name"] = wholesaler_input.strip()

    st.sidebar.subheader("💰 Default Assumptions & Fees")
    inbound_placement = st.sidebar.number_input(
        "Inbound Placement Fee ($/unit)",
        value=0.25,
        step=0.05,
        min_value=0.0,
        help="Amazon Inbound Placement service fee (standard ~$0.21 - $0.35/unit).",
        key="inbound_placement_fee_input",
    )
    inbound_shipping = st.sidebar.number_input(
        "Inbound Shipping Estimate ($/unit)",
        value=0.50,
        step=0.10,
        min_value=0.0,
        help="Estimated freight shipping cost per unit from supplier to Amazon prep center.",
        key="inbound_shipping_input",
    )
    vat_rate = st.sidebar.number_input(
        "VAT Rate (%)",
        value=0.0,
        step=1.0,
        min_value=0.0,
        max_value=100.0,
        help="Value Added Tax percentage applied to European or UK marketplaces.",
        key="vat_rate_input",
    )

    with st.sidebar.expander("🛠️ Advanced Fee Overrides", expanded=False):
        override_ref = st.checkbox("Override Referral Fee %", value=False, key="override_ref_chk")
        custom_ref_pct = (
            st.number_input("Custom Referral Fee (%)", value=15.0, step=1.0, key="custom_ref_pct_input")
            if override_ref
            else None
        )

        override_fba = st.checkbox("Override FBA Fee ($)", value=False, key="override_fba_chk")
        custom_fba_fee = (
            st.number_input("Custom FBA Fee ($)", value=4.50, step=0.50, key="custom_fba_fee_input")
            if override_fba
            else None
        )

    # --- MAIN VIEW: FILE INGESTION ---
    st.subheader("1. Ingest Supplier Wholesale Catalog")
    u_col1, u_col2 = st.columns([3, 1])

    with u_col1:
        uploaded_file = st.file_uploader(
            "Upload Supplier File (.csv, .xlsx, .xls)",
            type=["csv", "xlsx", "xls"],
            help="Upload a supplier wholesale price catalog. Ensure it contains a column for UPC/EAN/ASIN and Cost.",
            key="analyzer_file_uploader",
        )

    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sample_file_path = os.path.join(project_root, "sample_supplier_catalog.csv")

    with u_col2:
        st.write("")
        st.write("")
        if os.path.exists(sample_file_path):
            if st.button("📄 Load Sample Catalog", key="load_sample_cat_btn", help="Load the built-in sample catalog with 13 products"):
                st.session_state["use_sample_catalog"] = True
                st.session_state["wholesaler_company_name"] = st.session_state.get("wholesaler_company_name") or "Acme Wholesale Supplies LLC"
                st.rerun()

    df = None
    if uploaded_file is not None:
        st.session_state["use_sample_catalog"] = False
        try:
            df = load_supplier_file(uploaded_file)
            st.success(f"Loaded `{uploaded_file.name}` successfully ({len(df)} rows detected).")
        except Exception as e:
            st.error(f"Error loading file: {e}")
            return
    elif st.session_state.get("use_sample_catalog") and os.path.exists(sample_file_path):
        try:
            df = load_supplier_file(sample_file_path)
            st.success(f"Loaded built-in `sample_supplier_catalog.csv` successfully ({len(df)} sample rows ready for analysis).")
        except Exception as e:
            st.error(f"Error loading sample catalog: {e}")
            return
    else:
        st.info("👋 Upload a CSV or Excel price list to get started, or click **📄 Load Sample Catalog** above to test immediately.")
        return

    with st.expander("👁️ Preview Raw Uploaded File (First 5 Rows)", expanded=False):
        st.dataframe(df.head(5), use_container_width=True)

    # Column Mapping
    st.subheader("2. Map Catalog Columns")
    cols = list(df.columns)

    default_upc_idx = 0
    default_cost_idx = 0
    for idx, c in enumerate(cols):
        c_lower = str(c).lower()
        if any(k in c_lower for k in ["upc", "ean", "barcode", "asin", "sku", "isbn", "item id", "product id"]):
            default_upc_idx = idx
            break
    for idx, c in enumerate(cols):
        c_lower = str(c).lower()
        if any(k in c_lower for k in ["cost", "price", "wholesale", "unit price", "rate"]):
            default_cost_idx = idx
            break

    c_map1, c_map2 = st.columns(2)
    with c_map1:
        upc_col = st.selectbox(
            "Product ID Column (UPC / EAN / ASIN)",
            cols,
            index=default_upc_idx,
            key="analyzer_upc_col",
        )
    with c_map2:
        cost_col = st.selectbox(
            "Wholesale Cost Column",
            cols,
            index=default_cost_idx,
            key="analyzer_cost_col",
        )

    # Action Button
    action_label = "🚀 Run Demo Catalog Analysis" if is_demo else "🚀 Run Live SP-API Catalog Analysis"
    if st.button(action_label, type="primary", key="analyzer_run_btn"):
        active_wholesaler = st.session_state.get("wholesaler_company_name", "").strip()
        if not active_wholesaler:
            st.error("⚠️ **Wholesaler Company Name is required!** Please type the Wholesaler Company Name in the sidebar before starting.")
            return

        if not is_demo and (not client_id or not client_secret or not refresh_token):
            st.error("Please provide your Amazon SP-API credentials in the sidebar, or switch to **Demo / Simulation Mode**.")
            return

        credentials = {
            "refresh_token": refresh_token.strip(),
            "lwa_app_id": client_id.strip(),
            "lwa_client_secret": client_secret.strip(),
        }

        analyzed_rows = []
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        total_rows = len(df)
        run_time = datetime.datetime.now()

        for index, row in df.iterrows():
            raw_id = row.get(upc_col, "")
            raw_cost = clean_cost(row.get(cost_col, 0.0))

            clean_id, id_type = clean_identifier(raw_id)
            status_text.text(f"Analyzing {index + 1}/{total_rows}: {clean_id or 'Item'}...")

            item_data = fetch_amazon_item_data(
                raw_id,
                credentials,
                selected_marketplace,
                is_demo=is_demo,
                cost=raw_cost,
            )

            target_row = build_full_target_row(
                item_data=item_data,
                cost=raw_cost,
                inbound_placement_fee=inbound_placement,
                inbound_shipping=inbound_shipping,
                vat_pct=vat_rate,
                referral_fee_pct=custom_ref_pct,
                estimated_fba_fees=custom_fba_fee,
                wholesaler_company_name=active_wholesaler,
                run_timestamp=run_time,
            )

            analyzed_rows.append(target_row)
            progress_bar.progress((index + 1) / total_rows)

        status_text.text("Analysis complete! Full target dataset generated.")
        st.session_state["analysis_results"] = pd.DataFrame(analyzed_rows)

    # --- RESULTS & REPORTING ---
    if "analysis_results" in st.session_state:
        results_df = st.session_state["analysis_results"]
        st.markdown("---")
        st.header("📊 Target Format Wholesale Analysis Results")

        # Metrics Summary Cards
        m1, m2, m3, m4, m5 = st.columns(5)
        total_items = len(results_df)
        listed_items = results_df[results_df["Sell Price"].notnull() & (results_df["Sell Price"] > 0)]
        profitable_leads = results_df[results_df["Profit ($)"].notnull() & (results_df["Profit ($)"] > 0)]
        avg_roi = listed_items["ROI (%)"].mean() * 100.0 if not listed_items.empty else 0.0
        max_profit = results_df["Profit ($)"].max() if not results_df["Profit ($)"].dropna().empty else 0.0

        m1.metric("Items Analyzed", total_items)
        m2.metric("Listed on Amazon", len(listed_items))
        m3.metric("Profitable Leads (Profit > $0)", len(profitable_leads))
        m4.metric("Avg ROI on Listed Items", f"{avg_roi:.1f}%")
        m5.metric("Top Profit Lead", f"${max_profit:.2f}")

        # Interactive Filters
        st.subheader("🔍 Filter Wholesale Leads")
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            only_profitable = st.checkbox("Only show profitable products (Profit > $0)", value=False, key="filter_prof")
        with f_col2:
            min_roi = st.slider("Minimum ROI (%)", min_value=-50, max_value=150, value=0, step=5, key="filter_roi")
        with f_col3:
            min_profit = st.number_input("Minimum Net Profit ($)", value=0.0, step=1.0, key="filter_profit")
        with f_col4:
            categories = ["All Categories"] + sorted(list(results_df["Category"].dropna().unique()))
            selected_cat = st.selectbox("Category", categories, key="filter_cat")

        filtered_df = results_df.copy()
        if only_profitable:
            filtered_df = filtered_df[filtered_df["Profit ($)"].notnull() & (filtered_df["Profit ($)"] > 0)]
        if min_roi > -50:
            filtered_df = filtered_df[filtered_df["ROI (%)"].isnull() | (filtered_df["ROI (%)"] >= (min_roi / 100.0))]
        if min_profit > 0:
            filtered_df = filtered_df[filtered_df["Profit ($)"].isnull() | (filtered_df["Profit ($)"] >= min_profit)]
        if selected_cat != "All Categories":
            filtered_df = filtered_df[filtered_df["Category"] == selected_cat]

        st.write(f"Showing **{len(filtered_df)}** of **{len(results_df)}** analyzed products:")

        display_cols = [
            "ASIN", "Product ID", "Wholesaller Company Name", "Brand", "Title",
            "Category", "Sales Rank", "Sub Category", "Sub Category Sales Rank",
            "Customer Reviews", "Average Rating", "Total Review Count",
            "Current Est Sales", "Estimated Monthly Revenue ($)",
            "Cost", "Sell Price", "Referral Fee %", "Referral Fee",
            "FBA Pick & Pack Fee ($)", "Fulfillment Subtotal",
            "Profit ($)", "Margin (%)", "ROI (%)",
            "Break Even Sell Price", "Total Offers", "Selling Restriction", "About this item"
        ]
        preview_df = filtered_df[[c for c in display_cols if c in filtered_df.columns]].copy()

        st.dataframe(
            preview_df,
            column_config={
                "Cost": st.column_config.NumberColumn(format="$%.2f"),
                "Sell Price": st.column_config.NumberColumn(format="$%.2f"),
                "Referral Fee %": st.column_config.NumberColumn(format="%.1f%%"),
                "Referral Fee": st.column_config.NumberColumn(format="$%.2f"),
                "FBA Pick & Pack Fee ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Fulfillment Subtotal": st.column_config.NumberColumn(format="$%.2f"),
                "Estimated Monthly Revenue ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Profit ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Margin (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "ROI (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Break Even Sell Price": st.column_config.NumberColumn(format="$%.2f"),
                "Current Est Sales": st.column_config.NumberColumn(format="%d"),
                "Sales Rank": st.column_config.NumberColumn(format="%d"),
                "Sub Category Sales Rank": st.column_config.NumberColumn(format="%d"),
                "Average Rating": st.column_config.NumberColumn(format="%.1f ⭐"),
                "Total Review Count": st.column_config.NumberColumn(format="%d"),
            },
            use_container_width=True,
        )

        # Export & Pipeline Transition
        st.markdown("### 📥 Export & Next Module")
        d_col1, d_col2, d_col3 = st.columns(3)

        with d_col1:
            xlsx_bytes = export_to_target_excel(filtered_df)
            st.download_button(
                label="📥 Download Target Excel (.xlsx)",
                data=xlsx_bytes,
                file_name=f"amazon_wholesale_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_target_xlsx",
            )

        with d_col2:
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📄 Download Analysis CSV",
                data=csv_data,
                file_name="amazon_wholesale_analysis_report.csv",
                mime="text/csv",
                key="download_target_csv",
            )

        with d_col3:
            if st.button("☁️ Send Data to Module 3 (Cloudflare D1)", type="secondary", key="send_to_uploader_btn"):
                # Save into session state for Module 3
                st.session_state["pending_d1_upload"] = filtered_df
                st.session_state["active_module"] = "uploader"
                st.rerun()
