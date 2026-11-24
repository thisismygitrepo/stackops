import hashlib
import os
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import TypedDict

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_support import SecretsFileSource, SecretsFileStats, load_secret_stats_from_sources
from stackops.scripts.python.helpers.helpers_webui.vault_file_constants import VAULT_DUE_SOON_DAYS, VaultRotationState, VaultSchemaState
from stackops.scripts.python.helpers.helpers_webui.vault_file_problem import VaultFileFinding, explain_vault_problem
from stackops.scripts.python.helpers.helpers_webui.vault_form import VaultProblem
from stackops.scripts.python.helpers.helpers_webui.vault_views import vault_sources
from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
from stackops.secrets.models import Login
from stackops.utils.managed_files import ManagedFileSpec, get_managed_file_spec, managed_schema_path


class VaultLabelCount(TypedDict):
    label: str
    count: int


# One secret that keeps a rotation record. `index` is its login's place in the file, `age` the days since it was last replaced and -1 when the
# record has no date that can be read, `every` the days between replacements and 0 when none is set.
class VaultRotationView(TypedDict):
    index: int
    login: str
    account: str
    secret: str
    last: str
    every: int
    age: int
    owner: str
    state: VaultRotationState


# What one vault file holds, as `devops vault stats` counts it: labels and numbers, never a value. `described` says how many logins and secrets
# carry each optional note. `untouched` says the logins are still the examples a new file starts with.
class VaultFileHolds(TypedDict):
    untouched: bool
    logins: int
    secrets: int
    values: int
    value_names: int
    repeated_names: int
    unloadable_names: int
    login_tags: list[VaultLabelCount]
    secret_tags: list[VaultLabelCount]
    scopes: list[VaultLabelCount]
    described: dict[str, int]
    rotation: list[VaultRotationView]


# `version` is the hash of the file as read and empty for a missing one. `private` says nobody but its owner can read it. `finding` is what the
# quick check found wrong, and `holds` is there only for a file that passed it.
class VaultFileHealth(TypedDict):
    name: str
    path: str
    exists: bool
    version: str
    bytes: int
    modified: float
    private: bool
    schema: VaultSchemaState
    finding: VaultFileFinding | None
    holds: VaultFileHolds | None


# `starter_logins` are the example logins a newly created file starts with.
class VaultHealthView(TypedDict):
    files: list[VaultFileHealth]
    starter_logins: list[str]


# Every vault file the page works with, the way the Vault page lists them: the project's, one per member of a workspace, then the user's.
def read_vault_health(base_directory: str) -> VaultHealthView | VaultProblem:
    try:
        sources = vault_sources(base_directory)
    except ValueError as error:
        return VaultProblem(status=400, message=str(error))
    spec = get_managed_file_spec("secrets")
    today = date.today()
    starter_logins = [login["name"] for login in load_secrets_file(spec.example_source_path)["entries"]]
    return {"files": [_file_health(name=name, path=path, spec=spec, today=today, starter_logins=starter_logins) for name, path in sources], "starter_logins": starter_logins}


def _file_health(name: str, path: Path, spec: ManagedFileSpec, today: date, starter_logins: list[str]) -> VaultFileHealth:
    schema_path = managed_schema_path(spec=spec, data_path=path)
    schema: VaultSchemaState = (
        "missing" if not schema_path.is_file() else "current" if schema_path.read_text(encoding="utf-8") == spec.schema_source_path.read_text(encoding="utf-8") else "stale"
    )
    if not path.is_file():
        return {"name": name, "path": str(path), "exists": False, "version": "", "bytes": 0, "modified": 0.0, "private": True, "schema": schema, "finding": None, "holds": None}
    content = path.read_bytes()
    status = path.stat()
    finding: VaultFileFinding | None = None
    holds: VaultFileHolds | None = None
    try:
        entries = load_secrets_file(path)["entries"]
        # The command's own counting. It reads the file once more, and stops the way a command does if the file went missing in between.
        row = load_secret_stats_from_sources(secret_sources=[SecretsFileSource(name=name, path=path)], show_paths=False)[0]
        holds = _holds(row=row, entries=entries, today=today, starter_logins=starter_logins)
    except SecretsSchemaError as error:
        finding = explain_vault_problem(message=str(error), path=path)
    except typer.Exit:
        finding = {"what": "The file changed while it was being read. Check again.", "where": "", "line": 0, "column": 0, "said": ""}
    return {
        "name": name,
        "path": str(path),
        "exists": True,
        "version": hashlib.sha256(content).hexdigest(),
        "bytes": len(content),
        "modified": status.st_mtime,
        # Windows keeps who may read a file somewhere these bits do not show.
        "private": os.name == "nt" or status.st_mode & 0o077 == 0,
        "schema": schema,
        "finding": finding,
        "holds": holds,
    }


def _holds(row: SecretsFileStats, entries: list[Login], today: date, starter_logins: list[str]) -> VaultFileHolds:
    return {
        "untouched": [login["name"] for login in entries] == starter_logins,
        "logins": row.logins,
        "secrets": row.secret_bundles,
        "values": row.env_vars,
        "value_names": row.unique_env_keys,
        "repeated_names": row.duplicate_env_key_occurrences,
        "unloadable_names": row.invalid_env_keys,
        "login_tags": _label_counts(row.login_tag_counts),
        "secret_tags": _label_counts(row.secret_tag_counts),
        "scopes": _label_counts(row.scope_counts),
        "described": {
            "login_description": row.login_description_count,
            "login_url": row.login_url_count,
            "login_username": row.login_username_count,
            "login_email": row.login_email_count,
            "login_account": row.login_account_name_count,
            "secret_description": row.secret_description_count,
            "secret_rotation": row.secret_rotation_count,
            "secret_tags": row.secrets_with_tags,
            "secret_scopes": row.secrets_with_scopes,
        },
        "rotation": [view for index, login in enumerate(entries) for view in _rotations(index=index, login=login, today=today)],
    }


def _label_counts(counts: Counter[str] | None) -> list[VaultLabelCount]:
    return [{"label": label, "count": count} for label, count in sorted((counts or Counter()).items(), key=lambda item: (-item[1], item[0]))]


def _rotations(index: int, login: Login, today: date) -> list[VaultRotationView]:
    views: list[VaultRotationView] = []
    for secret in login["secrets"]:
        if "rotation" not in secret:
            continue
        rotation = secret["rotation"]
        last = rotation.get("lastRotated", "")
        every = rotation.get("rotateEveryDays", 0)
        try:
            age = (today - datetime.fromisoformat(last).date()).days if last else -1
        except ValueError:
            age = -1
        state: VaultRotationState = (
            "undated" if age < 0 else "unscheduled" if every == 0 else "due" if age > every else "soon" if every - age <= VAULT_DUE_SOON_DAYS else "fine"
        )
        views.append({
            "index": index, "login": login["name"], "account": login.get("accountName", ""), "secret": secret["name"],
            "last": last, "every": every, "age": age, "owner": rotation.get("owner", ""), "state": state,
        })
    return views
