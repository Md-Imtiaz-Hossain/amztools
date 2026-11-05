"""
Module 6: Remote MySQL Database CRUD Operations - CRUD Service Layer
====================================================================
Purpose:
    Executes business logic and dynamic parameterized SQL queries (`%s`)
    against a remote MySQL database (e.g., Hostinger MySQL) to deliver complete
    Create, Read, Update, and Delete capabilities.

Operations Provided:
    - READ (List): Query wholesale products with dynamic filtering, keyword search,
      sorting, and limit/offset pagination.
    - READ (Single): Retrieve full details for an individual product by ID or ASIN & Wholesaler.
    - CREATE: Manually insert a newly discovered wholesale lead or custom item.
    - UPDATE: Modify product attributes (e.g. toggle favorite, adjust supplier cost, update notes).
      Automatically recalculates profit, margin, and ROI when cost or sell price changes.
    - DELETE: Remove outdated, restricted, or discontinued products from MySQL.
    - ANALYTICS: Compute aggregate KPI metrics (total items, profitable count, average ROI, top profit).
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from modules.mysql_uploader.mysql_client import MySQLRemoteClient
from modules.analyzer.analytics import calculate_comprehensive_financials
from modules.crud.models import (
    PaginatedQueryResult,
    ProductFilterCriteria,
    WholesaleProductModel,
)

logger = logging.getLogger(__name__)

# Columns needed for table display & summary export (avoids transferring large LONGTEXT blobs on list queries)
DISPLAY_SQL_COLUMNS = (
    "id, asin, parent_asin, product_id, favorite, wholesaler_company_name, "
    "analyzing_software_name, brand, title, category, sales_rank, cost, sell_price, "
    "referral_fee, fba_pick_pack_fee, profit, margin_pct, roi_pct, current_est_sales, "
    "estimated_monthly_revenue, total_offers, average_rating, total_review_count, last_run"
)

VALID_SORT_COLUMNS = {
    "profit": "profit",
    "roi_pct": "roi_pct",
    "sales_rank": "sales_rank",
    "cost": "cost",
    "sell_price": "sell_price",
    "last_run": "last_run",
    "title": "title",
    "wholesaler_company_name": "wholesaler_company_name",
}


class MySQLCrudService:
    """
    Service layer providing CRUD operations over a Remote MySQL database.
    """

    def __init__(self, client: MySQLRemoteClient):
        self.client = client

    def _build_where_clause(self, criteria: ProductFilterCriteria) -> Tuple[str, List[Any]]:
        """
        Construct dynamic parameterized MySQL WHERE conditions using `%s` placeholders.
        """
        clauses = ["1=1"]
        params: List[Any] = []

        if criteria.keyword and criteria.keyword.strip():
            trimmed_kw = criteria.keyword.strip()
            if re.match(r"^B[0-9A-Z]{9}$", trimmed_kw, re.IGNORECASE):
                upper_asin = trimmed_kw.upper()
                clauses.append("(asin = %s OR parent_asin = %s)")
                params.extend([upper_asin, upper_asin])
            elif re.match(r"^\d{8,14}$", trimmed_kw):
                clauses.append("product_id = %s")
                params.append(trimmed_kw)
            else:
                kw = f"%{trimmed_kw}%"
                clauses.append(
                    "(asin LIKE %s OR product_id LIKE %s OR title LIKE %s OR brand LIKE %s OR wholesaler_company_name LIKE %s)"
                )
                params.extend([kw, kw, kw, kw, kw])

        if criteria.category and criteria.category not in ("All Categories", "All", ""):
            clauses.append("category = %s")
            params.append(criteria.category.strip())

        if criteria.wholesaler and criteria.wholesaler not in ("All Wholesalers", "All", ""):
            clauses.append("wholesaler_company_name = %s")
            params.append(criteria.wholesaler.strip())

        if criteria.only_profitable:
            clauses.append("profit > 0")

        if criteria.only_favorites:
            clauses.append("favorite = 1")

        if criteria.min_profit is not None and criteria.min_profit > 0:
            clauses.append("profit >= %s")
            params.append(float(criteria.min_profit))

        if criteria.min_roi is not None and criteria.min_roi > -50:
            val = float(criteria.min_roi)
            clauses.append("(roi_pct >= %s OR roi_pct >= %s)")
            params.extend([val, val / 100.0])

        where_sql = " AND ".join(clauses)
        return where_sql, params

    def fetch_products(
        self,
        criteria: ProductFilterCriteria,
        known_total_count: Optional[int] = None,
        select_all_columns: bool = False,
    ) -> PaginatedQueryResult:
        """
        Fetch a paginated list of wholesale products matching filter criteria from MySQL.
        """
        where_sql, params = self._build_where_clause(criteria)

        sort_col = VALID_SORT_COLUMNS.get(criteria.sort_by, "profit")
        sort_dir = "ASC" if criteria.sort_ascending else "DESC"

        limit = max(1, int(criteria.page_size))
        offset = max(0, (int(criteria.page) - 1) * limit)
        cols_sql = "*" if select_all_columns else DISPLAY_SQL_COLUMNS

        items_sql = (
            f"SELECT {cols_sql} FROM wholesale_products "
            f"WHERE {where_sql} "
            f"ORDER BY {sort_col} {sort_dir} "
            f"LIMIT %s OFFSET %s;"
        )
        query_params = list(params) + [limit, offset]
        res = self.client.execute_query(items_sql, query_params)
        rows = res.get("results", [])
        items = [WholesaleProductModel.from_d1_row(row) for row in rows]

        if known_total_count is not None and known_total_count >= 0:
            total_count = int(known_total_count)
        elif criteria.page == 1 and len(items) < limit:
            total_count = len(items)
        else:
            count_sql = f"SELECT COUNT(*) AS total_count FROM wholesale_products WHERE {where_sql};"
            count_res = self.client.execute_query(count_sql, list(params))
            total_count = len(items)
            if count_res.get("results"):
                total_count = int(count_res["results"][0].get("total_count", 0))

        return PaginatedQueryResult(
            items=items,
            total_count=total_count,
            page=criteria.page,
            page_size=limit,
        )

    def get_product_by_id(self, row_id: int) -> Optional[WholesaleProductModel]:
        """
        Fetch a single wholesale product record by its primary key ID.
        """
        sql = "SELECT * FROM wholesale_products WHERE id = %s LIMIT 1;"
        res = self.client.execute_query(sql, [int(row_id)])
        rows = res.get("results", [])
        if rows:
            return WholesaleProductModel.from_d1_row(rows[0])
        return None

    def get_product_by_asin(self, asin: str, wholesaler: Optional[str] = None) -> Optional[WholesaleProductModel]:
        """
        Fetch a single wholesale product record by ASIN and optional wholesaler.
        """
        clean_asin = asin.strip().upper()
        if wholesaler:
            sql = "SELECT * FROM wholesale_products WHERE asin = %s AND wholesaler_company_name = %s LIMIT 1;"
            params = [clean_asin, wholesaler.strip()]
        else:
            sql = "SELECT * FROM wholesale_products WHERE asin = %s LIMIT 1;"
            params = [clean_asin]

        res = self.client.execute_query(sql, params)
        rows = res.get("results", [])
        if rows:
            return WholesaleProductModel.from_d1_row(rows[0])
        return None

    def create_product(self, product_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Insert a single wholesale product into Remote MySQL.
        """
        asin = product_data.get("asin", "").strip().upper()
        wholesaler = product_data.get("wholesaler_company_name", "").strip()

        if not asin:
            return False, "ASIN is required."
        if not wholesaler:
            return False, "Wholesaler Company Name is required."

        product_data["asin"] = asin
        product_data["wholesaler_company_name"] = wholesaler
        if not product_data.get("analyzing_software_name"):
            product_data["analyzing_software_name"] = "InternalAMZ"

        cost = float(product_data.get("cost") or 0.0)
        sell_price = float(product_data.get("sell_price") or 0.0)
        if sell_price > 0 and cost > 0:
            fin = calculate_comprehensive_financials(
                cost=cost,
                sell_price=sell_price,
                category=product_data.get("category", "Beauty & Personal Care"),
            )
            product_data["profit"] = fin.get("Profit")
            product_data["margin_pct"] = fin.get("Margin")
            product_data["roi_pct"] = fin.get("ROI")
            product_data["referral_fee"] = fin.get("Referral Fee")
            product_data["fba_pick_pack_fee"] = fin.get("FBA Pick & Pack Fee ($)")

        columns = [c for c in product_data.keys() if c != "id"]
        placeholders = ", ".join(["%s"] * len(columns))
        col_str = ", ".join(columns)
        params = [product_data[c] for c in columns]

        sql = f"INSERT INTO wholesale_products ({col_str}) VALUES ({placeholders});"
        try:
            self.client.execute_query(sql, params)
            return True, f"Successfully created product {asin} in MySQL!"
        except Exception as e:
            return False, f"Failed creating product in MySQL: {e}"

    def update_product(
        self,
        asin: str,
        wholesaler: str,
        updates: Dict[str, Any],
        current_product: Optional[WholesaleProductModel] = None,
    ) -> Tuple[bool, str]:
        """
        Update specific fields of an existing product record in Remote MySQL.
        Automatically recalculates profitability metrics if cost or sell price changes.
        """
        clean_asin = asin.strip().upper()
        clean_ws = wholesaler.strip()

        if not updates:
            return False, "No fields specified for update."

        if "cost" in updates or "sell_price" in updates:
            current = current_product or self.get_product_by_asin(clean_asin, clean_ws)
            if not current:
                return False, f"Product {clean_asin} ({clean_ws}) not found in MySQL database."

            new_cost = updates.get("cost", current.cost)
            new_sell = updates.get("sell_price", current.sell_price)
            try:
                c_val = float(new_cost or 0.0)
                s_val = float(new_sell or 0.0)
                if s_val > 0:
                    fin = calculate_comprehensive_financials(
                        cost=c_val,
                        sell_price=s_val,
                        category=current.category or "Beauty & Personal Care",
                        weight_lb=current.package_weight_lb,
                        dimensions_str=current.package_dimensions or "",
                    )
                    updates["profit"] = fin["Profit"]
                    updates["margin_pct"] = fin["Margin"]
                    updates["roi_pct"] = fin["ROI"]
                    updates["referral_fee"] = fin["Referral Fee"]
                    updates["fba_pick_pack_fee"] = fin["FBA Pick & Pack Fee ($)"]
            except Exception as fin_err:
                logger.warning(f"MySQL financial recalculation warning: {fin_err}")

        set_clauses = []
        params = []
        for col, val in updates.items():
            if col in ("id", "asin", "wholesaler_company_name", "created_at"):
                continue
            set_clauses.append(f"{col} = %s")
            params.append(val)

        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        set_sql = ", ".join(set_clauses)
        sql = f"UPDATE wholesale_products SET {set_sql} WHERE asin = %s AND wholesaler_company_name = %s;"
        params.extend([clean_asin, clean_ws])

        try:
            self.client.execute_query(sql, params)
            return True, f"Successfully updated {clean_asin} in MySQL!"
        except Exception as e:
            return False, f"Failed updating product in MySQL: {e}"

    def toggle_favorite(self, asin: str, wholesaler: str, current_favorite: bool) -> Tuple[bool, str]:
        """
        Toggle the favorite star for a product in MySQL.
        """
        new_val = 0 if current_favorite else 1
        return self.update_product(asin, wholesaler, {"favorite": new_val})

    def delete_product(self, asin: str, wholesaler: Optional[str] = None) -> Tuple[bool, str]:
        """
        Remove a product record from Remote MySQL.
        """
        clean_asin = asin.strip().upper()
        if wholesaler:
            sql = "DELETE FROM wholesale_products WHERE asin = %s AND wholesaler_company_name = %s;"
            params = [clean_asin, wholesaler.strip()]
        else:
            sql = "DELETE FROM wholesale_products WHERE asin = %s;"
            params = [clean_asin]

        try:
            self.client.execute_query(sql, params)
            return True, f"Successfully deleted product {clean_asin} from MySQL database."
        except Exception as e:
            return False, f"Failed deleting product from MySQL: {e}"

    def get_database_statistics(self) -> Dict[str, Any]:
        """
        Query aggregate KPI statistics across all stored products in Remote MySQL.
        """
        sql = (
            "SELECT "
            "  COUNT(*) AS total_products, "
            "  COUNT(DISTINCT wholesaler_company_name) AS total_wholesalers, "
            "  SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) AS profitable_leads, "
            "  AVG(CASE WHEN roi_pct IS NOT NULL THEN roi_pct ELSE NULL END) AS avg_roi, "
            "  MAX(profit) AS top_profit "
            "FROM wholesale_products;"
        )
        try:
            res = self.client.execute_query(sql, [])
            rows = res.get("results", [])
            if rows:
                r = rows[0]
                avg_roi_raw = float(r.get("avg_roi") or 0.0)
                avg_roi_pct = avg_roi_raw * 100.0 if avg_roi_raw <= 1.0 else avg_roi_raw
                return {
                    "total_products": int(r.get("total_products") or 0),
                    "total_wholesalers": int(r.get("total_wholesalers") or 0),
                    "profitable_leads": int(r.get("profitable_leads") or 0),
                    "avg_roi_pct": round(avg_roi_pct, 1),
                    "top_profit": round(float(r.get("top_profit") or 0.0), 2),
                }
        except Exception as e:
            logger.error(f"Error fetching MySQL DB stats: {e}")

        return {
            "total_products": 0,
            "total_wholesalers": 0,
            "profitable_leads": 0,
            "avg_roi_pct": 0.0,
            "top_profit": 0.0,
        }

    def get_distinct_categories(self) -> List[str]:
        """
        Retrieve distinct categories present in Remote MySQL.
        """
        sql = "SELECT DISTINCT category FROM wholesale_products WHERE category IS NOT NULL AND category != '' ORDER BY category ASC;"
        try:
            res = self.client.execute_query(sql, [])
            return [row["category"] for row in res.get("results", []) if row.get("category")]
        except Exception:
            return []

    def get_distinct_wholesalers(self) -> List[str]:
        """
        Retrieve distinct wholesaler company names in Remote MySQL.
        """
        sql = "SELECT DISTINCT wholesaler_company_name FROM wholesale_products WHERE wholesaler_company_name IS NOT NULL AND wholesaler_company_name != '' ORDER BY wholesaler_company_name ASC;"
        try:
            res = self.client.execute_query(sql, [])
            return [
                row["wholesaler_company_name"]
                for row in res.get("results", [])
                if row.get("wholesaler_company_name")
            ]
        except Exception:
            return []
