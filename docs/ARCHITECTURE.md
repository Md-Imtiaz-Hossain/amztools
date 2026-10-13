# System Architecture & Maintenance Guide

## Overview

`amztools` (Amazon Wholesale Suite) is designed around a modular, decoupled pipeline architecture. Each module handles a distinct phase in the wholesale catalog lifecycle:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Module 1: Entrypoint & Router                   │
│         (Navigation, Browser Session Storage, Module Dispatching)       │
└───────────────┬───────────────────────────┬────────────────────────────┘
                │                           │
                ▼                           ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│ Module 2: Analyzer & Pricing  │   │ Module 3: Cloudflare D1 Sync  │
│  - Ingest CSV / Excel         │   │  - Schema Verification / DDL  │
│  - SP-API & Simulation Engine │──►│  - Pre-flight Validation      │
│  - Unit Economics & BSR Model │   │  - Smart Slot Batching        │
│  - 52-Column Target Export    │   │  - Live Audit Logs & Toasts   │
└───────────────────────────────┘   └───────────────┬───────────────┘
                                                    │
                                                    ▼
                                    ┌───────────────────────────────┐
                                    │ Module 4: Database CRUD & BI  │
                                    │  - Live Cloudflare D1 Browser │
                                    │  - KPI Statistics Aggregation │
                                    │  - Dynamic Filters & Search   │
                                    │  - Lead Editing & Deletion    │
                                    └───────────────────────────────┘
```

---

## Directory Organization

```
amztools/
├── assets/                  # Static assets & screenshots for documentation
│   └── screenshots/         # Module UI screenshots and banners
├── data/                    # Sample data & reference specifications
│   ├── sample_supplier_catalog.csv
│   └── Target_Data_and_format.xlsx
├── docs/                    # Technical architecture & maintenance guides
│   └── ARCHITECTURE.md
├── modules/                 # Decoupled core application packages
│   ├── entrypoint/          # Module 1: Navigation router & session bridge
│   ├── analyzer/            # Module 2: Ingestion, SP-API, unit economics, Excel export
│   ├── uploader/            # Module 3: Cloudflare D1 REST client, batch ingestion
│   └── crud/                # Module 4: Cloudflare D1 SQL query engine & lead manager
├── tests/                   # Automated unittest suite
├── .github/workflows/       # GitHub Actions CI/CD workflows
├── main.py                  # CLI & programmatic launcher
├── streamlit_app.py         # Streamlit web application root entrypoint
├── pyproject.toml           # PEP 517/518 build configuration & metadata
├── requirements.txt         # Runtime dependencies
├── requirements-dev.txt     # Developer & testing dependencies
├── .env.example             # Environment variable template
└── LICENSE                  # MIT License
```

---

## Maintenance & Extension Guidelines

### 1. Adding a New Marketplace to Module 2
- Open `modules/analyzer/config.py`.
- Add the marketplace code and Amazon Marketplace ID to `MARKETPLACE_MAP`.
- If currency conversion or special VAT rates apply, configure fee overrides in `modules/analyzer/analytics.py`.

### 2. Adding a New Column to the 52-Column Wholesale Schema
When adding a new data field:
1. **Target Columns List**: Update `TARGET_COLUMNS` in `modules/analyzer/sp_api_client.py`.
2. **Excel Exporter**: Add column width and formatting rules in `modules/analyzer/excel_exporter.py`.
3. **Database Schema**: Add the column to `modules/uploader/schema.sql`.
4. **Header Mapping**: Add the column mapping to `TARGET_TO_SQL_COLUMN_MAP` in `modules/uploader/file_parser.py`.
5. **Data Model**: Add the field to `WholesaleProductModel` in `modules/crud/models.py`.

### 3. Adding a New Module to the Pipeline
To introduce a Module 5 (e.g., automated repricing, purchase order generation, or inventory replenishment):
1. Create `modules/<module_name>/` with `__init__.py`, `ui.py`, and domain services.
2. In `modules/entrypoint/router.py`, add `<MODULE_NAME> = "<module_name>"` to the `ModuleView` enum.
3. In `modules/entrypoint/ui.py`, add the radio option and conditionally dispatch to your module's UI renderer:
   ```python
   elif current_module == ModuleView.NEW_MODULE:
       from modules.new_module.ui import render_new_module_ui
       render_new_module_ui()
   ```
4. Add corresponding unit tests in `tests/test_<module_name>.py`.

### 4. Running Tests
Run all unit and integration tests using:
```bash
python -m unittest discover tests
```
Or with pytest:
```bash
pytest
```
