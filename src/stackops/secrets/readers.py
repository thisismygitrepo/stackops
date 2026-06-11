import json

from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.types import Login


def read_quick_password() -> str:
    from stackops.secrets import search_logins

    secrets = search_logins(path=SECRETS_DOFILE, login_name="quickPassword", keys=("PASSWORD",))
    if not secrets:
        expected_entry: Login = {
            "name": "quickPassword",
            "secrets": [
                {
                    "name": "credentials",
                    "tags": [],
                    "scopes": [],
                    "keyValues": {
                        "PASSWORD": "<quick-password>",
                    },
                }
            ],
        }
        raise ValueError(
            "No quick password entry found in StackOps secrets.\n"
            f"Expected {SECRETS_DOFILE} to contain a login entry shaped like:\n"
            + json.dumps(expected_entry, indent=2)
        )
    if len(secrets) > 1:
        raise ValueError(f"Multiple quick password entries found in StackOps secrets: {SECRETS_DOFILE}")
    password = secrets[0]["secrets"][0]["keyValues"]["PASSWORD"]
    if not isinstance(password, str):
        raise TypeError("Secret value at quickPassword.PASSWORD must be a string.")
    return password


def read_virus_total_api_key() -> str:
    from stackops.secrets import search_logins

    secrets = search_logins(path=SECRETS_DOFILE, login_name="virusTotal", keys=("API_KEY",))
    if not secrets:
        expected_entry: Login = {
            "name": "virusTotal",
            "secrets": [
                {
                    "name": "api-key",
                    "tags": [],
                    "scopes": [],
                    "keyValues": {
                        "API_KEY": "<virus-total-api-key>",
                    },
                }
            ],
        }
        raise ValueError(
            "No VirusTotal API key entry found in StackOps secrets.\n"
            f"Expected {SECRETS_DOFILE} to contain a login entry shaped like:\n"
            + json.dumps(expected_entry, indent=2)
        )
    if len(secrets) > 1:
        raise ValueError(f"Multiple VirusTotal API key entries found in StackOps secrets: {SECRETS_DOFILE}")
    api_key = secrets[0]["secrets"][0]["keyValues"]["API_KEY"]
    if not isinstance(api_key, str):
        raise TypeError("Secret value at virusTotal.API_KEY must be a string.")
    return api_key
