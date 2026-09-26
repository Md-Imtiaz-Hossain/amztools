import datetime
import os
import pandas as pd
import streamlit as st

from analytics import clean_cost
from config import MARKETPLACE_MAP
from excel_exporter import export_to_target_excel
from file_loader import load_supplier_file
from sp_api_client import (
    TARGET_COLUMNS,
    build_full_target_row,
    clean_identifier,
    fetch_amazon_item_data,
    test_lwa_connection,
)

st.set_page_config(
    page_title="Amazon Wholesale Catalog Analyzer",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Amazon Wholesale Catalog Analyzer")
st.markdown(
    "Upload supplier wholesale price lists (CSV or Excel) to evaluate Buy Box competition, FBA fees, "
    "referral fees, sales velocity, profit margins, and export reports in the **Target 52-Column Wholesale Format**."
)

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Configuration")

mode = st.sidebar.radio(
    "Execution Mode",
    ["🧪 Demo / Simulation Mode", "🟢 Live Amazon SP-API"],
    help="Demo mode simulates realistic Amazon catalog matches, pricing, BSR, and fees matching Target_Data_and_format.xlsx.",
)
is_demo = "Demo" in mode

client_id = ""
client_secret = ""
refresh_token = ""
selected_marketplace = MARKETPLACE_MAP["US"]

if not is_demo:
    st.sidebar.subheader("🔐 SP-API Credentials")
    client_id = st.sidebar.text_input("LWA Client ID", type="password")
    client_secret = st.sidebar.text_input("LWA Client Secret", type="password")
    refresh_token = st.sidebar.text_input("Refresh Token (Atzr|...)", type="password")

    market_choice = st.sidebar.selectbox("Marketplace", list(MARKETPLACE_MAP.keys()))
    selected_marketplace = MARKETPLACE_MAP.get(market_choice)

    if st.sidebar.button("Test SP-API Connection"):
        if client_id and client_secret and refresh_token:
            with st.sidebar.spinner("Testing connection..."):
                success, msg = test_lwa_connection(client_id, client_secret, refresh_token)
            if success:
                st.sidebar.success(msg)
            else:
                st.sidebar.error(f"Connection failed: {msg}")
        else:
            st.sidebar.warning("Please enter Client ID, Secret, and Refresh Token.")
else:
    st.sidebar.info("💡 **Demo Mode Active**: Simulates full 52-column target catalog data and financials instantly.")

# Fee Configuration Expander
with st.sidebar.expander("💰 Fee & Economics Settings", expanded=False):
    auto_fba = st.checkbox("Auto-calculate FBA Fee by Weight & Size Tier", value=True)
    custom_fba_fee = None
    if not auto_fba:
        custom_fba_fee = st.number_input("Override FBA Fee ($)", min_value=0.0, value=4.50, step=0.25)

    auto_ref = st.checkbox("Auto-detect Category Referral Fee (e.g. Beauty 8%/15%)", value=True)
    custom_ref_pct = None
    if not auto_ref:
        custom_ref_pct = st.number_input("Override Referral Fee (%)", min_value=0.0, max_value=50.0, value=15.0, step=0.5)

    inbound_placement = st.number_input("Inbound Placement Fee per Unit ($)", min_value=0.0, value=0.00, step=0.05)
    inbound_shipping = st.number_input("Inbound Shipping Estimate ($)", min_value=0.0, value=0.00, step=0.10)
    vat_rate = st.number_input("VAT (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)

# --- WHOLESALE SUPPLIER CONFIGURATION ---
st.sidebar.markdown("---")
st.sidebar.subheader("🏢 Wholesale Supplier")
wholesaler_input = st.sidebar.text_input(
    "Wholesaller Company Name *",
    value=st.session_state.get("wholesaler_company_name", ""),
    placeholder="e.g. Acme Wholesale Supplies LLC",
    help="Required: Enter the wholesale supplier company name before analyzing the catalog.",
)
if wholesaler_input:
    st.session_state["wholesaler_company_name"] = wholesaler_input.strip()

# --- SUPPLIER DATA INPUT ---
st.markdown("---")
col_upload, col_sample = st.columns([3, 1])

with col_upload:
    uploaded_file = st.file_uploader(
        "Upload Supplier Price List (CSV or Excel)",
        type=["csv", "xlsx", "xls"],
        help="Upload supplier catalogs containing barcode numbers (UPC/EAN/ASIN) and wholesale costs.",
    )

with col_sample:
    st.write("Or test with ready sample data:")
    if st.button("📄 Load Sample Catalog"):
        sample_path = os.path.join(os.path.dirname(__file__), "sample_supplier_catalog.csv")
        if os.path.exists(sample_path):
            st.session_state["supplier_df"] = pd.read_csv(sample_path, dtype=str)
            st.session_state["source_label"] = "Sample Supplier Catalog"
            st.success("Loaded sample catalog with 12 wholesale products!")
        else:
            st.error("Sample catalog file not found.")

# Manage loaded dataframe in session state
if uploaded_file is not None:
    try:
        st.session_state["supplier_df"] = load_supplier_file(uploaded_file)
        st.session_state["source_label"] = uploaded_file.name
    except Exception as e:
        st.error(f"Error reading uploaded file: {e}")

df = st.session_state.get("supplier_df")

if df is not None and not df.empty:
    st.subheader(f"📋 Supplier Data Preview ({st.session_state.get('source_label', 'Active File')} - {len(df)} rows)")
    st.dataframe(df.head(5), use_container_width=True)

    # Smart column matching
    cols = list(df.columns)
    default_upc_idx = 0
    default_cost_idx = min(1, len(cols) - 1)

    for i, c in enumerate(cols):
        c_lower = str(c).lower()
        if any(k in c_lower for k in ["upc", "barcode", "ean", "asin", "identifier", "sku"]):
            default_upc_idx = i
            break

    for i, c in enumerate(cols):
        c_lower = str(c).lower()
        if any(k in c_lower for k in ["cost", "price", "wholesale", "unit price"]):
            default_cost_idx = i
            break

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Column Mapping")
    upc_col = st.sidebar.selectbox("Product ID (UPC / EAN / ASIN)", cols, index=default_upc_idx)
    cost_col = st.sidebar.selectbox("Wholesale Cost", cols, index=default_cost_idx)

    action_label = "🚀 Run Demo Catalog Analysis" if is_demo else "🚀 Run Live SP-API Catalog Analysis"
    if st.button(action_label, type="primary"):
        active_wholesaler = st.session_state.get("wholesaler_company_name", "").strip()
        if not active_wholesaler:
            st.error("⚠️ **Wholesaller Company Name is required!** Please type the Wholesaller Company Name in the sidebar before starting the analysis.")
        elif not is_demo and (not client_id or not client_secret or not refresh_token):
            st.error("Please provide your Amazon SP-API credentials in the sidebar, or switch to **Demo / Simulation Mode**.")
        else:
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
        only_profitable = st.checkbox("Only show profitable products (Profit > $0)", value=False)
    with f_col2:
        min_roi = st.slider("Minimum ROI (%)", min_value=-50, max_value=150, value=0, step=5)
    with f_col3:
        min_profit = st.number_input("Minimum Net Profit ($)", value=0.0, step=1.0)
    with f_col4:
        categories = ["All Categories"] + sorted(list(results_df["Category"].dropna().unique()))
        selected_cat = st.selectbox("Category", categories)

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

    # Table preview with essential columns
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

    # --- DOWNLOAD BUTTONS ---
    st.markdown("### 📥 Export Analysis")
    down_col1, down_col2 = st.columns(2)

    with down_col1:
        # Generate target formatted Excel file with formulas, formats, and columns
        xlsx_bytes = export_to_target_excel(filtered_df)
        st.download_button(
            label="📥 Download Full Target Analysis (Excel .xlsx)",
            data=xlsx_bytes,
            file_name=f"amazon_wholesale_analysis_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            help="Generates an Excel workbook with formatting, headers, formulas, and columns including Customer Reviews, About this item, and Wholesaller Company Name.",
        )

    with down_col2:
        csv_data = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📄 Download Analysis Report (CSV)",
            data=csv_data,
            file_name="amazon_wholesale_analysis_report.csv",
            mime="text/csv",
        )