"""
Tests for Module 1: SessionStorage Bridge & Security Wipe.
"""

import unittest
from unittest.mock import patch
from modules.entrypoint.session_bridge import (
    TRACKED_CREDENTIAL_KEYS,
    sync_session_credentials,
    clear_all_credentials,
)


class TestSessionBridge(unittest.TestCase):
    def test_tracked_keys_list(self):
        self.assertIn("sp_client_id", TRACKED_CREDENTIAL_KEYS)
        self.assertIn("sp_client_secret", TRACKED_CREDENTIAL_KEYS)
        self.assertIn("sp_refresh_token", TRACKED_CREDENTIAL_KEYS)
        self.assertIn("cf_account_id", TRACKED_CREDENTIAL_KEYS)
        self.assertIn("cf_database_id", TRACKED_CREDENTIAL_KEYS)
        self.assertIn("cf_api_token", TRACKED_CREDENTIAL_KEYS)
        self.assertIn("wholesaler_company_name", TRACKED_CREDENTIAL_KEYS)

    @patch("modules.entrypoint.session_bridge.st")
    def test_clear_all_credentials(self, mock_st):
        session_mock = {
            "sp_client_id": "test_id",
            "cf_api_token": "test_token",
        }
        mock_st.session_state = session_mock
        clear_all_credentials()

        self.assertEqual(session_mock.get("sp_client_id"), "")
        self.assertEqual(session_mock.get("cf_api_token"), "")
        self.assertTrue(session_mock.get("trigger_session_clear"))


if __name__ == "__main__":
    unittest.main()
