import os
import json
import platform
import configparser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests


def get_rclone_token(section: str) -> dict[str, str] | None:
    if platform.system() == "Windows":
        rclone_file_path = Path(os.getenv("APPDATA", "")) / "rclone" / "rclone.conf"
    else:
        rclone_file_path = Path.home() / ".config" / "rclone" / "rclone.conf"
    if rclone_file_path.exists():
        config = configparser.ConfigParser()
        config.read(rclone_file_path)
        if section in config:
            results = config[section]
            return dict(results)
    return None


_cached_config: dict[str, Any] | None = None


def get_config(section: str) -> dict[str, Any]:
    global _cached_config
    if _cached_config is None:
        rclone_config = get_rclone_token(section)
        if not rclone_config:
            raise Exception(f"Could not find rclone config section '{section}'. Please set up rclone first.")
        token_str = rclone_config.get("token", "{}")
        try:
            token_data = json.loads(token_str)
        except json.JSONDecodeError:
            raise Exception(f"Invalid token format in rclone config section '{section}'")
        _cached_config = {"token": token_data, "drive_id": rclone_config.get("drive_id"), "drive_type": rclone_config.get("drive_type", "personal")}
    return _cached_config


def get_token(section: str) -> dict[str, Any]:
    return get_config(section)["token"]


def get_drive_id(section: str) -> str | None:
    return get_config(section)["drive_id"]


def get_drive_type(section: str) -> str:
    return get_config(section)["drive_type"]


def clear_config_cache() -> None:
    global _cached_config
    _cached_config = None


CLIENT_ID: str = os.getenv("ONEDRIVE_CLIENT_ID", "your_client_id_here")
CLIENT_SECRET: str = os.getenv("ONEDRIVE_CLIENT_SECRET", "your_client_secret_here")
REDIRECT_URI: str = os.getenv("ONEDRIVE_REDIRECT_URI", "http://localhost:8080/callback")

GRAPH_API_BASE: str = "https://graph.microsoft.com/v1.0"
OAUTH_TOKEN_ENDPOINT: str = "https://login.microsoftonline.com/common/oauth2/v2.0/token"


def is_token_valid(section: str) -> bool:
    try:
        token = get_token(section)
        expiry_str = token.get("expiry")
        if not expiry_str:
            return False
        if "+" in expiry_str:
            expiry_str = expiry_str.split("+")[0]
        elif "Z" in expiry_str:
            expiry_str = expiry_str.replace("Z", "")
        expiry_time = datetime.fromisoformat(expiry_str)
        current_time = datetime.now()
        return expiry_time > current_time + timedelta(minutes=5)
    except Exception as e:
        print(f"Error checking token validity: {e}")
        return False


def save_token_to_file(token_data: dict[str, Any], file_path: str) -> bool:
    try:
        token_file_path = Path(file_path)
        token_file_path.parent.mkdir(parents=True, exist_ok=True)
        token_file_path.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
        os.chmod(token_file_path, 0o600)
        print(f"💾 Token saved to: {token_file_path}")
        return True
    except Exception as e:
        print(f"❌ Error saving token: {e}")
        return False


def load_token_from_file(file_path: str) -> dict[str, Any] | None:
    try:
        token_file_path = Path(file_path)
        if token_file_path.exists():
            token_data = json.loads(token_file_path.read_text(encoding="utf-8"))
            global _cached_config
            if _cached_config is not None:
                _cached_config["token"] = token_data
            else:
                clear_config_cache()
            print(f"📂 Token loaded from: {token_file_path}")
            return token_data
        else:
            print(f"ℹ️  No saved token file found at: {token_file_path}")
            return None
    except Exception as e:
        print(f"❌ Error loading token: {e}")
        return None


DEFAULT_TOKEN_FILE: str = os.path.expanduser("~/.onedrive_token.json")


def refresh_access_token(section: str) -> dict[str, Any] | None:
    token = get_token(section)
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        print("ERROR: No refresh token available!")
        return None

    print("🔄 Refreshing access token...")
    data: dict[str, str] = {
        "client_id": CLIENT_ID,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "scope": "https://graph.microsoft.com/Files.ReadWrite.All offline_access",
    }
    if CLIENT_SECRET and CLIENT_SECRET != "your_client_secret_here":
        data["client_secret"] = CLIENT_SECRET

    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(OAUTH_TOKEN_ENDPOINT, data=data, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            expires_in = token_data.get("expires_in", 3600)
            expiry_time = datetime.now() + timedelta(seconds=expires_in)
            new_token: dict[str, Any] = {
                "access_token": token_data["access_token"],
                "token_type": token_data.get("token_type", "Bearer"),
                "refresh_token": token_data.get("refresh_token", refresh_token),
                "expiry": expiry_time.isoformat(),
            }
            global _cached_config
            if _cached_config is not None:
                _cached_config["token"] = new_token
            else:
                clear_config_cache()
            print("✅ Access token refreshed successfully!")
            print(f"🕒 New token expires at: {expiry_time}")
            save_token_to_file(new_token, file_path=DEFAULT_TOKEN_FILE)
            return new_token
        else:
            print(f"❌ Token refresh failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error refreshing token: {e}")
        return None


def get_access_token(section: str) -> str | None:
    load_token_from_file(file_path=DEFAULT_TOKEN_FILE)
    if not is_token_valid(section):
        print("🔄 Access token has expired, attempting to refresh...")
        refreshed_token = refresh_access_token(section)
        if refreshed_token:
            return refreshed_token["access_token"]
        else:
            print("❌ Failed to refresh token automatically!")
            print("\n🔧 You have two options:")
            print("1. Run setup_oauth_authentication() to set up OAuth")
            print("2. Update your rclone token by running: rclone config reconnect odp")
            return None
    token = get_token(section)
    return token.get("access_token")


def make_graph_request(method: str, endpoint: str, section: str, **kwargs: Any) -> requests.Response:
    token = get_access_token(section)
    if not token:
        raise Exception("Failed to get valid access token")
    headers: dict[str, str] = kwargs.get("headers", {})
    headers["Authorization"] = f"Bearer {token}"
    kwargs["headers"] = headers
    url = f"{GRAPH_API_BASE}/{endpoint.lstrip('/')}"
    response = requests.request(method, url, **kwargs)
    return response


def get_authorization_url() -> str:
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "response_mode": "query",
        "scope": "https://graph.microsoft.com/Files.ReadWrite.All offline_access",
        "state": "onedrive_auth",
    }
    auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(params)}"
    return auth_url


def exchange_authorization_code(authorization_code: str) -> dict[str, Any] | None:
    data: dict[str, str] = {
        "client_id": CLIENT_ID,
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
        "scope": "https://graph.microsoft.com/Files.ReadWrite.All offline_access",
    }
    if CLIENT_SECRET and CLIENT_SECRET != "your_client_secret_here":
        data["client_secret"] = CLIENT_SECRET
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        response = requests.post(OAUTH_TOKEN_ENDPOINT, data=data, headers=headers)
        if response.status_code == 200:
            token_data = response.json()
            expires_in = token_data.get("expires_in", 3600)
            expiry_time = datetime.now() + timedelta(seconds=expires_in)
            new_token: dict[str, Any] = {
                "access_token": token_data["access_token"],
                "token_type": token_data.get("token_type", "Bearer"),
                "refresh_token": token_data["refresh_token"],
                "expiry": expiry_time.isoformat(),
            }
            global _cached_config
            if _cached_config is not None:
                _cached_config["token"] = new_token
            else:
                clear_config_cache()
            save_token_to_file(new_token, file_path=DEFAULT_TOKEN_FILE)
            print("✅ Initial tokens obtained successfully!")
            return new_token
        else:
            print(f"❌ Token exchange failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error exchanging authorization code: {e}")
        return None


def setup_oauth_authentication() -> None:
    print("🔧 Setting up OneDrive OAuth Authentication")
    print("=" * 50)
    if CLIENT_ID == "your_client_id_here":
        print("❌ You need to set up Azure App Registration first!")
        print("\n📋 Setup Instructions:")
        print("1. Go to https://portal.azure.com")
        print("2. Navigate to 'Azure Active Directory' > 'App registrations'")
        print("3. Click 'New registration'")
        print("4. Set Name: 'OneDrive API Access'")
        print("5. Set Redirect URI: http://localhost:8080/callback")
        print("6. After creation, copy the 'Application (client) ID'")
        print("7. Go to 'API permissions' > 'Add permission' > 'Microsoft Graph'")
        print("8. Add 'Files.ReadWrite.All' and 'offline_access' permissions")
        print("9. Set environment variables:")
        print("   export ONEDRIVE_CLIENT_ID='your_client_id'")
        print("   export ONEDRIVE_REDIRECT_URI='http://localhost:8080/callback'")
        return
    print(f"Using Client ID: {CLIENT_ID}")
    print(f"Redirect URI: {REDIRECT_URI}")
    auth_url = get_authorization_url()
    print("\n🌐 Please visit this URL to authorize the application:")
    print(f"{auth_url}")
    print("\n📋 After authorization, you'll be redirected to:")
    print(f"{REDIRECT_URI}?code=AUTHORIZATION_CODE&state=onedrive_auth")
    print("\n🔑 Copy the 'code' parameter from the URL and paste it below:")
    auth_code = input("Authorization Code: ").strip()
    if auth_code:
        token_data = exchange_authorization_code(auth_code)
        if token_data:
            print("\n✅ OAuth setup completed successfully!")
            print("🎉 You can now use the OneDrive functions without rclone!")
        else:
            print("\n❌ OAuth setup failed. Please try again.")
    else:
        print("\n❌ No authorization code provided.")
