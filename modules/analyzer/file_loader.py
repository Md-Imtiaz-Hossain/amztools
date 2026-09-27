"""
Module 2: Analyze & Prepare Data - Supplier File Loader
======================================================
Purpose:
    Safely load supplier wholesale catalog files (CSV or Excel) into pandas DataFrames.
    Guarantees preservation of UPC/EAN/SKU leading zeros (dtype=str) and handles
    diverse file encodings (UTF-8, UTF-8-SIG, Latin-1, CP1252).

Inputs:
    - uploaded_file: Streamlit UploadedFile buffer or file-like object / file path.

Outputs:
    - pd.DataFrame: Ingested raw supplier catalog with preserved string codes.
"""

import pandas as pd


def load_supplier_file(uploaded_file):
    """
    Safely load a supplier file (CSV or Excel) into a pandas DataFrame.
    Preserves barcode strings with leading zeroes (dtype=str) and handles various file encodings.

    Args:
        uploaded_file: Streamlit UploadedFile or file path.

    Returns:
        pd.DataFrame or None if input is None.

    Raises:
        ValueError: If file parsing fails across all attempted encodings and formats.
    """
    if uploaded_file is None:
        return None

    try:
        file_name = getattr(uploaded_file, "name", str(uploaded_file)).lower()

        if file_name.endswith(".csv"):
            for encoding in ["utf-8", "utf-8-sig", "latin1", "cp1252"]:
                try:
                    if hasattr(uploaded_file, "seek"):
                        uploaded_file.seek(0)
                    return pd.read_csv(uploaded_file, encoding=encoding, dtype=str)
                except UnicodeDecodeError:
                    continue
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, dtype=str)
        else:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            return pd.read_excel(uploaded_file, dtype=str)
    except Exception as e:
        raise ValueError(f"Failed to load supplier file: {e}")
