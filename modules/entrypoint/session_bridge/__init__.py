"""
SessionStorage Bridge for Ephemeral In-Browser Credential Management
===================================================================
Purpose:
    Bridges Streamlit with the browser's native window.sessionStorage.
    - Credentials exist strictly in browser process memory for the active tab.
    - Survives page refreshes (Cmd+R / F5) during development.
    - Automatically deleted by the browser when the tab or window is closed.
    - Never written to disk or .env files.
"""

import os
from typing import Any, Dict, List, Optional
import streamlit as st
import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
_bridge_component = components.declare_component("session_storage_bridge", path=_FRONTEND_DIR)

TRACKED_CREDENTIAL_KEYS: List[str] = [
    "sp_client_id",
    "sp_client_secret",
    "sp_refresh_token",
    "cf_account_id",
    "cf_database_id",
    "cf_api_token",
    "wholesaler_company_name",
]


def sync_session_credentials(
    save_keys: Optional[Dict[str, Any]] = None,
    clear_all: bool = False,
) -> Dict[str, str]:
    """
    Synchronizes credentials between Streamlit session state and browser sessionStorage.

    Args:
        save_keys: Optional dictionary of key/value pairs to save into sessionStorage.
        clear_all: If True, deletes all keys from browser sessionStorage.

    Returns:
        Dict[str, str]: Currently stored credentials retrieved from browser sessionStorage.
    """
    # Check if a clear action was requested via button
    if clear_all or st.session_state.get("trigger_session_clear"):
        st.session_state["trigger_session_clear"] = False
        action = "clear"
        payload_save = {}
    else:
        action = "sync"
        # Collect any active credentials in session state to persist in sessionStorage
        payload_save = {}
        for k in TRACKED_CREDENTIAL_KEYS:
            val = st.session_state.get(k)
            if val is not None and str(val).strip() != "":
                payload_save[k] = str(val).strip()
        if save_keys:
            payload_save.update(save_keys)

    try:
        res = _bridge_component(
            action=action,
            save_keys=payload_save,
            read_keys=TRACKED_CREDENTIAL_KEYS,
            default={"cleared": False, "values": {}},
            key="amztools_session_storage_bridge_widget",
        )
    except Exception:
        # Fallback if component rendering is in headless testing environment
        res = {"cleared": False, "values": {}}

    if res and isinstance(res, dict):
        if res.get("cleared"):
            return {}
        stored_values = res.get("values", {})
        if isinstance(stored_values, dict):
            # Populate session state if not already set
            for k, v in stored_values.items():
                if v and not st.session_state.get(k):
                    st.session_state[k] = v
            return stored_values

    return {}


def clear_all_credentials() -> None:
    """
    Purges all credentials from both Python session state and browser sessionStorage.
    """
    for k in TRACKED_CREDENTIAL_KEYS:
        st.session_state[k] = ""
    st.session_state["trigger_session_clear"] = True


__all__ = [
    "TRACKED_CREDENTIAL_KEYS",
    "sync_session_credentials",
    "clear_all_credentials",
]
