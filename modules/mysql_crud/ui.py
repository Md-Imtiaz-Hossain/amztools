"""
Module 6: Remote MySQL Database CRUD Operations - Streamlit User Interface
==========================================================================
Purpose:
    Renders the interactive database viewer and management portal for Remote MySQL (e.g. Hostinger).
    Enables users to:
    - Browse and search wholesale catalog items stored in Remote MySQL
    - Filter leads dynamically by Category, Wholesaler, Profit, and ROI
    - View live KPI aggregate metrics across historical catalog uploads
    - Perform inline record updates (wholesale cost, sell price, notes, favorite toggle)
    - Inspect full product details and high-resolution product images
    - Delete obsolete or discontinued products
    - Manually insert new catalog items
    - Export queried database subsets in Target Excel (.xlsx) or CSV format
"""

import datetime
import time
import pandas as pd
import streamlit as st

from modules.mysql_uploader.config import MySQLDatabaseConfig
from modules.mysql_uploader.mysql_client import MySQLRemoteClient
from modules.analyzer.excel_exporter import export_to_target_excel
from modules.crud.models import ProductFilterCriteria
from .crud_service import MySQLCrudService

METADATA_CACHE_TTL_SEC = 300  # 5 minutes cache for KPI stats and distinct dropdowns


def _invalidate_mysql_crud_cache():
    """Clear cached MySQL statistics, dropdowns, and count signatures after a DB write."""
    for k in (
        "mysql_crud_metadata_cache",
        "mysql_crud_last_filter_sig",
        "mysql_crud_cached_total_count",
        "mysql_crud_cached_edit_prod",
        "mysql_crud_cached_inspect_prod",
    ):
        st.session_state.pop(k, None)


def render_mysql_crud_ui():
    """
    Renders the complete user interface for Module 6: MySQL Database CRUD Operations & Data Viewer.
    """
    st.header("🗄️ Module 6: MySQL Remote Database CRUD & Viewer")
    st.markdown("**Hostinger / Remote MySQL Database Explorer & Lead Manager**")

    # --- SIDEBAR CONFIGURATION ---
    st.sidebar.subheader("🔐 MySQL Remote DB Credentials")
    env_config = MySQLDatabaseConfig.from_env()

    mysql_host = st.sidebar.text_input(
        "MySQL Host Address",
        value=st.session_state.get("mysql_host", env_config.host),
        placeholder="srv1570.hstgr.io or 82.197.82.58",
        key="mysql_crud_host_input",
    )
    mysql_port = st.sidebar.number_input(
        "MySQL Port",
        min_value=1,
        max_value=65535,
        value=int(st.session_state.get("mysql_port", env_config.port or 3306)),
        step=1,
        key="mysql_crud_port_input",
    )
    mysql_database = st.sidebar.text_input(
        "Database Name",
        value=st.session_state.get("mysql_database", env_config.database),
        placeholder="u742113797_re_D2AKZzTX",
        key="mysql_crud_db_input",
    )
    mysql_user = st.sidebar.text_input(
        "User Name",
        value=st.session_state.get("mysql_user", env_config.user),
        placeholder="u742113797_re_D2AKZzTX",
        key="mysql_crud_user_input",
    )
    mysql_password = st.sidebar.text_input(
        "Password",
        value=st.session_state.get("mysql_password", env_config.password),
        type="password",
        key="mysql_crud_password_input",
    )

    # Synchronize session state
    st.session_state["mysql_host"] = mysql_host.strip()
    st.session_state["mysql_port"] = int(mysql_port)
    st.session_state["mysql_database"] = mysql_database.strip()
    st.session_state["mysql_user"] = mysql_user.strip()
    st.session_state["mysql_password"] = mysql_password.strip()

    active_config = MySQLDatabaseConfig(
        host=st.session_state["mysql_host"],
        port=st.session_state["mysql_port"],
        database=st.session_state["mysql_database"],
        user=st.session_state["mysql_user"],
        password=st.session_state["mysql_password"],
    )
    client = MySQLRemoteClient(active_config)
    crud_service = MySQLCrudService(client)

    if st.sidebar.button("🧪 Test MySQL Connection", key="mysql_crud_test_conn_btn", use_container_width=True):
        if not active_config.is_valid():
            st.sidebar.warning("Please provide Host, Database Name, User Name, and Password.")
        else:
            with st.sidebar.spinner("Testing MySQL connection..."):
                ok, msg = client.test_connection()
            if ok:
                st.sidebar.success(msg)
            else:
                st.sidebar.error(msg)

    if not active_config.is_valid():
        st.warning(
            "⚠️ Please configure your **MySQL Host Address**, **Database Name**, **User Name**, and **Password** in the sidebar."
        )
        return

    # --- 1. KPI SUMMARY DASHBOARD ---
    hdr_col1, hdr_col2 = st.columns([4, 1])
    with hdr_col1:
        st.subheader("1. Live Remote MySQL Database Overview")
    with hdr_col2:
        if st.button("🔄 Refresh Stats", key="mysql_crud_refresh_stats_btn", use_container_width=True):
            _invalidate_mysql_crud_cache()

    db_cache_key = f"{active_config.host}:{active_config.port}:{active_config.database}"
    meta_cache = st.session_state.get("mysql_crud_metadata_cache")
    now_ts = time.time()

    if (
        not meta_cache
        or meta_cache.get("db_key") != db_cache_key
        or (now_ts - meta_cache.get("ts", 0)) > METADATA_CACHE_TTL_SEC
    ):
        with st.spinner("Fetching Remote MySQL database statistics..."):
            client.init_database_schema()
            stats = crud_service.get_database_statistics()
            distinct_cats = crud_service.get_distinct_categories()
            distinct_ws = crud_service.get_distinct_wholesalers()
        meta_cache = {
            "db_key": db_cache_key,
            "ts": now_ts,
            "stats": stats,
            "categories": distinct_cats,
            "wholesalers": distinct_ws,
        }
        st.session_state["mysql_crud_metadata_cache"] = meta_cache
    else:
        stats = meta_cache["stats"]
        distinct_cats = meta_cache["categories"]
        distinct_ws = meta_cache["wholesalers"]

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Stored Products", f"{stats['total_products']:,}")
    k2.metric("Active Wholesalers", f"{stats['total_wholesalers']:,}")
    k3.metric("Profitable Leads", f"{stats['profitable_leads']:,}")
    k4.metric("Avg ROI on Stored Items", f"{stats['avg_roi_pct']:.1f}%")
    k5.metric("Top Profit Lead", f"${stats['top_profit']:.2f}")

    if stats["total_products"] == 0:
        st.info(
            "ℹ️ Your Remote MySQL `wholesale_products` table is currently empty. "
            "Run Module 2 to analyze a supplier catalog and use Module 5 to upload the results!"
        )
        col_m2, col_m5, _ = st.columns([1.2, 1.2, 2])
        with col_m2:
            if st.button("📊 Go to Module 2 (Analyze Catalog)", type="primary", key="mysql_crud_goto_m2"):
                st.session_state["active_module"] = "analyzer"
                st.rerun()
        with col_m5:
            if st.button("🐬 Go to Module 5 (MySQL Uploader)", type="secondary", key="mysql_crud_goto_m5"):
                st.session_state["active_module"] = "mysql_uploader"
                st.rerun()

    # --- 2. SEARCH & FILTER TOOLBAR ---
    st.markdown("---")
    st.subheader("2. Filter & Search MySQL Database Leads")

    categories = ["All Categories"] + distinct_cats
    wholesalers = ["All Wholesalers"] + distinct_ws

    f_row1_col1, f_row1_col2, f_row1_col3, f_row1_col4 = st.columns(4)
    with f_row1_col1:
        keyword = st.text_input(
            "🔍 Search Keyword",
            placeholder="ASIN, Title, Brand, UPC...",
            key="mysql_crud_kw_input",
        )
    with f_row1_col2:
        selected_cat = st.selectbox("Category", categories, key="mysql_crud_cat_dropdown")
    with f_row1_col3:
        selected_ws = st.selectbox("Wholesaler", wholesalers, key="mysql_crud_ws_dropdown")
    with f_row1_col4:
        sort_by = st.selectbox(
            "Sort By",
            options=["profit", "roi_pct", "sales_rank", "cost", "sell_price", "last_run"],
            format_func=lambda s: {
                "profit": "Profit ($)",
                "roi_pct": "ROI (%)",
                "sales_rank": "Sales Rank (BSR)",
                "cost": "Cost ($)",
                "sell_price": "Sell Price ($)",
                "last_run": "Last Run Date",
            }.get(s, s),
            key="mysql_crud_sort_by",
        )

    f_row2_col1, f_row2_col2, f_row2_col3, f_row2_col4 = st.columns(4)
    with f_row2_col1:
        min_profit = st.number_input(
            "Minimum Net Profit ($)",
            value=0.0,
            step=1.0,
            key="mysql_crud_min_profit_input",
        )
    with f_row2_col2:
        min_roi = st.slider(
            "Minimum ROI (%)",
            min_value=-50,
            max_value=150,
            value=0,
            step=5,
            key="mysql_crud_min_roi_input",
        )
    with f_row2_col3:
        only_prof = st.checkbox("Only Profitable (Profit > $0)", value=False, key="mysql_crud_only_prof_chk")
        only_fav = st.checkbox("Only Favorites (⭐)", value=False, key="mysql_crud_only_fav_chk")
    with f_row2_col4:
        sort_asc = (
            st.radio(
                "Sort Order",
                ["Descending (High to Low)", "Ascending (Low to High)"],
                index=0,
                key="mysql_crud_sort_order",
            )
            == "Ascending (Low to High)"
        )
        page_size = st.selectbox("Page Size", [25, 50, 100], index=1, key="mysql_crud_page_size")

    if "mysql_crud_current_page" not in st.session_state:
        st.session_state["mysql_crud_current_page"] = 1

    filter_sig = (
        db_cache_key,
        (keyword or "").strip(),
        selected_cat,
        selected_ws,
        float(min_profit or 0.0),
        float(min_roi or 0.0),
        bool(only_prof),
        bool(only_fav),
    )
    if st.session_state.get("mysql_crud_last_filter_sig") != filter_sig:
        st.session_state["mysql_crud_current_page"] = 1
        st.session_state["mysql_crud_last_filter_sig"] = filter_sig
        st.session_state["mysql_crud_cached_total_count"] = None

    criteria = ProductFilterCriteria(
        keyword=keyword,
        category=selected_cat,
        wholesaler=selected_ws,
        min_profit=min_profit,
        min_roi=min_roi,
        only_profitable=only_prof,
        only_favorites=only_fav,
        sort_by=sort_by,
        sort_ascending=sort_asc,
        page=st.session_state["mysql_crud_current_page"],
        page_size=page_size,
    )

    # --- 3. FETCH & DISPLAY DATA ---
    known_total = st.session_state.get("mysql_crud_cached_total_count")
    try:
        with st.spinner("Querying Remote MySQL Database..."):
            query_result = crud_service.fetch_products(criteria, known_total_count=known_total)
        st.session_state["mysql_crud_cached_total_count"] = query_result.total_count
    except Exception as query_err:
        st.error(f"MySQL query error: {query_err}")
        return

    items = query_result.items
    total_count = query_result.total_count
    total_pages = query_result.total_pages

    st.markdown(f"**Found {total_count:,} matching products** (Page {criteria.page} of {total_pages}):")

    if not items:
        st.info("No products found matching the current search & filter criteria.")
    else:
        display_rows = [p.to_display_row() for p in items]
        view_df = pd.DataFrame(display_rows)

        st.dataframe(
            view_df,
            column_config={
                "Cost": st.column_config.NumberColumn(format="$%.2f"),
                "Sell Price": st.column_config.NumberColumn(format="$%.2f"),
                "Referral Fee": st.column_config.NumberColumn(format="$%.2f"),
                "FBA Pick & Pack Fee ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Profit ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Margin (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "ROI (%)": st.column_config.NumberColumn(format="%.2f%%"),
                "Current Est Sales": st.column_config.NumberColumn(format="%d"),
                "Estimated Monthly Revenue ($)": st.column_config.NumberColumn(format="$%.2f"),
                "Sales Rank": st.column_config.NumberColumn(format="%d"),
                "Average Rating": st.column_config.NumberColumn(format="%.1f ⭐"),
                "Total Review Count": st.column_config.NumberColumn(format="%d"),
            },
            use_container_width=True,
        )

        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        with p_col1:
            if st.button("⬅️ Previous Page", disabled=(criteria.page <= 1), key="mysql_prev_page_btn"):
                st.session_state["mysql_crud_current_page"] = max(1, criteria.page - 1)
                st.rerun()
        with p_col2:
            st.markdown(
                f"<div style='text-align: center; padding-top: 8px;'>Page <b>{criteria.page}</b> of <b>{total_pages}</b> ({total_count:,} total items)</div>",
                unsafe_allow_html=True,
            )
        with p_col3:
            if st.button("Next Page ➡️", disabled=(criteria.page >= total_pages), key="mysql_next_page_btn"):
                st.session_state["mysql_crud_current_page"] = min(total_pages, criteria.page + 1)
                st.rerun()

    # --- 4. CRUD MANAGEMENT OPERATIONS ---
    st.markdown("---")
    st.subheader("3. Product Management & Actions (Remote MySQL)")

    tab_edit, tab_inspect, tab_delete, tab_create, tab_export = st.tabs(
        [
            "✏️ Edit Product",
            "🔍 Product Details & Media",
            "🗑️ Delete Product",
            "➕ Add New Lead",
            "📥 Export Database",
        ]
    )

    # 1. Edit Product
    with tab_edit:
        st.markdown("#### Edit Wholesale Lead in MySQL")
        st.caption(
            "Update supplier cost, sell price, notes, or toggle favorite status. Unit economics recalculate automatically."
        )

        edit_asin = st.text_input("Enter ASIN to Edit", placeholder="e.g. B0BDHWDR12", key="mysql_crud_edit_asin_input")
        if edit_asin:
            clean_edit_asin = edit_asin.strip().upper()
            cached_edit = st.session_state.get("mysql_crud_cached_edit_prod")
            if cached_edit and cached_edit.get("asin") == clean_edit_asin:
                prod = cached_edit.get("model")
            else:
                prod = crud_service.get_product_by_asin(clean_edit_asin)
                st.session_state["mysql_crud_cached_edit_prod"] = {"asin": clean_edit_asin, "model": prod}
            if prod:
                st.success(f"Loaded `{prod.asin}`: {prod.title or 'Product'}")
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1:
                    new_cost = st.number_input(
                        "Wholesale Cost ($)",
                        value=float(prod.cost or 0.0),
                        step=1.0,
                        key="mysql_edit_cost_val",
                    )
                with e_col2:
                    new_sell = st.number_input(
                        "Sell Price ($)",
                        value=float(prod.sell_price or 0.0),
                        step=1.0,
                        key="mysql_edit_sell_val",
                    )
                with e_col3:
                    is_fav = st.checkbox("Mark as Favorite (⭐)", value=prod.favorite, key="mysql_edit_fav_val")

                new_notes = st.text_area(
                    "Custom Supplier Notes",
                    value=prod.custom_notes or "",
                    key="mysql_edit_notes_val",
                )

                if st.button("💾 Save Changes to Remote MySQL", type="primary", key="mysql_save_edit_btn"):
                    with st.spinner("Updating Remote MySQL record..."):
                        ok, msg = crud_service.update_product(
                            asin=prod.asin,
                            wholesaler=prod.wholesaler_company_name,
                            updates={
                                "cost": new_cost,
                                "sell_price": new_sell,
                                "favorite": 1 if is_fav else 0,
                                "custom_notes": new_notes,
                            },
                            current_product=prod,
                        )
                    if ok:
                        _invalidate_mysql_crud_cache()
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.info(f"Product {edit_asin} not found in MySQL database.")

    # 2. Inspect Product
    with tab_inspect:
        st.markdown("#### Product Inspector & High-Resolution Images")
        inspect_asin = st.text_input(
            "Enter ASIN to Inspect",
            placeholder="e.g. B0BDHWDR12",
            key="mysql_inspect_asin_input",
        )
        if inspect_asin:
            clean_inspect_asin = inspect_asin.strip().upper()
            cached_inspect = st.session_state.get("mysql_crud_cached_inspect_prod")
            if cached_inspect and cached_inspect.get("asin") == clean_inspect_asin:
                item = cached_inspect.get("model")
            else:
                item = crud_service.get_product_by_asin(clean_inspect_asin)
                st.session_state["mysql_crud_cached_inspect_prod"] = {"asin": clean_inspect_asin, "model": item}
            if item:
                st.markdown(f"### {item.title or 'Product'}")
                st.markdown(
                    f"**ASIN**: `{item.asin}` | **UPC/Product ID**: `{item.product_id}` | "
                    f"**Brand**: `{item.brand}` | **Supplier**: `{item.wholesaler_company_name}` | "
                    f"**Software**: `{item.analyzing_software_name or 'InternalAMZ'}`"
                )

                i1, i2, i3, i4, i5 = st.columns(5)
                i1.metric("Wholesale Cost", f"${item.cost:.2f}" if item.cost else "N/A")
                i2.metric("Sell Price", f"${item.sell_price:.2f}" if item.sell_price else "N/A")
                i3.metric("Net Profit", f"${item.profit:.2f}" if item.profit else "N/A")
                i4.metric("ROI", f"{item.roi_pct:.1f}%" if item.roi_pct else "N/A")
                i5.metric("Est Monthly Sales", f"{item.current_est_sales:,}" if item.current_est_sales else "N/A")

                if item.about_this_item:
                    st.markdown("**About This Item:**")
                    st.text(item.about_this_item)

                img_links = [
                    item.product_image_link_1,
                    item.product_image_link_2,
                    item.product_image_link_3,
                    item.product_image_link_4,
                    item.product_image_link_5,
                ]
                valid_imgs = [img for img in img_links if img]
                if valid_imgs:
                    st.markdown("**Product Images:**")
                    img_cols = st.columns(min(5, len(valid_imgs)))
                    for idx, img_url in enumerate(valid_imgs[:5]):
                        with img_cols[idx]:
                            st.image(img_url, caption=f"Image {idx + 1}", use_column_width=True)

                st.markdown("**External Research Links:**")
                l_col1, l_col2, l_col3 = st.columns(3)
                with l_col1:
                    if item.amazon_link:
                        st.markdown(f"🔗 [Amazon Listing]({item.amazon_link})")
                with l_col2:
                    if item.keepa:
                        st.markdown(f"📈 [Keepa Chart]({item.keepa})")
                with l_col3:
                    if item.camelcc:
                        st.markdown(f"🐪 [CamelCamelCamel]({item.camelcc})")
            else:
                st.info(f"Product {inspect_asin} not found in MySQL database.")

    # 3. Delete Product
    with tab_delete:
        st.markdown("#### Delete Product Record from MySQL")
        st.caption("Permanently delete a product from your Remote MySQL database.")
        del_asin = st.text_input("ASIN to Delete", placeholder="e.g. B0BDHWDR12", key="mysql_del_asin_input")
        if del_asin:
            confirm = st.checkbox(
                f"⚠️ I confirm I want to permanently delete product `{del_asin}` from Remote MySQL.",
                key="mysql_confirm_del_chk",
            )
            if st.button(
                "🗑️ Delete from Remote MySQL",
                type="secondary",
                disabled=not confirm,
                key="mysql_execute_delete_btn",
            ):
                with st.spinner("Deleting from Remote MySQL..."):
                    ok, msg = crud_service.delete_product(del_asin)
                if ok:
                    _invalidate_mysql_crud_cache()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # 4. Add Product
    with tab_create:
        st.markdown("#### Manually Insert Product Record into MySQL")
        st.caption("Add a custom wholesale lead directly into your Remote MySQL database.")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            add_asin = st.text_input("Product ASIN*", placeholder="B0...", key="mysql_add_asin_input")
            add_ws = st.text_input(
                "Wholesaler Company Name*",
                value=st.session_state.get("wholesaler_company_name", "Direct Supplier"),
                key="mysql_add_ws_input",
            )
            add_cost = st.number_input("Wholesale Cost ($)*", value=10.0, step=1.0, key="mysql_add_cost_input")
            add_sell = st.number_input("Sell Price ($)*", value=25.0, step=1.0, key="mysql_add_sell_input")
        with c_col2:
            add_title = st.text_input("Product Title", placeholder="Sample Title", key="mysql_add_title_input")
            add_brand = st.text_input("Brand", placeholder="Brand Name", key="mysql_add_brand_input")
            add_cat = st.text_input("Category", value="Beauty & Personal Care", key="mysql_add_cat_input")
            add_upc = st.text_input("Product ID (UPC)", placeholder="012345678901", key="mysql_add_upc_input")

        if st.button("➕ Insert into Remote MySQL", type="primary", key="mysql_execute_insert_btn"):
            if not add_asin or not add_ws:
                st.warning("ASIN and Wholesaler Company Name are required.")
            else:
                with st.spinner("Inserting into Remote MySQL..."):
                    ok, msg = crud_service.create_product(
                        {
                            "asin": add_asin,
                            "wholesaler_company_name": add_ws,
                            "title": add_title,
                            "brand": add_brand,
                            "category": add_cat,
                            "product_id": add_upc,
                            "cost": add_cost,
                            "sell_price": add_sell,
                            "analyzing_software_name": "InternalAMZ",
                            "last_run": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                if ok:
                    _invalidate_mysql_crud_cache()
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # 5. Export Stored Records
    with tab_export:
        st.markdown("#### Export Stored Records from Remote MySQL")
        st.caption("Download matching products from your MySQL database query in Target Excel (.xlsx) or CSV format.")

        if items:
            export_df = pd.DataFrame([p.to_dict() for p in items])
            if "Analyzing Software Name" not in export_df.columns:
                export_df["Analyzing Software Name"] = "InternalAMZ"
            else:
                export_df["Analyzing Software Name"] = (
                    export_df["Analyzing Software Name"].fillna("InternalAMZ").replace("", "InternalAMZ")
                )

            if st.button("📦 Prepare Export Files for Current Page", key="prepare_mysql_crud_export_btn"):
                st.session_state["mysql_crud_prepared_xlsx"] = export_to_target_excel(export_df)
                st.session_state["mysql_crud_prepared_csv"] = export_df.to_csv(index=False).encode("utf-8")

            if st.session_state.get("mysql_crud_prepared_xlsx"):
                exp_col1, exp_col2 = st.columns(2)
                with exp_col1:
                    st.download_button(
                        label="📥 Download MySQL Leads (Excel .xlsx)",
                        data=st.session_state["mysql_crud_prepared_xlsx"],
                        file_name=f"mysql_wholesale_leads_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="mysql_export_db_xlsx_btn",
                    )
                with exp_col2:
                    st.download_button(
                        label="📄 Download MySQL Leads (CSV)",
                        data=st.session_state["mysql_crud_prepared_csv"],
                        file_name="mysql_wholesale_leads_report.csv",
                        mime="text/csv",
                        key="mysql_export_db_csv_btn",
                    )
        else:
            st.info("No items to export.")
