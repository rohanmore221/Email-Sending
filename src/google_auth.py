import os
import json
import time
import base64
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional
import requests

from src.config import BASE_DIR

TOKENS_FILE = BASE_DIR / "data" / "google_tokens.json"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile"
]

def get_google_credentials() -> Dict[str, str]:
    """Retrieve Google OAuth Client ID and Secret from environment."""
    client_id = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
    client_secret = (os.getenv("GOOGLE_CLIENT_SECRET") or "").strip()
    redirect_uri = (os.getenv("GOOGLE_REDIRECT_URI") or "http://127.0.0.1:8000/api/auth/google/callback").strip()
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }

def get_authorization_url(state: Optional[str] = None) -> Dict[str, Any]:
    """Generates the Google OAuth 2.0 consent URL."""
    creds = get_google_credentials()
    if not creds["client_id"]:
        return {
            "configured": False,
            "url": None,
            "message": "Google Client ID is missing. Please add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
        }

    params = {
        "client_id": creds["client_id"],
        "redirect_uri": creds["redirect_uri"],
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
    }
    if state:
        params["state"] = state

    query_str = urllib.parse.urlencode(params)
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{query_str}"
    return {
        "configured": True,
        "url": auth_url,
        "redirect_uri": creds["redirect_uri"]
    }

def exchange_code_for_tokens(code: str) -> Dict[str, Any]:
    """Exchanges an authorization code for access and refresh tokens."""
    creds = get_google_credentials()
    if not creds["client_id"] or not creds["client_secret"]:
        raise ValueError("Google Client ID and Secret must be configured in .env.")

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "redirect_uri": creds["redirect_uri"],
        "grant_type": "authorization_code"
    }

    resp = requests.post(token_url, data=payload, timeout=20)
    if resp.status_code != 200:
        err_msg = resp.text
        try:
            err_json = resp.json()
            err_msg = err_json.get("error_description") or err_json.get("error") or resp.text
        except Exception:
            pass
        raise ValueError(f"Token exchange failed: {err_msg}")

    token_data = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in", 3600)
    expires_at = time.time() + expires_in

    # Fetch user profile details
    user_info = {}
    try:
        user_resp = requests.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10
        )
        if user_resp.status_code == 200:
            user_info = user_resp.json()
    except Exception:
        pass

    data_dir = TOKENS_FILE.parent
    data_dir.mkdir(parents=True, exist_ok=True)

    # If new token doesn't include refresh_token, keep previous refresh_token
    if not refresh_token and TOKENS_FILE.exists():
        try:
            with open(TOKENS_FILE, "r", encoding="utf-8") as f:
                prev_data = json.load(f)
                refresh_token = prev_data.get("refresh_token")
        except Exception:
            pass

    save_payload = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        "token_type": token_data.get("token_type", "Bearer"),
        "scope": token_data.get("scope", ""),
        "email": user_info.get("email", ""),
        "name": user_info.get("name", ""),
        "picture": user_info.get("picture", ""),
        "updated_at": time.time()
    }

    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(save_payload, f, indent=2)

    return save_payload

def get_valid_access_token() -> Optional[str]:
    """Returns a valid access token, auto-refreshing via refresh_token if expired."""
    if not TOKENS_FILE.exists():
        return None

    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return None

    expires_at = data.get("expires_at", 0)
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")

    # If valid for at least another 60 seconds, use it
    if access_token and (expires_at - time.time() > 60):
        return access_token

    # Token is expired or expiring soon, refresh it
    if not refresh_token:
        return None

    creds = get_google_credentials()
    if not creds["client_id"] or not creds["client_secret"]:
        return None

    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }

    try:
        resp = requests.post(token_url, data=payload, timeout=20)
        if resp.status_code == 200:
            token_data = resp.json()
            new_access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 3600)
            data["access_token"] = new_access_token
            data["expires_at"] = time.time() + expires_in
            data["updated_at"] = time.time()
            with open(TOKENS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return new_access_token
    except Exception:
        pass

    return None

def get_google_auth_status() -> Dict[str, Any]:
    """Returns the current connection status of Google OAuth."""
    creds = get_google_credentials()
    is_configured = bool(creds["client_id"] and creds["client_secret"])

    if not TOKENS_FILE.exists():
        return {
            "is_connected": False,
            "is_configured": is_configured,
            "client_id_set": bool(creds["client_id"]),
            "email": None,
            "name": None,
            "picture": None
        }

    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        has_token = bool(data.get("access_token") or data.get("refresh_token"))
        return {
            "is_connected": has_token,
            "is_configured": is_configured,
            "client_id_set": bool(creds["client_id"]),
            "email": data.get("email"),
            "name": data.get("name"),
            "picture": data.get("picture"),
            "expires_in_sec": max(0, int(data.get("expires_at", 0) - time.time()))
        }
    except Exception:
        return {
            "is_connected": False,
            "is_configured": is_configured,
            "client_id_set": bool(creds["client_id"]),
            "email": None,
            "name": None,
            "picture": None
        }

def disconnect_google():
    """Removes stored tokens to disconnect the Google account."""
    if TOKENS_FILE.exists():
        try:
            TOKENS_FILE.unlink()
        except Exception:
            pass
