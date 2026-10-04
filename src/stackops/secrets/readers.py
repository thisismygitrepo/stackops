import json
from dataclasses import dataclass, field

from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.models import Login
from stackops.secrets.search import search_logins


@dataclass(frozen=True, slots=True)
class VirusTotalApiKey:
    account_name: str
    api_key: str = field(repr=False)


def read_quick_password() -> str:
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


def read_virus_total_api_keys() -> tuple[VirusTotalApiKey, ...]:
    secrets = search_logins(path=SECRETS_DOFILE, login_name="virusTotal", keys=("API_KEY",))
    if not secrets:
        raise ValueError("No VirusTotal API keys found in StackOps secrets.")
    api_keys: list[VirusTotalApiKey] = []
    account_names: set[str] = set()
    key_values: set[str] = set()
    for login in secrets:
        account_name = login.get("accountName")
        if not isinstance(account_name, str) or not account_name.strip():
            raise ValueError("Each VirusTotal account must define a non-empty accountName.")
        if len(login["secrets"]) != 1:
            raise ValueError("Each VirusTotal account must match exactly one API key bundle.")
        api_key = login["secrets"][0]["keyValues"]["API_KEY"]
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("Each VirusTotal API_KEY must be a non-empty string.")
        if account_name in account_names:
            raise ValueError("VirusTotal accountName values must be unique.")
        if api_key in key_values:
            raise ValueError("VirusTotal API_KEY values must be unique.")
        account_names.add(account_name)
        key_values.add(api_key)
        api_keys.append(VirusTotalApiKey(account_name=account_name, api_key=api_key))
    return tuple(api_keys)
