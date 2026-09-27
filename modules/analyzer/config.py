"""
Module 2: Analyze & Prepare Data - Configuration & Marketplaces
===============================================================
Purpose:
    Defines supported Amazon marketplaces and regional endpoints for the
    Amazon Selling Partner API (SP-API).

Marketplace Coverage:
    - North America: US, CA
    - Europe: UK, DE, FR, IT, ES
    - Asia-Pacific: JP
"""

try:
    from sp_api.base import Marketplaces
except ImportError:
    # Fallback placeholder if python-amazon-sp-api is not yet installed in runtime
    class Marketplaces:
        US = "ATVPDKIKX0DER"
        UK = "A1F83G8C2ARO7P"
        DE = "A1PA6795UKMFR9"
        CA = "A2EUQ1WTGCTBG2"
        FR = "A13V1IB3VIYZZH"
        IT = "APJ6JRA9NG5V4"
        ES = "A1RKKUPIHCS9HS"
        JP = "A1VC38T7YXB528"

MARKETPLACE_MAP = {
    "US": Marketplaces.US,
    "UK": Marketplaces.UK,
    "DE": Marketplaces.DE,
    "CA": Marketplaces.CA,
    "FR": Marketplaces.FR,
    "IT": Marketplaces.IT,
    "ES": Marketplaces.ES,
    "JP": Marketplaces.JP,
}
