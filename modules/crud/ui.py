"""
Module 4: Database CRUD Operations - Streamlit User Interface
============================================================
Purpose:
    Renders the interactive database viewer and management portal for Cloudflare D1.
    Enables users to:
    - Browse and search wholesale catalog items stored in Cloudflare D1
    - Filter leads dynamically by Category, Wholesaler, Profit, and ROI
    - View live KPI aggregate metrics across historical catalog uploads
    - Perform inline record updates (wholesale cost, notes, favorite toggle)
    - Delete obsolete or discontinued products
    - Manually insert new catalog items
    - Export queried database subsets in Target Excel or CSV format
"""

import datetime
import pandas as pd
import streamlit as st

from modules.uploader.config import CloudflareD1Config
from modules.uploader.d1_client import CloudflareD1Client
from modules.analyzer.excel_exporter import export_to_target_excel
from .models import ProductFilterCriteria
from .crud_service import D1CrudService


def render_crud_ui():
    """
    Renders the complete user interface for Module 4: Database CRUD Operations & Data Viewer.
    """
    st.header("🗄️ Module 4: Database CRUD Operations & Data Viewer")
    st.markdown(
        "Inspect, filter, edit, and manage wholesale catalog leads stored in your **Cloudflare D1 Database**. "
        "Filter by profitability, update product details, or export database subsets in Target format."
    )

    # --- SIDEBAR CONFIGURATION ---
    st.sidebar.subheader("🔐 Cloudflare D1 Credentials")
    env_config = CloudflareD1Config.from_env()

    account_id = st.sidebar.text_input(
        "Cloudflare Account ID",
        value=st.session_state.get("cf_account_id", env_config.account_id),
        type="password",
        key="crud_cf_account_id",
    )
    database_id = st.sidebar.text_input(
        "D1 Database ID",
        value=st.session_state.get("cf_database_id", env_config.database_id),
        type="password",
        key="crud_cf_database_id",
    )
    api_token = st.sidebar.text_input(
        "Cloudflare API Token",
        value=st.session_state.get("cf_api_token", env_config.api_token),
        type="password",
        key="crud_cf_api_token",
    )

    # Synchronize session state
    st.session_state["cf_account_id"] = account_id.strip()
    st.session_state["cf_database_id"] = database_id.strip()
    st.session_state["cf_api_token"] = api_token.strip()

    active_config = CloudflareD1Config(
        account_id=st.session_state["cf_account_id"],
        database_id=st.session_state["cf_database_id"],
        api_token=st.session_state["cf_api_token"],
    )
    client = CloudflareD1Client(active_config)
    crud_service = D1CrudService(client)

    if not active_config.is_valid():
        st.warning(
            "⚠️ Please configure your **Cloudflare Account ID**, **Database ID**, and **API Token** in the sidebar. "
            "You can also save them in Module 3 or your `.env` file."
        )
        return

    # --- 1. KPI SUMMARY DASHBOARD ---
    st.subheader("1. Live Cloudflare D1 Database Overview")
    with st.spinner("Fetching database statistics..."):
        stats = crud_service.get_database_statistics()

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Stored Products", f"{stats['total_products']:,}")
    k2.metric("Active Wholesalers", f"{stats['total_wholesalers']:,}")
    k3.metric("Profitable Leads", f"{stats['profitable_leads']:,}")
    k4.metric("Avg ROI on Stored Items", f"{stats['avg_roi_pct']:.1f}%")
    k5.metric("Top Profit Lead", f"${stats['top_profit']:.2f}")

    if stats["total_products"] == 0:
        st.info(
            "ℹ️ Your Cloudflare D1 database table is currently empty. "
            "Run Module 2 to analyze a supplier catalog and use Module 3 to upload the results!"
        )
        # Offer quick button to Module 2
        col_m2, _ = st.columns([1, 3])
        with col_m2:
            if st.button("📊 Go to Module 2 (Analyze Catalog)", type="primary"):
                st.session_state["active_module"] = "analyzer"
                st.rerun()

    # --- 2. SEARCH & FILTER TOOLBAR ---
    st.markdown("---")
    st.subheader("2. Filter & Search Database Leads")

    # Fetch distinct categories and wholesalers for dynamic dropdowns
    categories = ["All Categories"] + crud_service.get_distinct_categories()
    wholesalers = ["All Wholesalers"] + crud_service.get_distinct_wholesalers()

    f_row1_col1, f_row1_col2, f_row1_col3, f_row1_col4 = st.columns(4)
    with f_row1_col1:
        keyword = st.text_input("🔍 Search Keyword", placeholder="ASIN, Title, Brand, UPC...", key="crud_kw_input")
    with f_row1_col2:
        selected_cat = st.selectbox("Category", categories, key="crud_cat_dropdown")
    with f_row1_col3:
        selected_ws = st.selectbox("Wholesaler", wholesalers, key="crud_ws_dropdown")
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
            key="crud_sort_by",
        )

    f_row2_col1, f_row2_col2, f_row2_col3, f_row2_col4 = st.columns(4)
    with f_row2_col1:
        min_profit = st.number_input("Minimum Net Profit ($)", value=0.0, step=1.0, key="crud_min_profit_input")
    with f_row2_col2:
        min_roi = st.slider("Minimum ROI (%)", min_value=-50, max_value=150, value=0, step=5, key="crud_min_roi_input")
    with f_row2_col3:
        only_prof = st.checkbox("Only Profitable (Profit > $0)", value=False, key="crud_only_prof_chk")
        only_fav = st.checkbox("Only Favorites (⭐)", value=False, key="crud_only_fav_chk")
    with f_row2_col4:
        sort_asc = st.radio("Sort Order", ["Descending (High to Low)", "Ascending (Low to High)"], index=0) == "Ascending (Low to High)"
        page_size = st.selectbox("Page Size", [25, 50, 100], index=1, key="crud_page_size")

    # Current Page Tracking
    if "crud_current_page" not in st.session_state:
        st.session_state["crud_current_page"] = 1

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
        page=st.session_state["crud_current_page"],
        page_size=page_size,
    )

    # --- 3. FETCH & DISPLAY DATA ---
    with st.spinner("Querying Cloudflare D1..."):
        query_result = crud_service.fetch_products(criteria)

    items = query_result.items
    total_count = query_result.total_count
    total_pages = query_result.total_pages

    st.markdown(f"**Found {total_count} matching products** (Page {criteria.page} of {total_pages}):")

    if not items:
        st.info("No products found matching the current search & filter criteria.")
    else:
        # Build DataFrame for display
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

        # Pagination controls
        p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
        with p_col1:
            if st.button("⬅️ Previous Page", disabled=(criteria.page <= 1), key="prev_page_btn"):
                st.session_state["crud_current_page"] = max(1, criteria.page - 1)
                st.rerun()
        with p_col2:
            st.markdown(
                f"<div style='text-align: center; padding-top: 8px;'>Page <b>{criteria.page}</b> of <b>{total_pages}</b> ({total_count} total items)</div>",
                unsafe_allow_html=True,
            )
        with p_col3:
            if st.button("Next Page ➡️", disabled=(criteria.page >= total_pages), key="next_page_btn"):
                st.session_state["crud_current_page"] = min(total_pages, criteria.page + 1)
                st.rerun()

    # --- 4. CRUD MANAGEMENT OPERATIONS ---
    st.markdown("---")
    st.subheader("3. Product Management & Actions")

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
        st.markdown("#### Edit Wholesale Lead")
        st.caption("Update supplier cost, sell price, notes, or toggle favorite status. Unit economics recalculate automatically.")
        
        edit_asin = st.text_input("Enter ASIN to Edit", placeholder="e.g. B0BDHWDR12", key="crud_edit_asin_input")
        if edit_asin:
            prod = crud_service.get_product_by_asin(edit_asin)
            if prod:
                st.success(f"Loaded `{prod.asin}`: {prod.title or 'Product'}")
                e_col1, e_col2, e_col3 = st.columns(3)
                with e_col1:
                    new_cost = st.number_input("Wholesale Cost ($)", value=float(prod.cost or 0.0), step=1.0, key="edit_cost_val")
                with e_col2:
                    new_sell = st.number_input("Sell Price ($)", value=float(prod.sell_price or 0.0), step=1.0, key="edit_sell_val")
                with e_col3:
                    is_fav = st.checkbox("Mark as Favorite (⭐)", value=prod.favorite, key="edit_fav_val")

                new_notes = st.text_area("Custom Supplier Notes", value=prod.custom_notes or "", key="edit_notes_val")

                if st.button("💾 Save Changes to Cloudflare D1", type="primary", key="save_edit_btn"):
                    with st.spinner("Updating Cloudflare D1 record..."):
                        ok, msg = crud_service.update_product(
                            asin=prod.asin,
                            wholesaler=prod.wholesaler_company_name,
                            updates={
                                "cost": new_cost,
                                "sell_price": new_sell,
                                "favorite": 1 if is_fav else 0,
                                "custom_notes": new_notes,
                            },
                        )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.info(f"Product {edit_asin} not found in database.")

    # 2. Inspect Product
    with tab_inspect:
        st.markdown("#### Product Inspector & High-Resolution Images")
        inspect_asin = st.text_input("Enter ASIN to Inspect", placeholder="e.g. B0BDHWDR12", key="inspect_asin_input")
        if inspect_asin:
            item = crud_service.get_product_by_asin(inspect_asin)
            if item:
                st.markdown(f"### {item.title or 'Product'}")
                st.markdown(f"**ASIN**: `{item.asin}` | **UPC/Product ID**: `{item.product_id}` | **Brand**: `{item.brand}` | **Supplier**: `{item.wholesaler_company_name}`")
                
                # Financials Row
                i1, i2, i3, i4, i5 = st.columns(5)
                i1.metric("Wholesale Cost", f"${item.cost:.2f}" if item.cost else "N/A")
                i2.metric("Sell Price", f"${item.sell_price:.2f}" if item.sell_price else "N/A")
                i3.metric("Net Profit", f"${item.profit:.2f}" if item.profit else "N/A")
                i4.metric("ROI", f"{item.roi_pct:.1f}%" if item.roi_pct else "N/A")
                i5.metric("Est Monthly Sales", f"{item.current_est_sales:,}" if item.current_est_sales else "N/A")

                # Bullet points
                if item.about_this_item:
                    st.markdown("**About This Item:**")
                    st.text(item.about_this_item)

                # Images
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
                            st.image(img_url, caption=f"Image {idx+1}", use_column_width=True)

                # External Links
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

    # 3. Delete Product
    with tab_delete:
        st.markdown("#### Delete Product Record")
        st.caption("Permanently delete a product from your Cloudflare D1 database.")
        del_asin = st.text_input("ASIN to Delete", placeholder="e.g. B0BDHWDR12", key="del_asin_input")
        if del_asin:
            confirm = st.checkbox(f"⚠️ I confirm I want to permanently delete product `{del_asin}` from Cloudflare D1.", key="confirm_del_chk")
            if st.button("🗑️ Delete from Cloudflare D1", type="secondary", disabled=not confirm, key="execute_delete_btn"):
                with st.spinner("Deleting from Cloudflare D1..."):
                    ok, msg = crud_service.delete_product(del_asin)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # 4. Add Product
    with tab_create:
        st.markdown("#### Manually Insert Product Record")
        st.caption("Add a custom wholesale lead directly into Cloudflare D1.")
        c_col1, c_col2 = st.columns(2)
        with c_col1:
            add_asin = st.text_input("Product ASIN*", placeholder="B0...", key="add_asin_input")
            add_ws = st.text_input("Wholesaler Company Name*", value=st.session_state.get("wholesaler_company_name", "Direct Supplier"), key="add_ws_input")
            add_cost = st.number_input("Wholesale Cost ($)*", value=10.0, step=1.0, key="add_cost_input")
            add_sell = st.number_input("Sell Price ($)*", value=25.0, step=1.0, key="add_sell_input")
        with c_col2:
            add_title = st.text_input("Product Title", placeholder="Sample Title", key="add_title_input")
            add_brand = st.text_input("Brand", placeholder="Brand Name", key="add_brand_input")
            add_cat = st.text_input("Category", value="Beauty & Personal Care", key="add_cat_input")
            add_upc = st.text_input("Product ID (UPC)", placeholder="012345678901", key="add_upc_input")

        if st.button("➕ Insert into Cloudflare D1", type="primary", key="execute_insert_btn"):
            if not add_asin or not add_ws:
                st.warning("ASIN and Wholesaler Company Name are required.")
            else:
                with st.spinner("Inserting into Cloudflare D1..."):
                    ok, msg = crud_service.create_product({
                        "asin": add_asin,
                        "wholesaler_company_name": add_ws,
                        "title": add_title,
                        "brand": add_brand,
                        "category": add_cat,
                        "product_id": add_upc,
                        "cost": add_cost,
                        "sell_price": add_sell,
                        "last_run": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # 5. Export Stored Records
    with tab_export:
        st.markdown("#### Export Stored Records from Cloudflare D1")
        st.caption("Download all matching products from your database query in Target Excel (.xlsx) or CSV format.")

        if items:
            export_df = pd.DataFrame([p.to_dict() for p in items])
            exp_col1, exp_col2 = st.columns(2)

            with exp_col1:
                # Target Excel export
                xlsx_bytes = export_to_target_excel(export_df)
                st.download_button(
                    label="📥 Download Database Leads (Excel .xlsx)",
                    data=xlsx_bytes,
                    file_name=f"d1_wholesale_leads_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="export_db_xlsx_btn",
                )

            with exp_col2:
                csv_bytes = export_df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📄 Download Database Leads (CSV)",
                    data=csv_bytes,
                    file_name="d1_wholesale_leads_report.csv",
                    mime="text/csv",
                    key="export_db_csv_btn",
                )
        else:
            st.info("No items to export.")
