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
    from dotenv import load_dotenv, set_key
except ImportError:
    load_dotenv = None
    set_key = None


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

    def save_to_env(self, env_path: str = ".env") -> bool:
        """
        Persist credentials into a .env file for future sessions.
        """
        try:
            if not os.path.exists(env_path):
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("# Cloudflare D1 Configuration\n")

            if set_key:
                set_key(env_path, "CLOUDFLARE_ACCOUNT_ID", self.account_id)
                set_key(env_path, "CLOUDFLARE_DATABASE_ID", self.database_id)
                set_key(env_path, "CLOUDFLARE_API_TOKEN", self.api_token)
                set_key(env_path, "CLOUDFLARE_D1_BATCH_SIZE", str(self.batch_size))
                return True
            else:
                # Fallback manual write
                lines = []
                if os.path.exists(env_path):
                    with open(env_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                
                keys_to_update = {
                    "CLOUDFLARE_ACCOUNT_ID": self.account_id,
                    "CLOUDFLARE_DATABASE_ID": self.database_id,
                    "CLOUDFLARE_API_TOKEN": self.api_token,
                    "CLOUDFLARE_D1_BATCH_SIZE": str(self.batch_size),
                }

                new_lines = []
                updated_keys = set()
                for line in lines:
                    matched = False
                    for k, v in keys_to_update.items():
                        if line.startswith(f"{k}="):
                            new_lines.append(f"{k}={v}\n")
                            updated_keys.add(k)
                            matched = True
                            break
                    if not matched:
                        new_lines.append(line)

                for k, v in keys_to_update.items():
                    if k not in updated_keys:
                        new_lines.append(f"{k}={v}\n")

                with open(env_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
                return True
        except Exception:
            return False

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
