# 📦 Amazon Wholesale Catalog Analyzer (`amztools`)

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![API](https://img.shields.io/badge/Amazon-SP--API-FF9900.svg)](https://developer-docs.amazon.com/sp-api/)
[![Format](https://img.shields.io/badge/Format-Target%2052--Column%20Standard-success.svg)]()

An enterprise-grade wholesale catalog analysis and unit-economics decision engine for Amazon FBA sellers. Upload raw supplier manifests (CSV or Excel) and instantly retrieve live Amazon catalog matches, Buy Box competition, size tiers, FBA fulfillment fees, category referral fees, estimated sales velocity, net profits, and margins. Export executive-ready reports strictly compliant with the **Target 52-Column Wholesale Format**.

---

## 🌟 Key Features

- **📂 Multi-Format Supplier Ingestion**: Supports `.csv`, `.xlsx`, and `.xls`. Intelligently auto-detects and preserves leading zeros for barcodes (UPC, EAN, GTIN, ASIN) with smart column auto-mapping.
- **🧪 Dual Execution Modes**:
  - **Live Amazon SP-API Mode**: Connects directly to Amazon's Selling Partner API (Catalog Items API `2022-04-01` & Product Pricing API) using Login with Amazon (LWA) credentials across global marketplaces (US, UK, DE, CA, FR, IT, ES, JP).
  - **Demo / Simulation Mode**: Built-in high-fidelity simulation engine with verified wholesale catalog entries and deterministic simulation for offline evaluation and UI testing.
- **💰 Precision Financial & Fee Modeling**:
  - **Amazon FBA Fees**: Automatic calculation based on dimensions and weight across standard size tiers (Small Standard, Large Standard, Low-Price FBA eligibility for items $\le \$10.00$, and Hazmat surcharges).
  - **Category-Based Referral Fees**: Automated detection of fee schedules (e.g., Beauty & Personal Care 8%/15% split at \$10.00, Grocery 8%/15% at \$15.00, Electronics 8%/15% at \$100.00) with a standard \$0.30 floor.
  - **Custom Landed Cost Variables**: Custom inputs for Inbound Placement Fees, Inbound Shipping estimates, and VAT percentages.
  - **Automated Profitability Analysis**: Instant computation of Seller Proceeds, Net Profit (\$), Profit Margin (%), ROI (%), and Break-Even Sell Price.
- **📈 BSR & Sales Velocity Estimation**: Category-calibrated power-law regression model converting Amazon Best Sellers Rank (BSR) into estimated monthly unit sales and revenue.
- **📊 Interactive Streamlit Analytics Dashboard**:
  - KPI summary cards (Total Analyzed, Listed on Amazon, Profitable Leads, Average ROI, Top Profit Lead).
  - Multi-dimensional lead filtering by minimum profit, minimum ROI slider, category dropdown, and profitable-only toggle.
- **📑 Executive Excel Export (Target Format)**:
  - Generates custom styled `.xlsx` workbooks adhering to the **Target 52-Column Standard** (extended to 62 columns for deep analytics).
  - Enforces strict single-line 20pt row heights (no bloated rows; linebreaks converted to inline dividers).
  - Professional corporate navy styling, freeze panes, auto-filters, zebra striping, and cell-specific number/currency/percentage formatting.
  - One-click CSV export option.

---

## 🏗️ Multi-Module Architecture

The project is structured into four decoupled, extensible modules:

```
amztools/
├── streamlit_app.py            # Streamlit root entrypoint (Module 1 launcher)
├── main.py                     # CLI & programmatic launcher
├── requirements.txt            # Annotated dependencies
├── .env.example                # SP-API & Cloudflare D1 environment template
├── sample_supplier_catalog.csv # Sample catalog for testing
├── Target_Data_and_format.xlsx # Reference spreadsheet defining the 52-column layout
│
├── modules/
│   ├── __init__.py             # Multi-module package registry
│   │
│   ├── entrypoint/             # ================= MODULE 1: ENTRYPOINT =================
│   │   ├── __init__.py         # Module 1 exports
│   │   ├── router.py           # Application state router & cross-module dispatcher
│   │   └── ui.py               # Streamlit top navigation & multi-module layout frame
│   │
│   ├── analyzer/               # ================= MODULE 2: ANALYZE & PREPARE DATA =================
│   │   ├── __init__.py         # Module 2 exports
│   │   ├── config.py           # Amazon SP-API marketplaces & regional endpoints
│   │   ├── file_loader.py      # Supplier catalog ingestion (CSV/Excel)
│   │   ├── sp_api_client.py    # Amazon SP-API live client & Demo simulation engine
│   │   ├── demo_data.py        # Realistic simulation fixtures & category datasets
│   │   ├── analytics.py        # Unit economics: FBA fees, referral fees, BSR velocity, margins
│   │   ├── excel_exporter.py   # Target 52-column styled Excel workbook generator
│   │   └── ui.py               # Streamlit catalog analysis & export interface
│   │
│   ├── uploader/               # ================= MODULE 3: UPLOAD TO CLOUDFLARE D1 =================
│   │   ├── __init__.py         # Module 3 exports
│   │   ├── config.py           # Cloudflare D1 credentials & batch settings
│   │   ├── schema.sql          # Cloudflare D1 SQLite DDL schema (52 fields + indexes)
│   │   ├── d1_client.py        # Cloudflare D1 HTTP REST API client
│   │   ├── file_parser.py      # Module 2 output validator & row sanitizer
│   │   ├── uploader_service.py # Batch ingestion pipeline & parameterized upsert engine
│   │   └── ui.py               # Streamlit database upload interface
│   │
│   └── crud/                   # ================= MODULE 4: DATABASE CRUD & VIEWER =================
│       ├── __init__.py         # Module 4 exports
│       ├── models.py           # Strongly-typed product entities & filter criteria
│       ├── crud_service.py     # D1 SQL CRUD engine (Fetch, Insert, Update, Delete)
│       └── ui.py               # Streamlit interactive database browser & editor
│
└── tests/                      # Automated unit test suite
    ├── test_analytics.py       # FBA fees, referral fees, BSR velocity, profit math
    ├── test_file_loader.py     # CSV/Excel parsing and barcode leading zero retention
    ├── test_sp_api_client.py   # SP-API identifiers and simulation engine
    ├── test_excel_exporter.py  # 52-column Target format Excel generation
    ├── test_uploader.py        # D1 ingestion parsing and validation
    └── test_crud_models.py     # Router navigation and D1 product data models
```

### Module Implementation Status:
1. **Module 1 (Entrypoint)**: Main navigation hub and cross-module routing. [✅ Complete]
2. **Module 2 (Analyze & Prepare Data)**: Supplier catalog analysis, Amazon SP-API/Demo matching, and Target Excel export. [✅ Complete]
3. **Module 3 (Data Upload to Database)**: Cloudflare D1 REST client, batch upsert pipeline, and schema synchronization. [✅ Complete]
4. **Module 4 (Database CRUD Operation)**: Cloudflare D1 query engine, KPI dashboard, product editor, and lead search. [✅ Complete]


---

## 📋 Target 52-Column Specification

The export workbook conforms to the enterprise Target Wholesale standard:

| Category | Key Columns Included |
| :--- | :--- |
| **Identifiers** | `ASIN`, `Parent ASIN`, `Product ID` (UPC/EAN), `Brand`, `Manufacturer`, `Model`, `Part Number` |
| **Listing Status** | `Title`, `Package Quantity`, `Amazon Link`, `Color`, `Is Hazmat`, `Is Top Level Category`, `Last Run` |
| **Eligibility & Gate** | `Brand Restriction`, `Selling Restriction`, `Selling Restriction Link` |
| **Sales & Velocity** | `Sales Rank`, `Sub Category`, `Sub Category Sales Rank`, `Current Est Sales`, `Estimated Monthly Revenue ($)` |
| **Market Pricing** | `Cost`, `Sell Price`, `Buybox Landed`, `Lowest FBA`, `Lowest FBM`, `BuyBox Contention`, `Total Offers`, `New FBA Offers`, `New FBM Offers` |
| **Fulfillment & Fees** | `FBA Pick & Pack Fee ($)`, `Inbound Placement Fee`, `Fulfillment Subtotal`, `Inbound Shipping Estimate`, `Package Dimensions (in)`, `Package Weight (lb)` |
| **Referral & Taxes** | `Referral Fee %`, `Referral Fee`, `VAT %`, `VAT $`, `Cost Subtotal` |
| **Profitability** | `Seller Proceeds`, `Profit ($)`, `Margin (%)`, `ROI (%)`, `Break Even Sell Price` |
| **Product Media** | `Product Image link 1` through `Product Image link 5` |
| **Reviews & Intel** | `Average Rating`, `Total Review Count`, `Customer Reviews`, `About this item`, `Keepa`, `CamelCC`, `Wholesaller Company Name` |

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.9 or higher
- Git

### 2. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/Md-Imtiaz-Hossain/amztools.git
cd amztools

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Streamlit Application

```bash
streamlit run streamlit_app.py
```

The app will open automatically in your browser at `http://localhost:8501`.

---

## 💡 How to Use

1. **Select Execution Mode**:
   - **Demo / Simulation Mode**: No credentials required. Ideal for exploring features, reviewing UI capabilities, and testing exports using either the built-in sample catalog or custom supplier lists.
   - **Live Amazon SP-API Mode**: Provide your Login with Amazon (LWA) credentials in the sidebar to fetch live data from Amazon.
2. **Configure Economics**:
   - Enable or override auto-calculated FBA fees.
   - Set Inbound Placement Fee per unit, Inbound Shipping, and VAT % (if applicable).
3. **Enter Supplier Details**:
   - Provide the **Wholesaller Company Name** (e.g., `Acme Wholesale Supplies LLC`).
4. **Upload or Load Catalog**:
   - Upload your supplier `.csv` or `.xlsx` file, or click **📄 Load Sample Catalog**.
   - Map your catalog's columns for `Product ID (UPC/EAN/ASIN)` and `Wholesale Cost`.
5. **Run Analysis**:
   - Click **🚀 Run Catalog Analysis**. The system will match items, calculate unit economics, and display interactive charts and KPI metrics.
6. **Filter & Export**:
   - Filter leads by minimum ROI, minimum profit, or category.
   - Click **📥 Download Full Target Analysis (Excel .xlsx)** for the formatted workbook or **📄 Download Analysis Report (CSV)** for raw tabular data.

---

## 🔐 Amazon SP-API Configuration (Live Mode)

To use live Amazon data, register an Amazon Selling Partner developer account and create an LWA app:
1. Go to **Developer Central** in Amazon Seller Central.
2. Register your application to obtain:
   - **LWA Client ID** (`amzn1.application-oa2-client.xxx`)
   - **LWA Client Secret**
   - **LWA Refresh Token** (`Atzr|...`)
3. Select your target marketplace in the sidebar (US, UK, DE, CA, FR, IT, ES, JP).
4. Click **Test SP-API Connection** to verify your credentials.

---

## 🛠️ Testing & Verification

Run the automated test suite covering all modules:

```bash
# Run all unit and integration tests
python -m unittest discover tests
```

Or verify that all module packages load cleanly:

```bash
python -c "
from modules.entrypoint import AppRouter
from modules.analyzer import load_supplier_file, calculate_comprehensive_financials, export_to_target_excel
from modules.uploader import CloudflareD1Client, D1UploaderService
from modules.crud import D1CrudService
print('All modules loaded successfully!')
"
```

---

## 📄 License

This project is licensed under the terms described in the [LICENSE](LICENSE) file.
