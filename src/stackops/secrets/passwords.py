from typing import cast

import typer

from stackops.secrets.paths import SECRETS_DOFILE
from stackops.secrets.search import search_logins


def read_named_password(*, password_name: str) -> str:
    normalized_name = password_name.strip()
    if normalized_name == "":
        raise ValueError("--password-name must be non-empty.")

    matches = search_logins(path=SECRETS_DOFILE, login_name=normalized_name, keys=("PASSWORD",))
    if not matches:
        raise ValueError(f"No StackOps secrets login named {normalized_name!r} contains a PASSWORD value.")

    selected_login = matches[0]
    if len(matches) > 1:
        typer.echo(f"Multiple PASSWORD values matched StackOps secrets login {normalized_name!r}:")
        for index, login in enumerate(matches, start=1):
            secret = login["secrets"][0]
            account_name = login.get("accountName")
            account_label = "" if account_name is None else f" / account {account_name}"
            typer.echo(f"  {index}. {login['name']} / {secret['name']}{account_label}")
        selected_number = cast(int, typer.prompt("Select password", type=int))
        if not 1 <= selected_number <= len(matches):
            raise ValueError(f"Password selection must be between 1 and {len(matches)}.")
        selected_login = matches[selected_number - 1]

    password = selected_login["secrets"][0]["keyValues"]["PASSWORD"]
    if not isinstance(password, str):
        raise TypeError(f"StackOps secrets PASSWORD value for {normalized_name!r} must be a string.")
    if password == "":
        raise ValueError(f"StackOps secrets PASSWORD value for {normalized_name!r} must be non-empty.")
    return password
