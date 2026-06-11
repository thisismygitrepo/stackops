import re
import shlex
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, NoReturn, TypeAlias

import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as secret_actions
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretCandidate,
    load_secret_candidates,
)
from stackops.secrets.loader import SecretsSchemaError, load_secrets_file
from stackops.secrets.types import Login, SecretsFile

SECRETS_RELATIVE_PATH = Path(".stackops") / "secrets" / "secrets.json"
SECRETS_SCHEMA_FILENAME = secret_actions.SECRETS_SCHEMA_FILENAME
SECRETS_FILE_VERSION = secret_actions.SECRETS_FILE_VERSION
ENV_VAR_NAME_RE = secret_actions.ENV_VAR_NAME_RE
LOGIN_ENTRY_PATH_RE = re.compile(r"^(entries\[\d+\])(?:\.|$)")

SecretsSource: TypeAlias = Literal["local", "l", "global", "g", "both", "b"]
WritableSecretsSource: TypeAlias = Literal["local", "l", "global", "g"]
ResolvedSecretsSource: TypeAlias = Literal["local", "global", "both"]


@dataclass(frozen=True)
class SecretsFileSource:
    name: str
    path: Path


@dataclass(frozen=True)
class SecretsFileStats:
    source_name: str
    path: Path
    exists: bool
    version: str = "-"
    logins: int = 0
    secret_bundles: int = 0
    env_vars: int = 0
    unique_env_keys: int = 0
    duplicate_env_key_occurrences: int = 0
    invalid_env_keys: int = 0
    login_tag_counts: Counter[str] | None = None
    secret_tag_counts: Counter[str] | None = None
    scope_counts: Counter[str] | None = None
    login_description_count: int = 0
    login_url_count: int = 0
    login_email_count: int = 0
    login_username_count: int = 0
    login_account_name_count: int = 0
    login_metadata_count: int = 0
    login_metadata_fields: int = 0
    secret_description_count: int = 0
    secret_rotation_count: int = 0
    secret_metadata_count: int = 0
    secret_metadata_fields: int = 0
    secrets_with_tags: int = 0
    secrets_with_scopes: int = 0
    max_keys_per_secret: int = 0

def _resolve_secret_sources(*, secrets_path: Path | None, secrets_source: SecretsSource) -> list[SecretsFileSource]:
    resolved_source = _resolve_secrets_source_alias(secrets_source)
    local_source = SecretsFileSource(name="local", path=_resolve_local_secrets_path(secrets_path))
    if resolved_source == "local":
        return [local_source]

    global_source = SecretsFileSource(name="global", path=_resolve_global_secrets_path())
    if resolved_source == "global":
        if secrets_path is not None:
            _fail("--path overrides only the local secrets source. Use --source local or --source both with --path.")
        return [global_source]
    if resolved_source == "both":
        return [local_source, global_source]

    _fail(f"Unknown secrets source: {secrets_source}")


def _resolve_single_secret_source(*, secrets_path: Path | None, secrets_source: WritableSecretsSource) -> SecretsFileSource:
    secret_sources = _resolve_secret_sources(secrets_path=secrets_path, secrets_source=secrets_source)
    if len(secret_sources) != 1:
        _fail("Choose exactly one secrets source: local/l or global/g.")
    return secret_sources[0]


def _resolve_secrets_source_alias(secrets_source: SecretsSource) -> ResolvedSecretsSource:
    match secrets_source.casefold():
        case "local" | "l":
            return "local"
        case "global" | "g":
            return "global"
        case "both" | "b":
            return "both"
        case _:
            raise NotImplementedError
    _fail(f"Unknown secrets source: {secrets_source}")


def _resolve_local_secrets_path(secrets_path: Path | None) -> Path:
    if secrets_path is None:
        return Path.cwd() / SECRETS_RELATIVE_PATH
    expanded_path = secrets_path.expanduser()
    if expanded_path.is_absolute():
        return expanded_path
    return Path.cwd() / expanded_path


def _resolve_global_secrets_path() -> Path:
    from stackops.secrets.paths import SECRETS_DOFILE

    return SECRETS_DOFILE.expanduser()


def _load_secret_candidates_from_sources(secret_sources: list[SecretsFileSource]) -> list[SecretCandidate]:
    include_source_labels = len(secret_sources) > 1
    candidates: list[SecretCandidate] = []
    missing_sources: list[SecretsFileSource] = []
    for secret_source in secret_sources:
        if not secret_source.path.exists():
            if include_source_labels:
                missing_sources.append(secret_source)
                _warn(f"Secrets file not found for {secret_source.name} source: {secret_source.path}")
                continue
            _fail(f"Secrets file not found: {secret_source.path}")
        candidates.extend(load_secret_candidates(secret_source.path, source_name=secret_source.name if include_source_labels else None))
    if not candidates and missing_sources:
        checked_sources = ", ".join(f"{secret_source.name}={secret_source.path}" for secret_source in missing_sources)
        _fail(f"No secrets files found. Checked: {checked_sources}")
    return candidates


def _candidate_source_path(*, candidate: SecretCandidate, secret_sources: list[SecretsFileSource]) -> Path:
    if candidate.source_path is not None:
        return candidate.source_path
    return secret_sources[0].path


def _load_secret_stats_from_sources(*, secret_sources: list[SecretsFileSource], show_paths: bool) -> list[SecretsFileStats]:
    include_source_labels = len(secret_sources) > 1
    stats_rows: list[SecretsFileStats] = []
    missing_sources: list[SecretsFileSource] = []
    for secret_source in secret_sources:
        if not secret_source.path.exists():
            if include_source_labels:
                missing_sources.append(secret_source)
                stats_rows.append(SecretsFileStats(source_name=secret_source.name, path=secret_source.path, exists=False))
                _warn(_missing_source_message(secret_source=secret_source, show_paths=show_paths))
                continue
            _fail(_missing_source_message(secret_source=secret_source, show_paths=show_paths))
        stats_rows.append(_load_secret_stats(secret_source=secret_source, show_paths=show_paths))

    if missing_sources and not any(row.exists for row in stats_rows):
        checked_sources = _format_checked_sources(secret_sources=missing_sources, show_paths=show_paths)
        _fail(f"No secrets files found. Checked: {checked_sources}")
    return stats_rows


def _load_secret_stats(*, secret_source: SecretsFileSource, show_paths: bool) -> SecretsFileStats:
    try:
        secrets_file = load_secrets_file(secret_source.path)
    except SecretsSchemaError as exc:
        error_text = str(exc) if show_paths else str(exc).replace(str(secret_source.path), secret_source.name)
        _fail(error_text)
    return _build_secret_stats(secrets_file=secrets_file, secret_source=secret_source)


def _build_secret_stats(*, secrets_file: SecretsFile, secret_source: SecretsFileSource) -> SecretsFileStats:
    entries: list[Login] = list(secrets_file["entries"])
    login_tag_counts: Counter[str] = Counter()
    secret_tag_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    env_key_counts: Counter[str] = Counter()

    secret_bundles = 0
    env_vars = 0
    invalid_env_keys = 0
    login_description_count = 0
    login_url_count = 0
    login_email_count = 0
    login_username_count = 0
    login_account_name_count = 0
    login_metadata_count = 0
    login_metadata_fields = 0
    secret_description_count = 0
    secret_rotation_count = 0
    secret_metadata_count = 0
    secret_metadata_fields = 0
    secrets_with_tags = 0
    secrets_with_scopes = 0
    max_keys_per_secret = 0

    for login in entries:
        login_tag_counts.update(login.get("tags", ()))
        login_description_count += int("description" in login)
        login_url_count += int("url" in login)
        login_email_count += int("email" in login)
        login_username_count += int("username" in login)
        login_account_name_count += int("accountName" in login)
        login_metadata = login.get("metadata")
        if login_metadata:
            login_metadata_count += 1
            login_metadata_fields += len(login_metadata)

        for secret in login["secrets"]:
            secret_bundles += 1
            secret_tag_counts.update(secret["tags"])
            scope_counts.update(secret["scopes"])
            secrets_with_tags += int(bool(secret["tags"]))
            secrets_with_scopes += int(bool(secret["scopes"]))
            secret_description_count += int("description" in secret)
            secret_rotation_count += int("rotation" in secret)
            secret_metadata = secret.get("metadata")
            if secret_metadata:
                secret_metadata_count += 1
                secret_metadata_fields += len(secret_metadata)

            key_values = secret["keyValues"]
            env_vars += len(key_values)
            max_keys_per_secret = max(max_keys_per_secret, len(key_values))
            env_key_counts.update(key_values.keys())
            invalid_env_keys += sum(1 for key in key_values if ENV_VAR_NAME_RE.fullmatch(key) is None)

    duplicate_env_key_occurrences = sum(count - 1 for count in env_key_counts.values() if count > 1)
    return SecretsFileStats(
        source_name=secret_source.name,
        path=secret_source.path,
        exists=True,
        version=str(secrets_file["version"]),
        logins=len(entries),
        secret_bundles=secret_bundles,
        env_vars=env_vars,
        unique_env_keys=len(env_key_counts),
        duplicate_env_key_occurrences=duplicate_env_key_occurrences,
        invalid_env_keys=invalid_env_keys,
        login_tag_counts=login_tag_counts,
        secret_tag_counts=secret_tag_counts,
        scope_counts=scope_counts,
        login_description_count=login_description_count,
        login_url_count=login_url_count,
        login_email_count=login_email_count,
        login_username_count=login_username_count,
        login_account_name_count=login_account_name_count,
        login_metadata_count=login_metadata_count,
        login_metadata_fields=login_metadata_fields,
        secret_description_count=secret_description_count,
        secret_rotation_count=secret_rotation_count,
        secret_metadata_count=secret_metadata_count,
        secret_metadata_fields=secret_metadata_fields,
        secrets_with_tags=secrets_with_tags,
        secrets_with_scopes=secrets_with_scopes,
        max_keys_per_secret=max_keys_per_secret,
    )


def _render_secret_stats(*, stats_rows: list[SecretsFileStats], details: bool, show_paths: bool, top: int) -> None:
    from rich.console import Console

    console = Console()
    loaded_stats = [stats_row for stats_row in stats_rows if stats_row.exists]
    console.print(_secret_stats_source_table(stats_rows=stats_rows, show_paths=show_paths))
    if not loaded_stats:
        return
    console.print(_secret_stats_totals_table(stats_rows=loaded_stats))
    console.print(_secret_stats_coverage_table(stats_rows=loaded_stats))
    if details:
        details_table = _secret_stats_details_table(stats_rows=loaded_stats, top=top)
        if details_table.row_count:
            console.print(details_table)


def _secret_stats_source_table(*, stats_rows: list[SecretsFileStats], show_paths: bool):
    from rich import box
    from rich.markup import escape
    from rich.table import Table

    table = Table(title="StackOps Secrets Sources", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Source", style="bold")
    table.add_column("Status")
    table.add_column("Version", justify="right")
    table.add_column("Logins", justify="right")
    table.add_column("Bundles", justify="right")
    table.add_column("Env Vars", justify="right")
    table.add_column("Unique Keys", justify="right")
    table.add_column("Invalid Keys", justify="right")
    if show_paths:
        table.add_column("File")

    for stats_row in stats_rows:
        status = "[green]loaded[/green]" if stats_row.exists else "[yellow]missing[/yellow]"
        row = [
            escape(stats_row.source_name),
            status,
            escape(stats_row.version),
            str(stats_row.logins) if stats_row.exists else "-",
            str(stats_row.secret_bundles) if stats_row.exists else "-",
            str(stats_row.env_vars) if stats_row.exists else "-",
            str(stats_row.unique_env_keys) if stats_row.exists else "-",
            str(stats_row.invalid_env_keys) if stats_row.exists else "-",
        ]
        if show_paths:
            row.append(escape(str(stats_row.path)))
        table.add_row(*row)
    return table


def _secret_stats_totals_table(*, stats_rows: list[SecretsFileStats]):
    from rich import box
    from rich.table import Table

    table = Table(title="Inventory Totals", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Metric")
    table.add_column("Count", justify="right")
    table.add_row("Sources loaded", str(len(stats_rows)))
    table.add_row("Logins", str(sum(row.logins for row in stats_rows)))
    table.add_row("Secret bundles", str(sum(row.secret_bundles for row in stats_rows)))
    table.add_row("Env vars", str(sum(row.env_vars for row in stats_rows)))
    table.add_row("Unique env var names", str(_unique_env_key_total(stats_rows)))
    table.add_row("Duplicate env var occurrences", str(sum(row.duplicate_env_key_occurrences for row in stats_rows)))
    table.add_row("Invalid env var names", str(sum(row.invalid_env_keys for row in stats_rows)))
    table.add_row("Login tags", str(sum(_counter_total(row.login_tag_counts) for row in stats_rows)))
    table.add_row("Secret tags", str(sum(_counter_total(row.secret_tag_counts) for row in stats_rows)))
    table.add_row("Scopes", str(sum(_counter_total(row.scope_counts) for row in stats_rows)))
    table.add_row("Rotation records", str(sum(row.secret_rotation_count for row in stats_rows)))
    table.add_row("Metadata fields", str(sum(row.login_metadata_fields + row.secret_metadata_fields for row in stats_rows)))
    table.add_row("Max env vars in one bundle", str(max((row.max_keys_per_secret for row in stats_rows), default=0)))
    return table


def _secret_stats_coverage_table(*, stats_rows: list[SecretsFileStats]):
    from rich import box
    from rich.table import Table

    total_logins = sum(row.logins for row in stats_rows)
    total_secrets = sum(row.secret_bundles for row in stats_rows)
    table = Table(title="Metadata Coverage", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("With Field", justify="right")
    table.add_column("Coverage", justify="right")
    table.add_row("Login descriptions", str(sum(row.login_description_count for row in stats_rows)), _percent(sum(row.login_description_count for row in stats_rows), total_logins))
    table.add_row("Login URLs", str(sum(row.login_url_count for row in stats_rows)), _percent(sum(row.login_url_count for row in stats_rows), total_logins))
    table.add_row("Login emails", str(sum(row.login_email_count for row in stats_rows)), _percent(sum(row.login_email_count for row in stats_rows), total_logins))
    table.add_row("Login usernames", str(sum(row.login_username_count for row in stats_rows)), _percent(sum(row.login_username_count for row in stats_rows), total_logins))
    table.add_row("Login account names", str(sum(row.login_account_name_count for row in stats_rows)), _percent(sum(row.login_account_name_count for row in stats_rows), total_logins))
    table.add_row("Login metadata", str(sum(row.login_metadata_count for row in stats_rows)), _percent(sum(row.login_metadata_count for row in stats_rows), total_logins))
    table.add_row("Secret descriptions", str(sum(row.secret_description_count for row in stats_rows)), _percent(sum(row.secret_description_count for row in stats_rows), total_secrets))
    table.add_row("Secret rotations", str(sum(row.secret_rotation_count for row in stats_rows)), _percent(sum(row.secret_rotation_count for row in stats_rows), total_secrets))
    table.add_row("Secret metadata", str(sum(row.secret_metadata_count for row in stats_rows)), _percent(sum(row.secret_metadata_count for row in stats_rows), total_secrets))
    table.add_row("Secret tags", str(sum(row.secrets_with_tags for row in stats_rows)), _percent(sum(row.secrets_with_tags for row in stats_rows), total_secrets))
    table.add_row("Secret scopes", str(sum(row.secrets_with_scopes for row in stats_rows)), _percent(sum(row.secrets_with_scopes for row in stats_rows), total_secrets))
    return table


def _secret_stats_details_table(*, stats_rows: list[SecretsFileStats], top: int):
    from rich import box
    from rich.markup import escape
    from rich.table import Table

    rows: list[tuple[str, str, int]] = []
    for label, counter in (
        ("Login tag", _merge_counters(stats_rows, "login_tag_counts")),
        ("Secret tag", _merge_counters(stats_rows, "secret_tag_counts")),
        ("Scope", _merge_counters(stats_rows, "scope_counts")),
    ):
        rows.extend((label, value, count) for value, count in _top_counter_items(counter, top=top))

    table = Table(title="Top Labels", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    table.add_column("Type")
    table.add_column("Value")
    table.add_column("Count", justify="right")
    for row_type, value, count in rows:
        table.add_row(row_type, escape(value), str(count))
    return table


def _percent(count: int, total: int) -> str:
    if total == 0:
        return "-"
    return f"{count / total:.0%}"


def _counter_total(counter: Counter[str] | None) -> int:
    return sum((counter or Counter()).values())


def _merge_counters(stats_rows: list[SecretsFileStats], attribute_name: str) -> Counter[str]:
    merged = Counter[str]()
    for stats_row in stats_rows:
        merged.update(getattr(stats_row, attribute_name) or Counter())
    return merged


def _top_counter_items(counter: Counter[str], *, top: int) -> list[tuple[str, int]]:
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:top]


def _unique_env_key_total(stats_rows: list[SecretsFileStats]) -> int:
    if len(stats_rows) == 1:
        return stats_rows[0].unique_env_keys
    return sum(row.unique_env_keys for row in stats_rows)


def _missing_source_message(*, secret_source: SecretsFileSource, show_paths: bool) -> str:
    if show_paths:
        return f"Secrets file not found for {secret_source.name} source: {secret_source.path}"
    return f"Secrets file not found for {secret_source.name} source."


def _format_checked_sources(*, secret_sources: list[SecretsFileSource], show_paths: bool) -> str:
    if show_paths:
        return ", ".join(f"{secret_source.name}={secret_source.path}" for secret_source in secret_sources)
    return ", ".join(secret_source.name for secret_source in secret_sources)


def _echo_jq_login_entry_hint(*, candidate: SecretCandidate, secrets_path: Path) -> None:
    typer.echo("Selected login entry jq:")
    typer.echo(f"  {_jq_login_entry_command(candidate=candidate, secrets_path=secrets_path)}")


def _jq_login_entry_command(*, candidate: SecretCandidate, secrets_path: Path) -> str:
    return f"jq {shlex.quote(_jq_login_entry_filter(candidate))} {shlex.quote(str(secrets_path))}"


def _jq_login_entry_filter(candidate: SecretCandidate) -> str:
    match = LOGIN_ENTRY_PATH_RE.match(candidate.json_path)
    if match is None:
        return ".entries[]"
    return f".{match.group(1)}"


def _clean_optional_selector(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _clean_selector_values(values: list[str] | None) -> tuple[str, ...]:
    return tuple(stripped_value for value in values or () if (stripped_value := value.strip()))


def _echo_verbose_selection(*, candidate: SecretCandidate, secrets_path: Path) -> None:
    typer.echo("Selected secret bundle:")
    typer.echo(f"  Bundle: {_candidate_verbose_label(candidate)}")
    typer.echo(f"  Source: {secrets_path}")
    typer.echo(f"  JSON path: {candidate.json_path}")
    typer.echo(f"  Login tags: {_join_display(candidate.login_tags)}")
    typer.echo(f"  Secret tags: {_join_display(candidate.secret_tags)}")
    typer.echo(f"  Scopes: {_join_display(candidate.scopes)}")
    typer.echo("Defining env vars:")
    for key in candidate.key_values:
        typer.echo(f"  {key}")


def _candidate_verbose_label(candidate: SecretCandidate) -> str:
    return f"{candidate.login_name} / {candidate.secret_name}"


def _join_display(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)


def _warn(message: str) -> None:
    typer.echo(typer.style("Warning: ", fg=typer.colors.YELLOW) + message, err=True)


resolve_secret_sources = _resolve_secret_sources
resolve_single_secret_source = _resolve_single_secret_source
load_secret_candidates_from_sources = _load_secret_candidates_from_sources
candidate_source_path = _candidate_source_path
load_secret_stats_from_sources = _load_secret_stats_from_sources
render_secret_stats = _render_secret_stats
echo_jq_login_entry_hint = _echo_jq_login_entry_hint
clean_optional_selector = _clean_optional_selector
clean_selector_values = _clean_selector_values
echo_verbose_selection = _echo_verbose_selection
fail = _fail
