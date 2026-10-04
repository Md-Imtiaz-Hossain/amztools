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
    - Supports single queries and batch query execution.
    - Handles HTTP errors, network timeouts, and JSON response decoding.
    """

    def __init__(self, config: CloudflareD1Config):
        """
        Initialize the D1 client with connection configuration.
        """
        self.config = config

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

        url = self.config.query_endpoint_url
        headers = self._get_headers()
        payload = {
            "sql": sql,
            "params": params or [],
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)
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

    def execute_batch(self, batch_payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute multiple SQL statements in batch against Cloudflare D1.

        Args:
            batch_payload (List[Dict[str, Any]]): List of query dicts, each with 'sql' and 'params'.

        Returns:
            Dict[str, Any]: Summary response with total changes and status.
        """
        if not batch_payload:
            return {"success": True, "total_changes": 0, "batch_count": 0}

        if requests is None:
            raise RuntimeError("Python 'requests' library is not installed.")

        url = self.config.query_endpoint_url
        headers = self._get_headers()

        # Cloudflare D1 batch format: {"batch": [{"sql": "...", "params": [...]}, ...]}
        payload = {"batch": batch_payload}
        resp = requests.post(url, headers=headers, json=payload, timeout=self.config.timeout_seconds)
        
        # If the endpoint doesn't support the {"batch": ...} wrapper, fallback to sequential execution
        if resp.status_code != 200 or not resp.json().get("success"):
            logger.warning("Batch endpoint returned non-200. Attempting fallback individual execution...")
            total_changes = 0
            for item in batch_payload:
                res = self.execute_query(item.get("sql", ""), item.get("params", []))
                total_changes += res.get("meta", {}).get("changes", 1)
            return {"success": True, "total_changes": total_changes, "batch_count": len(batch_payload)}

        data = resp.json()
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

            return True, f"✅ Database schema initialized! Executed {executed_count} DDL statements (tables & indexes created)."
        except Exception as e:
            return False, f"Failed initializing schema: {e}"

