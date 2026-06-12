from collections.abc import Callable
from pathlib import Path
from typing import Literal, Mapping, NoReturn, TypeAlias

import typer

from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_interactive import (
    InteractivePickerOption,
    choose_interactive_options,
)
from stackops.secrets.models import Login, SecretsFile

SECRETS_SCHEMA_FILENAME = "secrets.schema.json"
SECRETS_FILE_VERSION = "0.5"
SubsetOutputConflictAction: TypeAlias = Literal["throw-error", "overwrite", "append"]
SubsetOutputConflictOption: TypeAlias = Literal["throw-error", "t", "overwrite", "o", "append", "a"]
_SUBSET_OUTPUT_CONFLICT_ACTIONS: dict[SubsetOutputConflictOption, SubsetOutputConflictAction] = {
    "throw-error": "throw-error",
    "t": "throw-error",
    "overwrite": "overwrite",
    "o": "overwrite",
    "append": "append",
    "a": "append",
}


def resolve_subset_output_conflict_action(on_conflict: SubsetOutputConflictOption) -> SubsetOutputConflictAction:
    return _SUBSET_OUTPUT_CONFLICT_ACTIONS[on_conflict]


def is_valid_env_name(name: str) -> bool:
    import re
    return re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) is not None


def edit_secrets_file(secrets_path: Path, editor: str, *, create: bool = False) -> None:
    import shutil
    import subprocess

    if not secrets_path.exists():
        if not create:
            _fail(f"Secrets file not found: {secrets_path}. Pass --create with --edit to create it from the packaged example.")
        secrets_path.parent.mkdir(parents=True, exist_ok=True)
        secrets_path.write_text(_read_default_secrets_template(), encoding="utf-8")
        _write_default_secrets_schema(secrets_path.parent / SECRETS_SCHEMA_FILENAME)
    elif create:
        _write_default_secrets_schema(secrets_path.parent / SECRETS_SCHEMA_FILENAME)
    editor_bin = shutil.which(editor)
    if editor_bin is None:
        _fail(f"Editor '{editor}' is not available on PATH.")
    result = subprocess.run([editor_bin, str(secrets_path)], check=False)
    if result.returncode != 0:
        _fail(f"Editor exited with status code {result.returncode}.")


def add_secrets_entry(
    secrets_path: Path,
    *,
    create: bool = False,
    prompt_secret_login_entry: Callable[[], Login] | None = None,
) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_prompts import prompt_secret_login

    secrets_file, created_file = _load_or_initialize_add_target(secrets_path=secrets_path, create=create)
    prompt_entry = prompt_secret_login_entry or prompt_secret_login
    entry = prompt_entry()
    _secrets_entries(secrets_file).append(entry)
    _write_secrets_file(secrets_path=secrets_path, secrets_file=secrets_file, created_file=created_file)
    if create:
        _write_default_secrets_schema(secrets_path.parent / SECRETS_SCHEMA_FILENAME)
    typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Added secrets entry '{entry['name']}' to {secrets_path}")


def subset_secrets_file(source_path: Path, output_path: Path, *, on_conflict: SubsetOutputConflictAction, preview_secrets: bool) -> None:
    import json
    from copy import deepcopy

    from stackops.secrets.loader import SecretsSchemaError, load_secrets_file

    try:
        secrets_file = load_secrets_file(source_path)
    except SecretsSchemaError as exc:
        _fail(str(exc))
    if source_path.resolve(strict=False) == output_path.resolve(strict=False):
        _fail("Subset output path must be different from the source secrets file.")
    existing_output_file = _load_existing_subset_output(output_path=output_path, on_conflict=on_conflict)
    if existing_output_file is not None and existing_output_file["version"] != secrets_file["version"]:
        _fail(
            f"Cannot append to {output_path}: output version {existing_output_file['version']} "
            + f"does not match source version {secrets_file['version']}."
        )
    selected_indices = _choose_subset_login_indices(secrets_file=secrets_file, source_path=source_path, preview_secrets=preview_secrets)
    if not selected_indices:
        _fail("No secrets entries selected.")
    selected_index_set = set(selected_indices)
    selected_entries = [deepcopy(entry) for index, entry in enumerate(secrets_file["entries"]) if index in selected_index_set]
    if not selected_entries:
        _fail("No secrets entries selected.")
    subset_file = _build_subset_file(source_file=secrets_file, selected_entries=selected_entries, existing_output_file=existing_output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(subset_file, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _chmod_private(output_path, 0o600)
    secret_count = sum(len(entry["secrets"]) for entry in selected_entries)
    action = "Appended" if on_conflict == "append" else "Wrote"
    suffix = f"; output now has {len(subset_file['entries'])} login entry(ies)" if on_conflict == "append" else ""
    typer.echo(
        typer.style("✅ Success: ", fg=typer.colors.GREEN)
        + f"{action} {len(selected_entries)} selected login entry(ies) and {secret_count} secret bundle(s) to {output_path}{suffix}"
    )


def validate_env_names(key_values: Mapping[str, object]) -> None:
    invalid_names = [name for name in key_values if not is_valid_env_name(name)]
    if invalid_names:
        _fail(f"Invalid environment variable name(s) in keyValues: {', '.join(invalid_names)}")


def write_env_handoff(key_values: Mapping[str, object]) -> None:
    import os
    import platform

    op_program_path_raw = os.environ.get("OP_PROGRAM_PATH")
    if not op_program_path_raw:
        _fail("Cannot define env variables in the parent shell because OP_PROGRAM_PATH is not set. Run through the StackOps shell wrapper.")
    op_program_path = Path(op_program_path_raw)
    if op_program_path.exists():
        _fail(f"Cannot write shell handoff script because OP_PROGRAM_PATH already exists: {op_program_path}")
    op_program_path.parent.mkdir(parents=True, exist_ok=True)
    powershell = platform.system() == "Windows"
    env_suffix = ".secrets.env.ps1" if powershell else ".secrets.env.sh"
    env_path = op_program_path.with_name(f"{op_program_path.stem}{env_suffix}")
    if env_path.exists():
        _fail(f"Cannot write secrets env file because it already exists: {env_path}")
    env_path.write_text(_render_env_file(key_values=key_values, powershell=powershell), encoding="utf-8")
    _chmod_private(env_path, 0o600)
    op_program_path.write_text(_render_loader_file(env_path=env_path, powershell=powershell), encoding="utf-8")
    _chmod_private(op_program_path, 0o700)


def _load_existing_subset_output(*, output_path: Path, on_conflict: SubsetOutputConflictAction) -> SecretsFile | None:
    from stackops.secrets.loader import SecretsSchemaError, load_secrets_file

    if on_conflict == "throw-error":
        if output_path.exists():
            _fail(
                f"Subset output file already exists: {output_path}. "
                + "Pass --on-conflict append to add entries or --on-conflict overwrite to replace it."
            )
        return None
    if on_conflict == "overwrite":
        return None
    if not output_path.exists():
        _fail(
            f"Subset output file does not exist: {output_path}. "
            + "Use --on-conflict throw-error to create a new output file."
        )
    try:
        return load_secrets_file(output_path)
    except SecretsSchemaError as exc:
        _fail(f"Cannot append to invalid subset output file: {exc}")


def _build_subset_file(*, source_file: SecretsFile, selected_entries: list[Login], existing_output_file: SecretsFile | None) -> SecretsFile:
    from copy import deepcopy

    if existing_output_file is None:
        subset_file: SecretsFile = {"version": source_file["version"], "entries": selected_entries}
        if "$schema" in source_file:
            subset_file["$schema"] = source_file["$schema"]
        return subset_file
    merged_entries = [deepcopy(entry) for entry in existing_output_file["entries"]]
    merged_entries.extend(selected_entries)
    subset_file = {"version": existing_output_file["version"], "entries": merged_entries}
    if "$schema" in existing_output_file:
        subset_file["$schema"] = existing_output_file["$schema"]
    return subset_file


def _load_or_initialize_add_target(*, secrets_path: Path, create: bool) -> tuple[dict[str, object], bool]:
    from stackops.secrets.loader import SecretsSchemaError, load_secrets_file

    if not secrets_path.exists():
        if not create:
            _fail(f"Secrets file not found: {secrets_path}. Pass --create with --add to create it.")
        return {"$schema": f"./{SECRETS_SCHEMA_FILENAME}", "version": SECRETS_FILE_VERSION, "entries": []}, True
    try:
        load_secrets_file(secrets_path)
    except SecretsSchemaError as exc:
        _fail(str(exc))
    return _read_secrets_json_payload(secrets_path), False


def _read_secrets_json_payload(secrets_path: Path) -> dict[str, object]:
    import json

    try:
        payload = json.loads(secrets_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON in {secrets_path}: {exc.msg} at line {exc.lineno}, column {exc.colno}.")
    if not isinstance(payload, dict):
        _fail(f"Secrets file must contain a JSON object: {secrets_path}")
    _secrets_entries(payload)
    return payload


def _secrets_entries(secrets_file: Mapping[str, object]) -> list[object]:
    entries = secrets_file.get("entries")
    if not isinstance(entries, list):
        _fail("Secrets file must define an entries array.")
    return entries


def _write_secrets_file(*, secrets_path: Path, secrets_file: Mapping[str, object], created_file: bool) -> None:
    import json

    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text(json.dumps(secrets_file, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if created_file:
        _chmod_private(secrets_path, 0o600)


def _choose_subset_login_indices(*, secrets_file: SecretsFile, source_path: Path, preview_secrets: bool) -> list[int]:
    picker_options = _subset_login_picker_options(secrets_file=secrets_file, source_path=source_path, preview_secrets=preview_secrets)
    return choose_interactive_options(
        picker_options,
        missing_tool_message="Interactive subset selection requires `tv` on PATH.",
        missing_selection_message="Interactive selection did not map to a secrets entry",
    )


def _subset_login_picker_options(*, secrets_file: SecretsFile, source_path: Path, preview_secrets: bool) -> list[InteractivePickerOption[int]]:
    return [
        InteractivePickerOption(
            value=entry_index,
            label=_subset_login_label(entry=entry),
            preview=_subset_login_preview(entry=entry, entry_index=entry_index, source_path=source_path, preview_secrets=preview_secrets),
            disambiguator=f"entries[{entry_index}]",
        )
        for entry_index, entry in enumerate(secrets_file["entries"])
    ]


def _subset_login_label(*, entry: Login) -> str:
    return f"{entry['name']} -> {_preview_summary(_subset_login_env_var_names(entry=entry), limit=4)}"


def _subset_login_preview(*, entry: Login, entry_index: int, source_path: Path, preview_secrets: bool) -> str:
    import json

    env_var_names = _subset_login_env_var_names(entry=entry)
    lines: list[str] = [
        f"# {_subset_login_label(entry=entry)}",
        "",
        f"- Path: `entries[{entry_index}]`",
        f"- File: `{source_path}`",
        f"- Login: `{entry['name']}`",
        f"- Login tags: `{_preview_join(tuple(entry.get('tags', ())))}`",
        f"- Secret bundles: `{len(entry['secrets'])}`",
        f"- Env vars: `{_preview_join(env_var_names)}`",
        "",
        "## Secret Bundles",
    ]
    for secret_index, secret in enumerate(entry["secrets"]):
        lines.extend((
            f"### {secret['name']}",
            f"- Path: `entries[{entry_index}].secrets[{secret_index}]`",
            f"- Secret tags: `{_preview_join(tuple(secret['tags']))}`",
            f"- Scopes: `{_preview_join(tuple(secret['scopes']))}`",
            f"- Env vars: `{_preview_join(tuple(secret['keyValues']))}`",
            "",
        ))
    if preview_secrets:
        lines.extend(("", "## Login entry", "```json", json.dumps(entry, indent=2, ensure_ascii=False), "```"))
    if lines[-1] == "":
        lines.pop()
    return "\n".join(lines) + "\n"


def _preview_join(values: tuple[str, ...]) -> str:
    return ", ".join(values) if values else "-"


def _preview_summary(values: tuple[str, ...], *, limit: int) -> str:
    if not values:
        return "<no env vars>"
    if len(values) <= limit:
        return ", ".join(values)
    return f"""{", ".join(values[:limit])}, +{len(values) - limit} more"""


def _subset_login_env_var_names(*, entry: Login) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for secret in entry["secrets"]:
        for env_var_name in secret["keyValues"]:
            if env_var_name not in seen:
                seen.add(env_var_name)
                result.append(env_var_name)
    return tuple(result)


def _read_default_secrets_template() -> str:
    import stackops.secrets.assets as secrets_assets
    from stackops.utils.path_reference import get_path_reference_path

    template_path = get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE)
    return template_path.read_text(encoding="utf-8")


def _write_default_secrets_schema(schema_path: Path) -> None:
    if schema_path.exists():
        return
    import stackops.secrets.assets as secrets_assets
    from stackops.utils.path_reference import get_path_reference_path

    source_path = get_path_reference_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE)
    schema_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")


def _render_env_file(key_values: Mapping[str, object], powershell: bool) -> str:
    import shlex

    from stackops.secrets.search import render_secret_value

    if powershell:
        lines = ["# StackOps secrets env file. This file is removed after loading."]
        for key, value in key_values.items():
            lines.append(f"$env:{key} = {_quote_powershell(render_secret_value(value))}")
        return "\n".join(lines) + "\n"
    lines = ["# StackOps secrets env file. This file is removed after loading.", "set +x"]
    for key, value in key_values.items():
        lines.append(f"export {key}={shlex.quote(render_secret_value(value))}")
    return "\n".join(lines) + "\n"


def _render_loader_file(env_path: Path, powershell: bool) -> str:
    import shlex

    if powershell:
        env_path_quoted = _quote_powershell(str(env_path))
        return (
            "# StackOps secrets loader. Secret values live in a private temp file, not here.\n"
            f"$StackOpsSecretEnvFile = {env_path_quoted}\n"
            "if (-not (Test-Path -LiteralPath $StackOpsSecretEnvFile)) {\n"
            '    Write-Error "StackOps secrets env file is missing: $StackOpsSecretEnvFile"\n'
            "    exit 1\n"
            "}\n"
            ". $StackOpsSecretEnvFile\n"
            "Remove-Item -LiteralPath $StackOpsSecretEnvFile -Force -ErrorAction SilentlyContinue\n"
            "Remove-Variable -Name StackOpsSecretEnvFile -ErrorAction SilentlyContinue\n"
        )
    env_path_quoted = shlex.quote(str(env_path))
    return (
        "# StackOps secrets loader. Secret values live in a private temp file, not here.\n"
        f"_stackops_secret_env_file={env_path_quoted}\n"
        'if [ ! -f "$_stackops_secret_env_file" ]; then\n'
        '  echo "StackOps secrets env file is missing: $_stackops_secret_env_file" >&2\n'
        "  return 1 2>/dev/null || exit 1\n"
        "fi\n"
        "case $- in\n"
        "  *x*) _stackops_restore_xtrace=1; set +x ;;\n"
        "  *) _stackops_restore_xtrace=0 ;;\n"
        "esac\n"
        '. "$_stackops_secret_env_file"\n'
        'rm -f "$_stackops_secret_env_file"\n'
        'if [ "$_stackops_restore_xtrace" = "1" ]; then\n'
        "  set -x\n"
        "fi\n"
        "unset _stackops_secret_env_file _stackops_restore_xtrace\n"
    )


def _quote_powershell(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _chmod_private(path: Path, mode: int) -> None:
    import platform

    if platform.system() == "Windows":
        return
    path.chmod(mode)


def _fail(message: str) -> NoReturn:
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + message)
    raise typer.Exit(code=1)
