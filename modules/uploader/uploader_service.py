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

    def build_insert_sql(self, sample_record: Dict[str, Any]) -> str:
        """
        Dynamically constructs an INSERT statement tailored to Cloudflare D1 (SQLite).
        Preserves 100% of rows from the catalog without merging duplicate ASINs or variations.
        """
        columns = [c for c in sample_record.keys() if c != "id"]
        col_list_str = ", ".join(columns)
        placeholders_str = ", ".join(["?"] * len(columns))
        return f"INSERT INTO wholesale_products ({col_list_str}) VALUES ({placeholders_str});"

    def upload_dataset(
        self,
        dataset_source: Any,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        slot_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        slot_size: int = 500,
        batch_size: Optional[int] = None,
        auto_init_schema: bool = True,
        upload_mode: str = "insert",
        clear_existing: str = "none",
        wholesaler_name: Optional[str] = None,
        stop_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the full upload pipeline for a wholesale dataset using smart slot-based batching.
        Partitions large datasets into slots (default 500 records per slot) and micro-batches to
        prevent database/client timeouts or memory crashes, issuing confirmations after each slot.

        Args:
            dataset_source: Pandas DataFrame, file path, uploaded file object, or list of record dicts.
            progress_callback: Optional callback receiving (progress_percentage: float, message: str).
            slot_callback: Optional callback invoked whenever a slot (e.g. 500 records) completes,
                           receiving detailed slot metrics and Excel row ranges.
            slot_size: Number of records per notification slot (default: 500).
            batch_size: Sub-batch size per HTTP statement (default: 50 to respect D1 boundaries).
            auto_init_schema: If True, executes schema.sql prior to uploading.
            upload_mode: "insert" (default, stores all 4,987 rows including variations/duplicate ASINs)
                         or "upsert" (overwrites matching ASINs).
            clear_existing: "none" (default, appends), "all" (wipes wholesale_products table before upload),
                            or "wholesaler" (clears only records for wholesaler_name).
            wholesaler_name: Optional wholesaler company name for scoped cleanup.
            stop_check: Optional callable returning True if user requested early cancellation.

        Returns:
            Dict[str, Any]: Summary dictionary containing execution metrics, slot logs, and statuses.
        """
        start_time = time.time()
        errors = []
        slot_logs = []

        if progress_callback:
            progress_callback(0.02, "Parsing and validating dataset...")

        # 1. Parse dataset into sanitized SQL records
        try:
            records = parse_and_validate_analysis_file(dataset_source)
        except Exception as e:
            return {
                "success": False,
                "total_processed": 0,
                "uploaded_count": 0,
                "failed_count": 0,
                "total_slots": 0,
                "completed_slots": 0,
                "slot_size": slot_size,
                "slot_logs": [],
                "elapsed_seconds": round(time.time() - start_time, 2),
                "errors": [f"File parsing failed: {e}"],
            }

        if not records:
            return {
                "success": False,
                "total_processed": 0,
                "uploaded_count": 0,
                "failed_count": 0,
                "total_slots": 0,
                "completed_slots": 0,
                "slot_size": slot_size,
                "slot_logs": [],
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
                "total_slots": 0,
                "completed_slots": 0,
                "slot_size": slot_size,
                "slot_logs": [],
                "elapsed_seconds": round(time.time() - start_time, 2),
                "errors": ["None of the records contained a valid Amazon ASIN."],
            }

        # 3. Ensure database schema exists and cleanup if requested
        if self.client:
            if clear_existing == "all":
                if progress_callback:
                    progress_callback(0.04, "Clearing entire wholesale_products table before upload...")
                self.client.clear_table()
            elif clear_existing == "wholesaler":
                target_ws = wholesaler_name or valid_records[0].get("wholesaler_company_name")
                if target_ws:
                    if progress_callback:
                        progress_callback(0.04, f"Clearing previous records for wholesaler '{target_ws}'...")
                    self.client.clear_table(wholesaler_company_name=target_ws)

            if auto_init_schema:
                if progress_callback:
                    progress_callback(0.05, "Verifying Cloudflare D1 table schema...")
                schema_ok, schema_msg = self.client.init_database_schema()
                if not schema_ok:
                    logger.warning(f"Schema init note: {schema_msg}")

            # If upload_mode is "insert", ensure table has no outdated UNIQUE constraint on ASIN
            if upload_mode == "insert" and getattr(self.client, "has_unique_asin_constraint", None):
                if self.client.has_unique_asin_constraint():
                    if progress_callback:
                        progress_callback(0.07, "Migrating table schema to allow duplicate ASINs...")
                    self.client.migrate_remove_unique_constraint()

        # 4. Partition records into slots of 500 (with safe micro-batches per HTTP call)
        effective_slot_size = max(10, int(slot_size or 500))
        default_batch = getattr(getattr(self.client, "config", None), "batch_size", 50) if self.client else 50
        effective_batch_size = max(5, min(100, int(batch_size or default_batch or 50)))

        total_valid = len(valid_records)
        total_slots = max(1, (total_valid + effective_slot_size - 1) // effective_slot_size)

        sample_record = valid_records[0]
        columns = [c for c in sample_record.keys() if c != "id"]
        if upload_mode == "insert":
            exec_sql = self.build_insert_sql(sample_record)
        else:
            exec_sql = self.build_upsert_sql(sample_record)

        uploaded_count = 0
        failed_count = 0

        for slot_idx in range(total_slots):
            # Check for early cancellation
            if stop_check and stop_check():
                logger.info(f"Upload process stopped by user after slot {slot_idx}.")
                break

            slot_start_time = time.time()
            start_record_idx = slot_idx * effective_slot_size
            end_record_idx = min(total_valid, (slot_idx + 1) * effective_slot_size)
            slot_records = valid_records[start_record_idx : end_record_idx]

            # 1-indexed Excel data row positions
            excel_start_row = start_record_idx + 1
            excel_end_row = end_record_idx

            slot_uploaded = 0
            slot_failed = 0
            sub_batches = max(1, (len(slot_records) + effective_batch_size - 1) // effective_batch_size)

            for sb_idx in range(sub_batches):
                chunk = slot_records[sb_idx * effective_batch_size : (sb_idx + 1) * effective_batch_size]
                if not chunk:
                    continue

                batch_payload = [
                    {"sql": exec_sql, "params": [row.get(col) for col in columns]}
                    for row in chunk
                ]

                try:
                    if self.client:
                        res = self.client.execute_batch(batch_payload)
                        if res.get("success"):
                            uploaded_count += len(chunk)
                            slot_uploaded += len(chunk)
                        else:
                            failed_count += len(chunk)
                            slot_failed += len(chunk)
                            errors.append(f"Slot {slot_idx + 1} Batch {sb_idx + 1} failed: {res.get('error', 'Execution error')}")
                    else:
                        uploaded_count += len(chunk)
                        slot_uploaded += len(chunk)
                except Exception as batch_err:
                    failed_count += len(chunk)
                    slot_failed += len(chunk)
                    errors.append(f"Slot {slot_idx + 1} Batch {sb_idx + 1} error: {batch_err}")

            # Slot Completed: Calculate metrics & notify
            slot_elapsed = round(time.time() - slot_start_time, 2)
            total_elapsed = round(time.time() - start_time, 2)
            speed = round(uploaded_count / max(0.1, total_elapsed), 1)
            remaining_records = max(0, total_valid - uploaded_count)
            eta_seconds = int(remaining_records / max(1.0, speed)) if speed > 0 else 0

            slot_msg = (
                f"Slot {slot_idx + 1} of {total_slots} complete: "
                f"Excel rows {excel_start_row} to {excel_end_row} ({slot_uploaded} records) "
                f"successfully uploaded to database."
            )

            slot_info = {
                "slot_number": slot_idx + 1,
                "total_slots": total_slots,
                "start_row": excel_start_row,
                "end_row": excel_end_row,
                "slot_records_count": len(slot_records),
                "slot_uploaded": slot_uploaded,
                "slot_failed": slot_failed,
                "cumulative_uploaded": uploaded_count,
                "total_records": total_valid,
                "slot_elapsed_seconds": slot_elapsed,
                "total_elapsed_seconds": total_elapsed,
                "speed_records_per_sec": speed,
                "eta_seconds": eta_seconds,
                "message": slot_msg,
            }
            slot_logs.append(slot_info)

            # Trigger slot notification callback
            if slot_callback:
                try:
                    slot_callback(slot_info)
                except Exception as cb_err:
                    logger.warning(f"Slot callback error: {cb_err}")

            # Trigger progress bar callback
            overall_pct = (slot_idx + 1) / total_slots
            if progress_callback:
                progress_callback(
                    overall_pct,
                    f"Uploaded {uploaded_count:,} of {total_valid:,} rows ({overall_pct*100:.1f}%) | "
                    f"Slot {slot_idx + 1}/{total_slots} (Excel rows {excel_start_row}–{excel_end_row}) complete | {speed} rows/s"
                )

        total_elapsed = round(time.time() - start_time, 2)
        if progress_callback:
            progress_callback(1.0, f"Upload complete! {uploaded_count:,} products synchronized in {len(slot_logs)} slots ({total_elapsed}s).")

        return {
            "success": uploaded_count > 0,
            "total_processed": len(records),
            "uploaded_count": uploaded_count,
            "failed_count": failed_count,
            "total_slots": total_slots,
            "completed_slots": len(slot_logs),
            "slot_size": effective_slot_size,
            "slot_logs": slot_logs,
            "integrity_summary": integrity,
            "elapsed_seconds": total_elapsed,
            "errors": errors,
        }

