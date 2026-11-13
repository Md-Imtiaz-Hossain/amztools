"""
Module 2: Analyze & Prepare Data - Live Amazon API Analysis Report
==================================================================
Purpose:
    Generates a single, clean report after Live Amazon SP-API analysis showing
    which rows succeeded in fetching data from Amazon SP-API and which rows
    were not successful and why.

    Example format:
        312547493833 - Success
        312547493855 - Not success - UPC not found on amazon
"""

import io
from typing import Any, Dict, List, Optional, Set
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from modules.analyzer.file_loader import detect_auxiliary_columns, detect_catalog_columns
from modules.analyzer.sp_api_client import clean_identifier


def generate_analysis_report(
    results_df: pd.DataFrame,
    supplier_df: Optional[pd.DataFrame] = None,
    upc_col: Optional[str] = None,
    cost_col: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a single report showing which rows succeeded in fetching data via Live Amazon API
    and which rows were unable to be analyzed and why.

    Returns:
        Dict containing:
            - "report_df": DataFrame with columns:
                ["Row #", "Product ID", "Title", "ASIN", "Status", "Reason", "Report"]
            - "failed_df": Subset of report_df where Status == "Not success"
            - "report_lines": List of strings (e.g. "312547493833 - Success",
                "312547493855 - Not success - UPC not found on amazon")
            - "summary": {
                "total_rows": int,
                "success_count": int,
                "not_success_count": int,
              }
    """
    if results_df is None:
        results_df = pd.DataFrame()

    # Index analyzed rows by Product ID and position
    results_by_pid: Dict[str, List[Dict[str, Any]]] = {}
    results_records: List[Dict[str, Any]] = []

    if not results_df.empty:
        for idx, r in results_df.iterrows():
            rec = r.to_dict()
            rec["_df_index"] = idx
            results_records.append(rec)
            pid_raw = str(rec.get("Product ID", "") or "").strip()
            clean_pid, _ = clean_identifier(pid_raw)
            for key in {pid_raw, clean_pid}:
                if key:
                    results_by_pid.setdefault(key, []).append(rec)

    title_col = None
    has_supplier = supplier_df is not None and not supplier_df.empty
    if has_supplier:
        if not upc_col or upc_col not in supplier_df.columns:
            u_idx, c_idx = detect_catalog_columns(supplier_df)
            cols_list = list(supplier_df.columns)
            upc_col = cols_list[u_idx] if cols_list else None
            if not cost_col or cost_col not in supplier_df.columns:
                cost_col = cols_list[c_idx] if cols_list else None
        aux = detect_auxiliary_columns(supplier_df, upc_col, cost_col)
        title_col = aux.get("title_col")

    total_rows = len(supplier_df) if has_supplier else len(results_records)
    used_result_indices: Set[Any] = set()

    report_rows: List[Dict[str, Any]] = []
    report_lines: List[str] = []
    success_count = 0
    not_success_count = 0

    for pos in range(total_rows):
        row_num = pos + 1
        supp_id_raw = ""
        supp_title = ""
        matched_rec: Optional[Dict[str, Any]] = None

        if has_supplier:
            s_row = supplier_df.iloc[pos]
            supp_id_raw = str(s_row.get(upc_col, "") if upc_col else "").strip()
            if supp_id_raw.endswith(".0"):
                supp_id_raw = supp_id_raw[:-2]
            if title_col and title_col in s_row:
                supp_title = str(s_row.get(title_col, "") or "").strip()

            clean_id, _ = clean_identifier(supp_id_raw)
            if pos < len(results_records):
                cand = results_records[pos]
                cand_pid = str(cand.get("Product ID", "") or "").strip()
                cand_clean, _ = clean_identifier(cand_pid)
                if cand_pid in (supp_id_raw, clean_id) or cand_clean in (supp_id_raw, clean_id):
                    matched_rec = cand
                    used_result_indices.add(cand["_df_index"])

            if matched_rec is None:
                for key in (supp_id_raw, clean_id):
                    if key and key in results_by_pid:
                        for cand in results_by_pid[key]:
                            if cand["_df_index"] not in used_result_indices:
                                matched_rec = cand
                                used_result_indices.add(cand["_df_index"])
                                break
                        if matched_rec is not None:
                            break
        else:
            matched_rec = results_records[pos]
            used_result_indices.add(matched_rec["_df_index"])
            supp_id_raw = str(matched_rec.get("Product ID", "") or "").strip()
            supp_title = str(matched_rec.get("Title", "") or "").strip()

        clean_id, id_type = clean_identifier(supp_id_raw)
        display_id = clean_id if clean_id else (supp_id_raw if supp_id_raw else f"Row_{row_num}")

        if matched_rec is None:
            not_success_count += 1
            status = "Not success"
            if not clean_id:
                why = "Invalid or empty Product ID"
            else:
                why = f"{id_type} not analyzed (missing from analyzed output)"
            reason_str = f"Not success - {why}"
            line_str = f"{display_id} - {reason_str}"
            asin_out = "NOT_FOUND"
            title_out = supp_title
        else:
            asin_val = str(matched_rec.get("ASIN", "") or "").strip()
            asin_upper = asin_val.upper()
            amz_title = str(matched_rec.get("Title", "") or "").strip()
            custom_notes = str(matched_rec.get("Custom Notes", "") or "").strip()
            title_out = amz_title if (amz_title and amz_title != "Product not found on Amazon") else supp_title

            if not clean_id or asin_upper == "INVALID_ID":
                not_success_count += 1
                status = "Not success"
                why = "Invalid or empty Product ID"
                reason_str = f"Not success - {why}"
                line_str = f"{display_id} - {reason_str}"
                asin_out = "INVALID_ID"
            elif asin_upper in ("NOT_FOUND", "", "NONE", "NAN"):
                not_success_count += 1
                status = "Not success"
                if custom_notes and ("error" in custom_notes.lower() or "not found" in custom_notes.lower()):
                    why = custom_notes
                else:
                    why = f"{id_type} not found on amazon"
                reason_str = f"Not success - {why}"
                line_str = f"{display_id} - {reason_str}"
                asin_out = "NOT_FOUND"
            else:
                success_count += 1
                status = "Success"
                reason_str = "Success"
                line_str = f"{display_id} - Success"
                asin_out = asin_val

        report_lines.append(line_str)
        report_rows.append(
            {
                "Row #": row_num,
                "Product ID": display_id,
                "Title": title_out,
                "ASIN": asin_out,
                "Status": status,
                "Reason": reason_str,
                "Report": line_str,
            }
        )

    report_df = pd.DataFrame(report_rows)
    if not report_df.empty:
        failed_df = report_df[report_df["Status"] == "Not success"].copy().reset_index(drop=True)
    else:
        failed_df = pd.DataFrame(columns=["Row #", "Product ID", "Title", "ASIN", "Status", "Reason", "Report"])

    return {
        "report_df": report_df,
        "failed_df": failed_df,
        "report_lines": report_lines,
        "summary": {
            "total_rows": total_rows,
            "success_count": success_count,
            "not_success_count": not_success_count,
        },
    }


def export_analysis_report_excel(report_data: Dict[str, Any]) -> bytes:
    """
    Generate a single-sheet Excel workbook (.xlsx) for the Live Analysis Report.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Analysis Report"

    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=10)
    ok_fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
    err_fill = PatternFill(start_color="FCE4D6", end_color="FCE4D6", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    report_df = report_data.get("report_df", pd.DataFrame())
    if report_df is None or report_df.empty:
        ws.append(["No rows in report."])
    else:
        cols = list(report_df.columns)
        ws.append(cols)
        for c_idx in range(1, len(cols) + 1):
            cell = ws.cell(row=1, column=c_idx)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")

        status_col_idx = cols.index("Status") + 1 if "Status" in cols else None
        report_col_idx = cols.index("Report") + 1 if "Report" in cols else None

        for r_idx, (_, row) in enumerate(report_df.iterrows(), start=2):
            ws.append([None if pd.isna(row[c]) else row[c] for c in cols])
            is_success = str(row.get("Status", "")) == "Success"
            row_fill = ok_fill if is_success else err_fill
            for c_idx in range(1, len(cols) + 1):
                c_cell = ws.cell(row=r_idx, column=c_idx)
                c_cell.border = thin_border
                if c_idx in (status_col_idx, report_col_idx):
                    c_cell.fill = row_fill

        ws.freeze_panes = "A2"
        for c_idx, col_name in enumerate(cols, start=1):
            col_letter = get_column_letter(c_idx)
            if col_name in ("Title", "Report", "Reason"):
                ws.column_dimensions[col_letter].width = 45
            elif col_name in ("Product ID", "ASIN", "Status"):
                ws.column_dimensions[col_letter].width = 20
            else:
                ws.column_dimensions[col_letter].width = 10

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
