"""
Module 3: Data Upload to Database - Cloudflare D1 Configuration
===============================================================
Purpose:
    Stores and validates configuration parameters required to authenticate
    and interact with Cloudflare D1 SQLite database via Cloudflare REST API.

API Reference:
    Cloudflare D1 Query API:
    POST https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query
    Headers:
        Authorization: Bearer <CLOUDFLARE_API_TOKEN>
        Content-Type: application/json
"""

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


@dataclass
class CloudflareD1Config:
    """
    Configuration dataclass for Cloudflare D1 Database connectivity.

    Attributes:
        account_id (str): Cloudflare Account ID (32-character hex string).
        database_id (str): Cloudflare D1 Database UUID.
        api_token (str): Cloudflare API Token with D1 Edit permissions.
        batch_size (int): Number of rows per batch query (default: 50 to respect SQLite parameter limits).
        timeout_seconds (int): HTTP request timeout in seconds.
    """
    account_id: str = ""
    database_id: str = ""
    api_token: str = ""
    batch_size: int = 50
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "CloudflareD1Config":
        """
        Load configuration from environment variables or .env file.
        """
        if load_dotenv:
            if env_path and os.path.exists(env_path):
                load_dotenv(env_path, override=True)
            else:
                load_dotenv(override=False)

        return cls(
            account_id=os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip(),
            database_id=os.environ.get("CLOUDFLARE_DATABASE_ID", "").strip(),
            api_token=os.environ.get("CLOUDFLARE_API_TOKEN", "").strip(),
            batch_size=int(os.environ.get("CLOUDFLARE_D1_BATCH_SIZE", 50)),
            timeout_seconds=int(os.environ.get("CLOUDFLARE_D1_TIMEOUT", 30)),
        )



    @property
    def query_endpoint_url(self) -> str:
        """
        Constructs the standard Cloudflare D1 REST query URL.

        Returns:
            str: https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query
        """
        clean_acc = self.account_id.strip()
        clean_db = self.database_id.strip()
        return f"https://api.cloudflare.com/client/v4/accounts/{clean_acc}/d1/database/{clean_db}/query"

    def is_valid(self) -> bool:
        """
        Validates whether all mandatory credentials have been provided.
        """
        return bool(self.account_id.strip() and self.database_id.strip() and self.api_token.strip())
