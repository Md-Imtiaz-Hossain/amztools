"""
Module 3: Data Upload to Database - Cloudflare D1 HTTP Client
=============================================================
Purpose:
    Provides a robust HTTP client for executing SQL commands on Cloudflare D1
    using Cloudflare's public REST API v4.

Authentication:
    Bearer Token authorization using a Cloudflare API Token with D1 Edit permissions.

Endpoints:
    POST https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None

from .config import CloudflareD1Config

logger = logging.getLogger(__name__)


class CloudflareD1Client:
    """
    Cloudflare D1 REST API Client.

    Responsibilities:
    - Authenticates requests via Bearer Token.
    - Sends parameterized SQL statements to Cloudflare D1.
    - Supports single queries and batch query execution with retry backoff.
    - Uses persistent HTTP connection pooling for high-throughput uploads.
    - Handles HTTP errors, network timeouts, and JSON response decoding.
    """

    def __init__(self, config: CloudflareD1Config):
        """
        Initialize the D1 client with connection configuration.
        """
        self.config = config
        self._session = None

    def _get_session(self):
        """
        Get or initialize a persistent requests session with connection pooling.
        """
        if requests is None:
            return None
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _get_headers(self) -> Dict[str, str]:
        """
        Construct required HTTP headers for Cloudflare API.
        """
        token = self.config.api_token.strip()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connectivity to Cloudflare D1 by running a lightweight query (SELECT 1).

        Returns:
            Tuple[bool, str]: (Success boolean, Status message or error description).
        """
        if not self.config.is_valid():
            missing = []
            if not self.config.account_id:
                missing.append("Account ID")
            if not self.config.database_id:
                missing.append("Database ID (UUID)")
            if not self.config.api_token:
                missing.append("API Token")
            return False, f"Missing required credentials: {', '.join(missing)}."

        if requests is None:
            return False, "Python 'requests' library is not available in runtime."

        try:
            url = self.config.query_endpoint_url
            headers = self._get_headers()
            payload = {
                "sql": "SELECT 1 as ping, datetime('now') as server_time;",
                "params": [],
            }

            resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("success"):
                    return True, "✅ Successfully connected to Cloudflare D1 database!"
                else:
                    errors = data.get("errors", [])
                    err_msg = "; ".join([e.get("message", str(e)) for e in errors]) or "Unknown D1 error"
                    return False, f"D1 API returned error: {err_msg}"
            
            elif resp.status_code == 401 or resp.status_code == 403:
                return False, f"HTTP {resp.status_code}: Unauthorized. Please check that your API Token has 'D1 Edit' permissions."
            
            elif resp.status_code == 404:
                return False, f"HTTP 404: Database or Account not found. Verify your Account ID and Database UUID."
            
            else:
                try:
                    err_body = resp.json()
                    msg = err_body.get("errors", resp.text)
                except Exception:
                    msg = resp.text
                return False, f"HTTP {resp.status_code}: {msg}"

        except Exception as e:
            return False, f"Connection failed: {e}"

    def execute_query(self, sql: str, params: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute a single parameterized SQL statement on Cloudflare D1.

        Args:
            sql (str): SQL statement.
            params (Optional[List[Any]]): Positional parameters binding to '?' placeholders.

        Returns:
            Dict[str, Any]: Parsed response dictionary with 'success', 'results', and 'meta'.
        """
        if requests is None:
            raise RuntimeError("Python 'requests' library is not installed.")

        session = self._get_session() or requests
        url = self.config.query_endpoint_url
        headers = self._get_headers()
        payload = {
            "sql": sql,
            "params": params or [],
        }

        resp = session.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)
        data = resp.json()

        if not data.get("success"):
            errors = data.get("errors", [])
            err_msg = "; ".join([e.get("message", str(e)) for e in errors]) or resp.text
            raise RuntimeError(f"D1 Query Execution Failed: {err_msg}")

        # Extract result
        # Cloudflare D1 returns "result": [ { "results": [...], "success": true, "meta": {...} } ]
        result_list = data.get("result", [])
        if result_list and isinstance(result_list, list):
            first_res = result_list[0]
            return {
                "success": True,
                "results": first_res.get("results", []),
                "meta": first_res.get("meta", {}),
            }
        return {"success": True, "results": [], "meta": {}}

    def execute_batch(self, batch_payload: List[Dict[str, Any]], max_retries: int = 3) -> Dict[str, Any]:
        """
        Execute multiple SQL statements in batch against Cloudflare D1 with automatic retry backoff.

        Args:
            batch_payload (List[Dict[str, Any]]): List of query dicts, each with 'sql' and 'params'.
            max_retries (int): Number of retries for transient 429/5xx errors.

        Returns:
            Dict[str, Any]: Summary response with total changes and status.
        """
        if not batch_payload:
            return {"success": True, "total_changes": 0, "batch_count": 0}

        if requests is None:
            raise RuntimeError("Python 'requests' library is not installed.")

        session = self._get_session() or requests
        url = self.config.query_endpoint_url
        headers = self._get_headers()
        payload = {"batch": batch_payload}

        for attempt in range(max_retries):
            try:
                resp = session.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)

                # Handle rate limiting (HTTP 429)
                if resp.status_code == 429:
                    retry_after = 2 * (attempt + 1)
                    try:
                        retry_after = int(resp.headers.get("Retry-After", retry_after))
                    except Exception:
                        pass
                    logger.warning(f"D1 Rate limit (429). Retrying in {retry_after}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(retry_after)
                    continue

                # Handle transient 5xx server errors
                if resp.status_code in (500, 502, 503, 504):
                    backoff = 1.5 * (attempt + 1)
                    logger.warning(f"D1 HTTP {resp.status_code}. Retrying in {backoff}s (attempt {attempt+1}/{max_retries})...")
                    time.sleep(backoff)
                    continue

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("success"):
                        results = data.get("result", [])
                        total_changes = 0
                        for r in results:
                            meta = r.get("meta", {})
                            total_changes += meta.get("changes", 0)
                        return {
                            "success": True,
                            "total_changes": total_changes,
                            "batch_count": len(batch_payload),
                            "raw_result": results,
                        }
                    else:
                        break
                else:
                    break

            except (requests.Timeout, requests.ConnectionError) as conn_err:
                logger.warning(f"D1 network warning: {conn_err}. Retrying in {1.5*(attempt+1)}s...")
                time.sleep(1.5 * (attempt + 1))
            except Exception as e:
                logger.warning(f"D1 batch exception: {e}")
                break

        # Fallback to sequential execution if batch wrapper returned non-200 or failed
        logger.warning("Batch endpoint returned non-200 or error. Attempting fallback individual execution...")
        total_changes = 0
        for item in batch_payload:
            res = self.execute_query(item.get("sql", ""), item.get("params", []))
            total_changes += res.get("meta", {}).get("changes", 1)
        return {"success": True, "total_changes": total_changes, "batch_count": len(batch_payload)}


    def has_unique_asin_constraint(self) -> bool:
        """
        Detects whether the wholesale_products table has a UNIQUE constraint on (asin, wholesaler_company_name).
        """
        try:
            res = self.execute_query("PRAGMA index_list(wholesale_products);", [])
            indexes = res.get("results", [])
            for idx in indexes:
                is_unique = (idx.get("unique") == 1 or idx.get("unique") is True)
                origin = idx.get("origin", "")
                idx_name = idx.get("name", "")
                # Origin 'u' signifies an auto-generated unique constraint index
                if is_unique and origin == "u":
                    col_res = self.execute_query(f"PRAGMA index_info({idx_name});", [])
                    cols = [c.get("name") for c in col_res.get("results", [])]
                    if "asin" in cols:
                        return True
            return False
        except Exception as e:
            logger.warning(f"Error checking unique constraint on wholesale_products: {e}")
            return False

    def migrate_remove_unique_constraint(self) -> Tuple[bool, str]:
        """
        Safely migrates the wholesale_products table in Cloudflare D1 to drop
        the UNIQUE(asin, wholesaler_company_name) constraint, preserving all
        existing records while enabling multiple items with identical ASINs.
        """
        try:
            table_info = self.execute_query("PRAGMA table_info(wholesale_products);", [])
            cols_info = table_info.get("results", [])
            if not cols_info:
                return False, "Table wholesale_products does not exist or has no columns."

            col_names = [c["name"] for c in cols_info]
            col_defs = []
            for col in cols_info:
                c_name = col["name"]
                c_type = col.get("type", "TEXT")
                not_null = " NOT NULL" if col.get("notnull") else ""
                dflt_val = col.get("dflt_value")
                dflt = f" DEFAULT {dflt_val}" if dflt_val is not None else ""
                if col.get("pk"):
                    col_defs.append(f"{c_name} INTEGER PRIMARY KEY AUTOINCREMENT")
                else:
                    col_defs.append(f"{c_name} {c_type}{not_null}{dflt}")

            cols_def_str = ", ".join(col_defs)
            cols_str = ", ".join(col_names)

            migration_stmts = [
                f"CREATE TABLE wholesale_products_migration_temp ({cols_def_str});",
                f"INSERT INTO wholesale_products_migration_temp ({cols_str}) SELECT {cols_str} FROM wholesale_products;",
                "DROP TABLE wholesale_products;",
                "ALTER TABLE wholesale_products_migration_temp RENAME TO wholesale_products;",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_asin ON wholesale_products(asin);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_product_id ON wholesale_products(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_wholesaler ON wholesale_products(wholesaler_company_name);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_category ON wholesale_products(category);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_sales_rank ON wholesale_products(sales_rank);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_profit ON wholesale_products(profit);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_roi ON wholesale_products(roi_pct);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_last_run ON wholesale_products(last_run);",
                "CREATE INDEX IF NOT EXISTS idx_wholesale_analyzing_software ON wholesale_products(analyzing_software_name);",
            ]

            for s in migration_stmts:
                self.execute_query(s, [])

            return True, "✅ Successfully migrated table wholesale_products: UNIQUE constraint removed. All duplicate ASIN rows are now accepted!"
        except Exception as e:
            return False, f"Migration failed: {e}"

    def clear_table(self, wholesaler_company_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Clears records from wholesale_products table.
        If wholesaler_company_name is provided, clears only records for that wholesaler.
        Otherwise, wipes the entire wholesale_products table.
        """
        try:
            if wholesaler_company_name and wholesaler_company_name.strip():
                ws = wholesaler_company_name.strip()
                self.execute_query("DELETE FROM wholesale_products WHERE wholesaler_company_name = ?;", [ws])
                return True, f"✅ Successfully cleared previous records for wholesaler '{ws}'."
            else:
                self.execute_query("DELETE FROM wholesale_products;", [])
                try:
                    self.execute_query("DELETE FROM sqlite_sequence WHERE name = 'wholesale_products';", [])
                except Exception:
                    pass
                return True, "✅ Successfully cleared all records from wholesale_products table."
        except Exception as e:
            return False, f"Failed clearing table: {e}"

    def init_database_schema(self, schema_sql_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Execute the DDL schema to ensure the wholesale_products table and indexes exist.

        Args:
            schema_sql_path (Optional[str]): Path to schema.sql file.

        Returns:
            Tuple[bool, str]: (Success boolean, Status description).
        """
        if not schema_sql_path:
            schema_sql_path = os.path.join(os.path.dirname(__file__), "schema.sql")

        if not os.path.exists(schema_sql_path):
            return False, f"Schema file not found at {schema_sql_path}"

        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        # Split SQL into individual statements by semicolon
        # Remove comments and empty lines
        raw_statements = sql_content.split(";")
        statements_to_run = []
        for stmt in raw_statements:
            # Strip single line comments
            lines = [l for l in stmt.splitlines() if not l.strip().startswith("--")]
            cleaned = " ".join(lines).strip()
            if cleaned:
                statements_to_run.append(cleaned)

        if not statements_to_run:
            return False, "No valid SQL statements found in schema.sql."

        # Execute each DDL statement sequentially
        executed_count = 0
        try:
            for s in statements_to_run:
                self.execute_query(s, [])
                executed_count += 1

            # Migration fallback for existing tables: add analyzing_software_name if not already present
            try:
                self.execute_query("ALTER TABLE wholesale_products ADD COLUMN analyzing_software_name TEXT DEFAULT 'InternalAMZ';", [])
            except Exception:
                pass

            # Auto-check if existing table has outdated UNIQUE constraint on ASIN
            if self.has_unique_asin_constraint():
                logger.info("Outdated UNIQUE(asin, wholesaler_company_name) constraint detected. Auto-migrating table...")
                mig_ok, mig_msg = self.migrate_remove_unique_constraint()
                if mig_ok:
                    return True, f"✅ Database schema initialized and migrated! (Removed UNIQUE constraint to allow all rows)."

            return True, f"✅ Database schema initialized! Executed {executed_count} DDL statements (tables & indexes created)."
        except Exception as e:
            return False, f"Failed initializing schema: {e}"

