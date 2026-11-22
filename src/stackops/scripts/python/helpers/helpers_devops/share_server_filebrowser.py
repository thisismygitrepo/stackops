import hashlib
import secrets
import subprocess
from pathlib import Path

import typer

from stackops.utils.source_of_truth import CONFIG_ROOT


def _run_filebrowser(arguments: list[str], database: Path, timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(["filebrowser", *arguments, "--database", str(database)], capture_output=True, text=True, check=False, timeout=timeout)
    except FileNotFoundError:
        typer.echo("❌ ERROR: 'filebrowser' is not installed or not on PATH. Pass --install-dep to install it.", err=True)
        raise typer.Exit(code=1) from None
    except subprocess.TimeoutExpired:
        typer.echo(f"❌ ERROR: 'filebrowser {' '.join(arguments[:2])}' did not finish within {timeout:g} seconds.", err=True)
        raise typer.Exit(code=1) from None


def _require_filebrowser_success(arguments: list[str], database: Path, timeout: float, secret: str) -> str:
    result = _run_filebrowser(arguments=arguments, database=database, timeout=timeout)
    if result.returncode == 0:
        return result.stdout
    output = "\n".join(line for line in f"{result.stdout}\n{result.stderr}".splitlines() if line.strip() != "").replace(secret, "<password>")
    hint = f"\nAnother share of this folder may still be running and holding its database: {database}" if "timeout" in output else ""
    typer.echo(f"❌ ERROR: 'filebrowser {' '.join(arguments[:2])}' failed with exit code {result.returncode}:\n{output}{hint}", err=True)
    raise typer.Exit(code=1)


def prepare_filebrowser_database(root: Path, username: str | None, password: str | None, timeout: float) -> Path:
    # One database per shared folder: share links are stored relative to the served root, and filebrowser locks a database while it serves from it.
    database = CONFIG_ROOT.joinpath("share-server", f"{root.name or 'root'}-{hashlib.sha256(str(root).encode()).hexdigest()[:12]}.db")
    database.parent.mkdir(parents=True, exist_ok=True)
    secret = password if password is not None else secrets.token_urlsafe(24)
    if not database.exists():
        _require_filebrowser_success(arguments=["config", "init"], database=database, timeout=timeout, secret=secret)
    # Builds that enforce a minimum password length name the setting in their help; older builds reject the flag.
    settings_help = _run_filebrowser(arguments=["config", "set", "--help"], database=database, timeout=timeout)
    minimum_length = ["--minimumPasswordLength", "1"] if "--minimumPasswordLength" in f"{settings_help.stdout}{settings_help.stderr}" else []
    if username is None or password is None:
        _require_filebrowser_success(arguments=["config", "set", "--auth.method", "noauth", *minimum_length], database=database, timeout=timeout, secret=secret)
        if _run_filebrowser(arguments=["users", "find", "1"], database=database, timeout=timeout).returncode != 0:
            _require_filebrowser_success(arguments=["users", "add", "anonymous", secret], database=database, timeout=timeout, secret=secret)
    else:
        user_table = _require_filebrowser_success(arguments=["users", "ls"], database=database, timeout=timeout, secret=secret)
        user_rows = user_table.splitlines()[1:]
        if len(user_rows) > 1:
            typer.echo(f"❌ ERROR: Multiple accounts exist in {database}. Keep one account before restarting the share.", err=True)
            raise typer.Exit(code=1)
        _require_filebrowser_success(arguments=["config", "set", "--auth.method", "json", *minimum_length], database=database, timeout=timeout, secret=secret)
        if user_rows:
            user_id = user_rows[0].split(maxsplit=1)[0]
            _require_filebrowser_success(arguments=["users", "update", user_id, "--username", username, "--password", password], database=database, timeout=timeout, secret=secret)
        else:
            _require_filebrowser_success(arguments=["users", "add", username, password], database=database, timeout=timeout, secret=secret)
    return database
