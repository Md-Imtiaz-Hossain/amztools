"""
Module 5: Data Upload to MySQL Remote Database - MySQL Client
=============================================================
Purpose:
    Provides a resilient MySQL client using PyMySQL for executing DDL,
    single queries, and high-throughput batch inserts/upserts against a
    remote MySQL server (such as Hostinger MySQL: srv1570.hstgr.io / 82.197.82.58).
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    pymysql = None
    DictCursor = None

from .config import MySQLDatabaseConfig

logger = logging.getLogger(__name__)

# Known Hostinger hostname <-> IP fallback mapping
_HOSTINGER_FALLBACK_HOSTS = {
    "srv1570.hstgr.io": "82.197.82.58",
    "82.197.82.58": "srv1570.hstgr.io",
}


class MySQLRemoteClient:
    """
    Remote MySQL Database Client powered by PyMySQL.

    Responsibilities:
    - Connects to remote MySQL servers over TCP (port 3306) with UTF-8 (utf8mb4).
    - Automatically falls back between Hostinger hostname (srv1570.hstgr.io) and IP (82.197.82.58)
      if DNS resolution or routing fails.
    - Executes parameterized SQL statements and fast `executemany` batch transactions.
    - Initializes and auto-migrates the 54-column `wholesale_products` schema.
    """

    _verified_schema_dbs = set()

    def __init__(self, config: MySQLDatabaseConfig):
        self.config = config
        self._conn = None

    def _connect(self):
        if pymysql is None:
            raise RuntimeError("Python 'PyMySQL' library is not installed. Run: pip install PyMySQL")

        primary_host = self.config.host.strip()
        hosts_to_try = [primary_host]
        fallback_host = _HOSTINGER_FALLBACK_HOSTS.get(primary_host.lower())
        if fallback_host and fallback_host not in hosts_to_try:
            hosts_to_try.append(fallback_host)

        last_err = None
        for host_candidate in hosts_to_try:
            try:
                conn = pymysql.connect(
                    host=host_candidate,
                    port=int(self.config.port or 3306),
                    user=self.config.user.strip(),
                    password=self.config.password,
                    database=self.config.database.strip(),
                    charset="utf8mb4",
                    cursorclass=DictCursor,
                    connect_timeout=int(self.config.timeout_seconds or 30),
                    read_timeout=int(self.config.timeout_seconds or 30),
                    write_timeout=int(self.config.timeout_seconds or 30),
                    autocommit=False,
                )
                return conn
            except Exception as err:
                last_err = err
                err_code = getattr(err, "args", [None])[0]
                if err_code == 1045:
                    break
                logger.warning(f"MySQL connect attempt to {host_candidate} failed: {err}")

        raise last_err

    def _get_connection(self):
        if self._conn is not None:
            try:
                self._conn.ping(reconnect=True)
                return self._conn
            except Exception:
                try:
                    self._conn.close()
                except Exception:
                    pass
                self._conn = None
        self._conn = self._connect()
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def test_connection(self) -> Tuple[bool, str]:
        """
        Tests connectivity to the remote MySQL database using SELECT 1 and VERSION().
        """
        if not self.config.is_valid():
            missing = []
            if not self.config.host.strip():
                missing.append("Host")
            if not self.config.database.strip():
                missing.append("Database Name")
            if not self.config.user.strip():
                missing.append("User Name")
            if not self.config.password.strip():
                missing.append("Password")
            return False, f"Missing required MySQL credentials: {', '.join(missing)}."

        if pymysql is None:
            return False, "Python 'PyMySQL' package is not installed in the active environment."

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 AS ping, VERSION() AS server_version, DATABASE() AS current_db;")
                row = cursor.fetchone() or {}
            conn.commit()
            version = row.get("server_version", "MySQL")
            current_db = row.get("current_db", self.config.database)
            return (
                True,
                f"✅ Successfully connected to Remote MySQL (`{current_db}` on `{self.config.host}`, Server: `{version}`)!",
            )
        except Exception as e:
            err_str = str(e)
            if "1045" in err_str:
                return (
                    False,
                    f"MySQL Access Denied (Error 1045): Verify your Username, Password, and that Remote MySQL access is enabled for your IP in Hostinger hPanel. Details: {e}",
                )
            if "2003" in err_str:
                return (
                    False,
                    f"Cannot reach MySQL server at `{self.config.host}:{self.config.port}` (Error 2003). Check Host address or firewall. Details: {e}",
                )
            return False, f"MySQL Connection failed: {e}"

    def execute_query(self, sql: str, params: Optional[Union[List[Any], Tuple[Any, ...]]] = None) -> Dict[str, Any]:
        """
        Executes a single parameterized SQL query on the remote MySQL server.
        """
        conn = self._get_connection()
        with conn.cursor() as cursor:
            affected = cursor.execute(sql, tuple(params) if params else None)
            rows = cursor.fetchall() if cursor.description else []
            last_id = cursor.lastrowid
        conn.commit()
        return {
            "success": True,
            "results": list(rows) if rows else [],
            "meta": {
                "changes": affected or 0,
                "last_row_id": last_id,
            },
        }

    def execute_batch(
        self,
        batch_payload: List[Dict[str, Any]],
        max_retries: int = 3,
    ) -> Dict[str, Any]:
        """
        Executes a batch of parameterized SQL statements inside a single MySQL transaction.
        Groups consecutive statements with identical SQL templates into `cursor.executemany()`
        for high-speed bulk writes over remote connections.
        """
        if not batch_payload:
            return {"success": True, "total_changes": 0, "batch_count": 0}

        last_err = None
        for attempt in range(max_retries):
            try:
                conn = self._get_connection()
                total_changes = 0
                with conn.cursor() as cursor:
                    grouped_sql = None
                    grouped_params: List[Tuple[Any, ...]] = []

                    for item in batch_payload:
                        sql = item.get("sql", "")
                        params = tuple(item.get("params") or [])
                        if grouped_sql is None:
                            grouped_sql = sql
                            grouped_params = [params]
                        elif sql == grouped_sql:
                            grouped_params.append(params)
                        else:
                            if len(grouped_params) == 1:
                                total_changes += cursor.execute(grouped_sql, grouped_params[0]) or 0
                            else:
                                total_changes += cursor.executemany(grouped_sql, grouped_params) or 0
                            grouped_sql = sql
                            grouped_params = [params]

                    if grouped_sql and grouped_params:
                        if len(grouped_params) == 1:
                            total_changes += cursor.execute(grouped_sql, grouped_params[0]) or 0
                        else:
                            total_changes += cursor.executemany(grouped_sql, grouped_params) or 0

                conn.commit()
                return {
                    "success": True,
                    "total_changes": total_changes,
                    "batch_count": len(batch_payload),
                }
            except Exception as e:
                last_err = e
                try:
                    if self._conn:
                        self._conn.rollback()
                except Exception:
                    pass
                self.close()
                backoff = 1.5 * (attempt + 1)
                logger.warning(
                    f"MySQL batch error (attempt {attempt + 1}/{max_retries}): {e}. Retrying in {backoff}s..."
                )
                if attempt < max_retries - 1:
                    time.sleep(backoff)

        return {
            "success": False,
            "total_changes": 0,
            "batch_count": len(batch_payload),
            "error": str(last_err),
        }

    def clear_table(self, wholesaler_company_name: Optional[str] = None) -> Tuple[bool, str]:
        """
        Clears records from `wholesale_products` table in MySQL.
        If `wholesaler_company_name` is provided, deletes only rows for that wholesaler.
        Otherwise, truncates the entire table.
        """
        try:
            if wholesaler_company_name and wholesaler_company_name.strip():
                ws = wholesaler_company_name.strip()
                self.execute_query(
                    "DELETE FROM wholesale_products WHERE wholesaler_company_name = %s;",
                    [ws],
                )
                return True, f"✅ Successfully cleared previous MySQL records for wholesaler '{ws}'."
            else:
                self.execute_query("TRUNCATE TABLE wholesale_products;", [])
                return True, "✅ Successfully cleared all records from MySQL `wholesale_products` table."
        except Exception as e:
            return False, f"Failed clearing MySQL table: {e}"

    def init_database_schema(self, schema_sql_path: Optional[str] = None, force: bool = False) -> Tuple[bool, str]:
        """
        Executes the MySQL DDL schema to ensure `wholesale_products` table and all columns/indexes exist.
        Caches verification per session so repeated uploads don't re-run DDL unnecessarily.
        """
        db_key = f"{self.config.host}:{self.config.port}:{self.config.database}"
        if not force and db_key in self._verified_schema_dbs:
            return True, "✅ MySQL schema already verified in this session."

        if not schema_sql_path:
            schema_sql_path = os.path.join(os.path.dirname(__file__), "schema.sql")

        if not os.path.exists(schema_sql_path):
            return False, f"MySQL schema file not found at {schema_sql_path}"

        with open(schema_sql_path, "r", encoding="utf-8") as f:
            sql_content = f.read()

        raw_statements = sql_content.split(";")
        statements_to_run = []
        for stmt in raw_statements:
            lines = [line for line in stmt.splitlines() if not line.strip().startswith("--")]
            cleaned = "\n".join(lines).strip()
            if cleaned:
                statements_to_run.append(cleaned)

        if not statements_to_run:
            return False, "No valid SQL statements found in MySQL schema.sql."

        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                for stmt in statements_to_run:
                    try:
                        cursor.execute(stmt)
                    except Exception as stmt_err:
                        err_code = getattr(stmt_err, "args", [None])[0]
                        if err_code != 1061:
                            raise

                cursor.execute("SHOW COLUMNS FROM wholesale_products;")
                existing_cols = {row["Field"].lower() for row in (cursor.fetchall() or [])}

                required_extra_cols = {
                    "parent_asin": "VARCHAR(32) NULL",
                    "analyzing_software_name": "VARCHAR(128) DEFAULT 'InternalAMZ'",
                    "last_run": "VARCHAR(64) NULL",
                }
                for col_name, col_def in required_extra_cols.items():
                    if col_name.lower() not in existing_cols:
                        cursor.execute(f"ALTER TABLE wholesale_products ADD COLUMN {col_name} {col_def};")

            conn.commit()
            self._verified_schema_dbs.add(db_key)
            return (
                True,
                f"✅ MySQL table `wholesale_products` initialized and verified in `{self.config.database}`!",
            )
        except Exception as e:
            return False, f"Failed initializing MySQL schema: {e}"
