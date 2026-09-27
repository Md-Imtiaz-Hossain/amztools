"""
Module 3: Data Upload to Database - D1 Uploader Service
======================================================
Purpose:
    Orchestrates the entire upload pipeline:
    1. Receives analyzed products from Module 2 (in-memory or from file).
    2. Runs schema initialization if table does not exist.
    3. Transforms and chunks records into safe batch sizes.
    4. Generates parameterized UPSERT statements:
       INSERT INTO wholesale_products (...) VALUES (...)
       ON CONFLICT(asin, wholesaler_company_name) DO UPDATE SET ...
    5. Transmits batches to Cloudflare D1 via CloudflareD1Client.
    6. Yields progress updates and returns an execution report.
"""

from typing import Any, Callable, Dict, List, Optional
import time
import logging

from .d1_client import CloudflareD1Client
from .file_parser import parse_and_validate_analysis_file, validate_record_integrity

logger = logging.getLogger(__name__)


class D1UploaderService:
    """
    Service coordinating the batch upload of analyzed wholesale items to Cloudflare D1.
    """

    def __init__(self, client: CloudflareD1Client):
        """
        Initialize the uploader service with an active Cloudflare D1 client.
        """
        self.client = client

    def build_upsert_sql(self, sample_record: Dict[str, Any]) -> str:
        """
        Dynamically constructs the parameterized UPSERT SQL statement based on column keys.

        Args:
            sample_record: Dictionary of columns for one row.

        Returns:
            str: Parametric SQL template with ON CONFLICT UPDATE.
        """
        # Exclude internal non-table keys if any
        columns = [c for c in sample_record.keys() if c != "id"]
        col_list_str = ", ".join(columns)
        placeholders_str = ", ".join(["?"] * len(columns))

        # Build update assignments for ON CONFLICT
        # Do not overwrite compound unique keys (asin, wholesaler_company_name) or created_at
        immutable_keys = {"asin", "wholesaler_company_name", "created_at"}
        update_clauses = [
            f"{c} = excluded.{c}"
            for c in columns
            if c not in immutable_keys
        ]
        update_clauses.append("updated_at = CURRENT_TIMESTAMP")
        update_str = ", ".join(update_clauses)

        sql = (
            f"INSERT INTO wholesale_products ({col_list_str}) "
            f"VALUES ({placeholders_str}) "
            f"ON CONFLICT(asin, wholesaler_company_name) DO UPDATE SET {update_str};"
        )
        return sql

    def upload_dataset(
        self,
        dataset_source: Any,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        auto_init_schema: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute the full upload pipeline for a wholesale dataset.

        Args:
            dataset_source: Pandas DataFrame, file path, or uploaded file object.
            progress_callback: Optional callback receiving (progress_percentage: float, message: str).
            auto_init_schema: If True, executes schema.sql prior to uploading.

        Returns:
            Dict[str, Any]: Summary dictionary containing:
                - 'total_processed': int
                - 'uploaded_count': int
                - 'failed_count': int
                - 'elapsed_seconds': float
                - 'errors': List[str]
        """
        start_time = time.time()
        errors = []

        if progress_callback:
            progress_callback(0.05, "Parsing and validating dataset...")

        # 1. Parse dataset into sanitized SQL records
        try:
            records = parse_and_validate_analysis_file(dataset_source)
        except Exception as e:
            return {
                "success": False,
                "total_processed": 0,
                "uploaded_count": 0,
                "failed_count": 0,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "errors": [f"File parsing failed: {e}"],
            }

        if not records:
            return {
                "success": False,
                "total_processed": 0,
                "uploaded_count": 0,
                "failed_count": 0,
                "elapsed_seconds": round(time.time() - start_time, 2),
                "errors": ["No records found in source dataset."],
            }

        # 2. Pre-flight verification
        integrity = validate_record_integrity(records)
        valid_records = [
            r for r in records
            if r.get("asin") and str(r.get("asin")).upper() != "NOT_FOUND"
        ]

        if not valid_records:
            return {
                "success": False,
                "total_processed": len(records),
                "uploaded_count": 0,
                "failed_count": len(records),
                "elapsed_seconds": round(time.time() - start_time, 2),
                "errors": ["None of the records contained a valid Amazon ASIN."],
            }

        # 3. Ensure database schema exists
        if auto_init_schema:
            if progress_callback:
                progress_callback(0.10, "Verifying Cloudflare D1 table schema...")
            schema_ok, schema_msg = self.client.init_database_schema()
            if not schema_ok:
                logger.warning(f"Schema init note: {schema_msg}")

        # 4. Partition records into batches
        batch_size = max(5, min(100, self.client.config.batch_size))
        total_valid = len(valid_records)
        total_batches = (total_valid + batch_size - 1) // batch_size

        sample_record = valid_records[0]
        columns = [c for c in sample_record.keys() if c != "id"]
        upsert_sql = self.build_upsert_sql(sample_record)

        uploaded_count = 0
        failed_count = 0

        for b_idx in range(total_batches):
            chunk = valid_records[b_idx * batch_size : (b_idx + 1) * batch_size]
            
            # Construct batch statements
            batch_payload = []
            for row in chunk:
                # Extract positional params strictly matching columns order
                params = [row.get(col) for col in columns]
                batch_payload.append({
                    "sql": upsert_sql,
                    "params": params,
                })

            pct = 0.15 + (0.80 * ((b_idx + 1) / total_batches))
            status_msg = f"Uploading batch {b_idx + 1}/{total_batches} ({len(chunk)} records)..."
            if progress_callback:
                progress_callback(pct, status_msg)

            try:
                res = self.client.execute_batch(batch_payload)
                if res.get("success"):
                    uploaded_count += len(chunk)
                else:
                    failed_count += len(chunk)
                    errors.append(f"Batch {b_idx + 1} failed: {res.get('error', 'Execution error')}")
            except Exception as batch_err:
                failed_count += len(chunk)
                errors.append(f"Batch {b_idx + 1} network/query error: {batch_err}")

        elapsed = round(time.time() - start_time, 2)
        if progress_callback:
            progress_callback(1.0, f"Upload complete! {uploaded_count} products synchronized in {elapsed}s.")

        return {
            "success": uploaded_count > 0,
            "total_processed": len(records),
            "uploaded_count": uploaded_count,
            "failed_count": failed_count,
            "integrity_summary": integrity,
            "elapsed_seconds": elapsed,
            "errors": errors,
        }
