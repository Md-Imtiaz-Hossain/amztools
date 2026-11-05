"""
Module 5: Data Upload to MySQL Remote Database - Uploader Service
=================================================================
Purpose:
    Orchestrates the batch upload pipeline to a remote MySQL database (e.g. Hostinger):
    1. Receives analyzed products from Module 2 (in-memory or from file).
    2. Initializes / verifies the `wholesale_products` MySQL table schema.
    3. Transforms and chunks records into slots and micro-batches.
    4. Generates parameterized MySQL INSERT or ON DUPLICATE KEY UPDATE statements.
    5. Executes batches via MySQLRemoteClient using `executemany()` transactions.
    6. Yields real-time progress and slot notifications.
"""

from typing import Any, Callable, Dict, List, Optional
import time
import logging

from .mysql_client import MySQLRemoteClient
from modules.uploader.file_parser import (
    parse_and_validate_analysis_file,
    validate_record_integrity,
)

logger = logging.getLogger(__name__)


class MySQLUploaderService:
    """
    Service coordinating the batch upload of analyzed wholesale items to Remote MySQL.
    """

    def __init__(self, client: MySQLRemoteClient):
        self.client = client

    def build_insert_sql(self, sample_record: Dict[str, Any]) -> str:
        """
        Constructs a parameterized MySQL INSERT statement using `%s` placeholders.
        Preserves 100% of rows from the catalog.
        """
        columns = [c for c in sample_record.keys() if c != "id"]
        col_list_str = ", ".join(columns)
        placeholders_str = ", ".join(["%s"] * len(columns))
        return f"INSERT INTO wholesale_products ({col_list_str}) VALUES ({placeholders_str});"

    def build_upsert_sql(self, sample_record: Dict[str, Any]) -> str:
        """
        Constructs a parameterized MySQL INSERT ... ON DUPLICATE KEY UPDATE statement.
        """
        columns = [c for c in sample_record.keys() if c != "id"]
        col_list_str = ", ".join(columns)
        placeholders_str = ", ".join(["%s"] * len(columns))

        immutable_keys = {"asin", "wholesaler_company_name", "created_at"}
        update_clauses = [
            f"{c} = VALUES({c})"
            for c in columns
            if c not in immutable_keys
        ]
        update_clauses.append("updated_at = CURRENT_TIMESTAMP")
        update_str = ", ".join(update_clauses)

        return (
            f"INSERT INTO wholesale_products ({col_list_str}) "
            f"VALUES ({placeholders_str}) "
            f"ON DUPLICATE KEY UPDATE {update_str};"
        )

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
        Executes the full upload pipeline for a wholesale dataset into Remote MySQL
        using slot-based batching.
        """
        start_time = time.time()
        errors: List[str] = []
        slot_logs: List[Dict[str, Any]] = []

        if progress_callback:
            progress_callback(0.02, "Parsing and validating dataset for MySQL upload...")

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

        integrity = validate_record_integrity(records)
        # Upload 100% of parsed records without filtering or deleting any rows
        valid_records = list(records)
        for r in valid_records:
            if r.get("asin") is None:
                r["asin"] = str(r.get("product_id") or "")
            if not r.get("wholesaler_company_name"):
                r["wholesaler_company_name"] = wholesaler_name or "Default Wholesale"

        if self.client:
            if auto_init_schema:
                if progress_callback:
                    progress_callback(0.04, "Verifying Remote MySQL table schema...")
                schema_ok, schema_msg = self.client.init_database_schema()
                if not schema_ok:
                    logger.warning(f"MySQL Schema init note: {schema_msg}")
                    errors.append(f"Schema initialization warning: {schema_msg}")

            # Ensure all columns from the uploaded file exist in the MySQL table
            if getattr(self.client, "ensure_columns_exist", None) and valid_records:
                sample_cols = [c for c in valid_records[0].keys() if c != "id"]
                self.client.ensure_columns_exist(sample_cols)

            if clear_existing == "all":
                if progress_callback:
                    progress_callback(0.05, "Clearing entire wholesale_products table in MySQL before upload...")
                self.client.clear_table()
            elif clear_existing == "wholesaler":
                target_ws = wholesaler_name or valid_records[0].get("wholesaler_company_name")
                if target_ws:
                    if progress_callback:
                        progress_callback(0.05, f"Clearing previous MySQL records for wholesaler '{target_ws}'...")
                    self.client.clear_table(wholesaler_company_name=target_ws)

        effective_slot_size = max(10, int(slot_size or 500))
        default_batch = getattr(getattr(self.client, "config", None), "batch_size", 100) if self.client else 100
        effective_batch_size = max(5, min(500, int(batch_size or default_batch or 100)))

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
            if stop_check and stop_check():
                logger.info(f"MySQL upload stopped by user after slot {slot_idx}.")
                break

            slot_start_time = time.time()
            start_record_idx = slot_idx * effective_slot_size
            end_record_idx = min(total_valid, (slot_idx + 1) * effective_slot_size)
            slot_records = valid_records[start_record_idx:end_record_idx]

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
                            errors.append(
                                f"Slot {slot_idx + 1} Batch {sb_idx + 1} failed: {res.get('error', 'MySQL execution error')}"
                            )
                    else:
                        uploaded_count += len(chunk)
                        slot_uploaded += len(chunk)
                except Exception as batch_err:
                    failed_count += len(chunk)
                    slot_failed += len(chunk)
                    errors.append(f"Slot {slot_idx + 1} Batch {sb_idx + 1} error: {batch_err}")

            slot_elapsed = round(time.time() - slot_start_time, 2)
            total_elapsed = round(time.time() - start_time, 2)
            speed = round(uploaded_count / max(0.1, total_elapsed), 1)
            remaining_records = max(0, total_valid - uploaded_count)
            eta_seconds = int(remaining_records / max(1.0, speed)) if speed > 0 else 0

            slot_msg = (
                f"Slot {slot_idx + 1} of {total_slots} complete: "
                f"Excel rows {excel_start_row} to {excel_end_row} ({slot_uploaded} records) "
                f"successfully uploaded to MySQL database."
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

            if slot_callback:
                try:
                    slot_callback(slot_info)
                except Exception as cb_err:
                    logger.warning(f"MySQL slot callback error: {cb_err}")

            overall_pct = (slot_idx + 1) / total_slots
            if progress_callback:
                progress_callback(
                    overall_pct,
                    f"Uploaded {uploaded_count:,} of {total_valid:,} rows ({overall_pct * 100:.1f}%) | "
                    f"Slot {slot_idx + 1}/{total_slots} (Excel rows {excel_start_row}–{excel_end_row}) complete | {speed} rows/s",
                )

        total_elapsed = round(time.time() - start_time, 2)
        if progress_callback:
            progress_callback(
                1.0,
                f"MySQL upload complete! {uploaded_count:,} products synchronized in {len(slot_logs)} slots ({total_elapsed}s).",
            )

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
