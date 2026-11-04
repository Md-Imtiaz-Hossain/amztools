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

import re
import pandas as pd


_ID_HEADER_KEYWORDS = (
    "upc", "ean", "gtin", "barcode", "bar code", "asin", "isbn",
    "product id", "product_id", "item id", "item_id", "sku",
)
_COST_HEADER_KEYWORDS = (
    "cost", "price", "wholesale", "fob", "net", "each", "w/s", "rate",
)


def _is_unnamed_or_empty_header(columns) -> bool:
    """Return True if the majority of DataFrame columns look like 'Unnamed: ...' or blank."""
    if not len(columns):
        return True
    unnamed_count = sum(
        1
        for c in columns
        if not str(c).strip()
        or str(c).strip().lower().startswith("unnamed:")
        or str(c).strip().lower() in ("none", "nan")
    )
    return unnamed_count >= max(1, len(columns) // 2)


def _promote_header_row_if_needed(df: pd.DataFrame) -> pd.DataFrame:
    """
    If a supplier Excel/CSV file has banner/title/blank rows above the real table header,
    scan the first 15 rows to locate the actual header row containing identifier and cost columns.
    """
    if df is None or df.empty:
        return df

    cols_lower = [str(c).strip().lower() for c in df.columns]
    has_id_col = any(any(k in c for k in _ID_HEADER_KEYWORDS) for c in cols_lower)
    has_cost_col = any(any(k in c for k in _COST_HEADER_KEYWORDS) for c in cols_lower)

    if (has_id_col and has_cost_col) or not _is_unnamed_or_empty_header(df.columns):
        return df

    max_scan = min(15, len(df))
    for row_idx in range(max_scan):
        row_vals = [str(v).strip() if pd.notna(v) else "" for v in df.iloc[row_idx].values]
        row_lower = [v.lower() for v in row_vals if v and v.lower() not in ("nan", "none")]
        if len(row_lower) < 2:
            continue
        row_has_id = any(any(k in cell for k in _ID_HEADER_KEYWORDS) for cell in row_lower)
        row_has_cost = any(any(k in cell for k in _COST_HEADER_KEYWORDS) for cell in row_lower)
        if row_has_id and row_has_cost:
            new_cols = [
                v if (v and v.lower() not in ("nan", "none")) else f"Column_{i}"
                for i, v in enumerate(row_vals)
            ]
            new_df = df.iloc[row_idx + 1 :].copy()
            new_df.columns = new_cols
            new_df = new_df.dropna(how="all").reset_index(drop=True)
            return new_df

    return df


def detect_catalog_columns(df: pd.DataFrame):
    """
    Accurately detect the Product ID (UPC/EAN/ASIN) column index and the Unit Wholesale Cost
    column index in a supplier DataFrame.

    Avoids false-positive matches on Case Pack, Case Price, Qty, MSRP, Retail Price, or Row IDs.

    Returns:
        Tuple[int, int]: (default_upc_idx, default_cost_idx)
    """
    if df is None or df.empty or len(df.columns) == 0:
        return 0, 0

    cols = list(df.columns)
    num_cols = len(cols)
    sample_df = df.head(25)

    # 1. Score each column as a candidate Product Identifier (UPC / EAN / ASIN)
    id_scores = []
    for idx, col in enumerate(cols):
        c_low = str(col).strip().lower()
        c_norm = re.sub(r"[^a-z0-9]+", " ", c_low).strip()
        score = 0

        # Penalize obvious cost/price/qty/pack/title columns
        if any(w in c_norm for w in ("price", "cost", "wholesale", "msrp", "retail", "qty", "quantity", "pack", "case", "title", "description", "name", "brand")):
            score -= 100

        # Priority header matching
        if c_norm in ("upc", "ean", "gtin", "barcode", "upc ean", "upc code", "ean code", "product id"):
            score += 100
        elif any(w in c_norm.split() for w in ("upc", "ean", "gtin", "barcode")):
            score += 85
        elif any(k in c_low for k in ("upc", "ean", "gtin", "barcode")):
            score += 75
        elif c_norm in ("asin", "amazon asin"):
            score += 70
        elif "product id" in c_norm or "item id" in c_norm or "isbn" in c_norm:
            score += 55
        elif "asin" in c_norm:
            score += 50
        elif "sku" in c_norm or "item number" in c_norm or "item no" in c_norm or "part number" in c_norm:
            score += 25

        # Inspect sample values for 11-14 digit barcodes or 10-char ASINs
        vals = [str(v).strip() for v in sample_df.iloc[:, idx].dropna() if str(v).strip().lower() not in ("", "nan", "none")]
        if vals:
            barcode_hits = 0
            for v in vals[:15]:
                v_clean = v[:-2] if v.endswith(".0") else v
                digits = re.sub(r"\D", "", v_clean)
                if 11 <= len(digits) <= 14 and len(digits) >= len(v_clean) - 2:
                    barcode_hits += 1
                elif re.fullmatch(r"B0[A-Z0-9]{8}", v_clean.upper()):
                    barcode_hits += 1
            ratio = barcode_hits / len(vals[:15])
            if ratio >= 0.5:
                score += 60

        id_scores.append((score, -idx, idx))

    best_upc_idx = max(id_scores)[2] if id_scores else 0

    # 2. Score each column as a candidate Unit Wholesale Cost
    cost_scores = []
    for idx, col in enumerate(cols):
        if idx == best_upc_idx and num_cols > 1:
            cost_scores.append((-999, -idx, idx))
            continue

        c_low = str(col).strip().lower()
        c_norm = re.sub(r"[^a-z0-9$€£]+", " ", c_low).strip()
        words = set(c_norm.split())
        score = 0

        # Strongly penalize Case Pack / Qty / Case Price / MSRP / Retail / Amazon / Fee columns
        if any(w in words for w in ("qty", "quantity", "pack", "pk", "stock", "available", "moq", "min", "minimum", "rank", "bsr", "offers", "weight", "upc", "ean", "asin", "sku", "id")):
            score -= 120
        if any(phrase in c_norm for phrase in ("case pack", "master pack", "inner pack", "case qty", "box qty", "pack size", "package quantity")):
            score -= 150
        if any(phrase in c_norm for phrase in ("case price", "case cost", "box price", "master case", "ext price", "extended price", "total price", "total cost")):
            score -= 80
        if any(w in words for w in ("msrp", "retail", "srp", "map", "list", "sell", "buybox", "fba", "fbm", "profit", "margin", "roi", "fee", "proceeds", "revenue")):
            score -= 90

        # Positive header matching for unit wholesale cost
        if c_norm in ("cost", "unit cost", "unit price", "wholesale cost", "wholesale price", "your cost", "your price", "net cost", "net price", "item cost", "item price", "each", "ea price", "fob", "price"):
            score += 100
        elif any(phrase in c_norm for phrase in ("unit cost", "unit price", "wholesale cost", "wholesale price", "your cost", "your price", "net price", "net cost", "single price", "each price", "piece price", "pc price")):
            score += 90
        elif "wholesale" in words or "cost" in words or "fob" in words:
            score += 75
        elif "price" in words or "net" in words or "each" in words or "ea" in words or "$" in c_norm:
            score += 60
        elif any(k in c_low for k in ("cost", "price", "wholesale")):
            score += 45

        # Inspect sample values for currency/decimal price patterns vs integer case packs (like 144, 72, 48)
        vals = [str(v).strip() for v in sample_df.iloc[:, idx].dropna() if str(v).strip().lower() not in ("", "nan", "none")]
        if vals:
            price_like = 0
            decimal_like = 0
            for v in vals[:15]:
                m = re.match(r"^[$€£]?\s*(\d{1,5}(?:\.\d{1,4})?)$", v.replace(",", ""))
                if m:
                    num = float(m.group(1))
                    if 0 < num < 5000:
                        price_like += 1
                        if "." in v or "$" in v or "€" in v or "£" in v:
                            decimal_like += 1
            n_checked = len(vals[:15])
            if price_like / n_checked >= 0.6:
                score += 25
            if decimal_like / n_checked >= 0.4:
                score += 35

        cost_scores.append((score, -idx, idx))

    best_cost_idx = max(cost_scores)[2] if cost_scores else (1 if num_cols > 1 and best_upc_idx == 0 else 0)
    return best_upc_idx, best_cost_idx


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
                    df = pd.read_csv(uploaded_file, encoding=encoding, dtype=str)
                    return _promote_header_row_if_needed(df)
                except UnicodeDecodeError:
                    continue
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, dtype=str)
            return _promote_header_row_if_needed(df)
        else:
            if hasattr(uploaded_file, "seek"):
                uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, dtype=str)
            return _promote_header_row_if_needed(df)
    except Exception as e:
        raise ValueError(f"Failed to load supplier file: {e}")
