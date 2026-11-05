"""
Module 5: Data Upload to MySQL Remote Database - Configuration
==============================================================
Purpose:
    Stores and validates configuration parameters required to connect and
    authenticate with a remote MySQL database (such as Hostinger MySQL).
"""

import os
from dataclasses import dataclass
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


_PLACEHOLDER_VALUES = {
    "your_mysql_host_here",
    "your_mysql_database_here",
    "your_mysql_user_here",
    "your_mysql_password_here",
}


def _clean_env_val(key: str, default: str = "") -> str:
    val = os.environ.get(key, default).strip()
    if val in _PLACEHOLDER_VALUES:
        return default
    return val


@dataclass
class MySQLDatabaseConfig:
    """
    Configuration dataclass for Remote MySQL Database connectivity.

    Attributes:
        host (str): MySQL Server Hostname or IP address (e.g. srv1570.hstgr.io or 82.197.82.58).
        port (int): MySQL Server TCP Port (default: 3306).
        database (str): MySQL Database Name (e.g. u742113797_re_D2AKZzTX).
        user (str): MySQL Username (e.g. u742113797_re_D2AKZzTX).
        password (str): MySQL Password.
        batch_size (int): Number of rows per executemany batch query (default: 100).
        timeout_seconds (int): Connection and read/write timeout in seconds (default: 30).
    """
    host: str = ""
    port: int = 3306
    database: str = ""
    user: str = ""
    password: str = ""
    batch_size: int = 100
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "MySQLDatabaseConfig":
        """
        Load MySQL configuration from environment variables or .env file.
        """
        if load_dotenv:
            if env_path and os.path.exists(env_path):
                load_dotenv(env_path, override=True)
            else:
                load_dotenv(override=False)

        raw_port = _clean_env_val("MYSQL_PORT", "3306")
        try:
            port_val = int(raw_port)
        except ValueError:
            port_val = 3306

        raw_batch = _clean_env_val("MYSQL_BATCH_SIZE", "100")
        try:
            batch_val = int(raw_batch)
        except ValueError:
            batch_val = 100

        raw_timeout = _clean_env_val("MYSQL_TIMEOUT", "30")
        try:
            timeout_val = int(raw_timeout)
        except ValueError:
            timeout_val = 30

        return cls(
            host=_clean_env_val("MYSQL_HOST", ""),
            port=port_val,
            database=_clean_env_val("MYSQL_DATABASE", ""),
            user=_clean_env_val("MYSQL_USER", ""),
            password=_clean_env_val("MYSQL_PASSWORD", ""),
            batch_size=batch_val,
            timeout_seconds=timeout_val,
        )

    def is_valid(self) -> bool:
        """
        Validates whether all mandatory MySQL connection parameters are provided.
        """
        return bool(
            self.host.strip()
            and self.database.strip()
            and self.user.strip()
            and self.password.strip()
            and int(self.port or 3306) > 0
        )
