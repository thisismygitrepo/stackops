import json
import re
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from stackops.utils.managed_files import (
    ManagedFileKind,
    ManagedFileSpec,
    ensure_managed_schema,
    get_managed_file_spec,
    managed_schema_path,
)

if TYPE_CHECKING:
    from stackops.utils.schemas.yaml_schema import JsonValue


def _validate_schema_document() -> None:
    import json
    import sys
    from typing import cast

    import yaml
    from jsonschema.exceptions import ValidationError
    from jsonschema.validators import validator_for

    payload = cast(dict[str, object], json.load(sys.stdin))
    schema = cast(dict[str, object], payload["schema"])
    content = cast(str, payload["content"])
    try:
        if payload["yaml"]:
            data: object = yaml.safe_load(content)
            if data is None and payload["kind"] in {"dotfiles", "data"}:
                data = {}
        else:
            data = json.loads(content)
    except (json.JSONDecodeError, yaml.YAMLError) as error:
        print(f"""Invalid {payload['kind']} file {payload['path']}: {error}""", file=sys.stderr)
        raise SystemExit(1) from error
    try:
        validator_for(schema)(schema).validate(cast("JsonValue", data))
    except ValidationError as error:
        detail = f"""failed schema rule '{error.validator}'""" if payload["kind"] == "secrets" else error.message
        print(f"""Invalid {payload['kind']} file {payload['path']} at {error.json_path}: {detail}""", file=sys.stderr)
        raise SystemExit(1) from error


def describe_managed_file(*, spec: ManagedFileSpec, data_path: Path) -> dict[str, str]:
    return {
        "path": str(data_path),
        "schema": str(spec.schema_source_path),
        "local_schema": str(managed_schema_path(spec=spec, data_path=data_path)),
    }


def initialize_managed_file(*, spec: ManagedFileSpec, data_path: Path) -> None:
    if data_path.exists() and not data_path.is_file():
        raise IsADirectoryError(f"""Configuration path is not a file: {data_path}""")
    schema_path = managed_schema_path(spec=spec, data_path=data_path)
    if data_path == schema_path:
        raise ValueError(f"""Configuration and schema must use different paths: {data_path}""")
    ensure_managed_schema(spec=spec, data_path=data_path)
    if data_path.exists():
        return
    content = spec.initial_content
    if spec.user_path.suffix in {".yaml", ".yml"}:
        content = re.sub(r"^# yaml-language-server: \$schema=.*\n?", "", content)
        content = f"""# yaml-language-server: $schema=./{schema_path.name}
{content}"""
    with data_path.open("x", encoding="utf-8") as stream:
        data_path.chmod(spec.file_mode)
        stream.write(content)


def validate_managed_file(*, kind: ManagedFileKind, data_path: Path) -> None:
    from stackops.utils.meta import lambda_to_python_script

    spec = get_managed_file_spec(kind)
    content = data_path.read_text(encoding="utf-8")
    if kind == "mcp":
        from stackops.utils.files.read import remove_c_style_comments

        content = remove_c_style_comments(content)
    schema = cast(dict[str, object], json.loads(spec.schema_source_path.read_text(encoding="utf-8")))
    payload = json.dumps({
        "kind": kind,
        "path": str(data_path),
        "schema": schema,
        "content": content,
        "yaml": spec.user_path.suffix in {".yaml", ".yml"},
    })
    worker_source = lambda_to_python_script(lambda: _validate_schema_document(), in_global=True, import_module=False)
    result = subprocess.run(
        ["uv", "run", "--no-project", "--python", sys.executable, "--with", "jsonschema", "python", "-c", worker_source],
        input=payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"""Schema validation failed with exit code {result.returncode}.""")
    try:
        match kind:
            case "config":
                return
            case "software":
                from stackops.utils.installer_utils.installer_catalog import load_installer_data_file
                from stackops.utils.installer_utils.installer_scripts import get_user_installer_scripts_root, validate_installer_script_references

                validate_installer_script_references(
                    installers=load_installer_data_file(path=data_path)["installers"],
                    user_scripts_root=get_user_installer_scripts_root(user_catalog_path=data_path),
                )
            case "repos":
                from stackops.scripts.python.helpers.helpers_repos.spec_store import load_repos_spec

                load_repos_spec(path=data_path)
            case "layouts":
                from stackops.utils.schemas.layouts.layout_file import read_layouts_file

                read_layouts_file(path=data_path)
            case "dotfiles":
                from stackops.profile.dotfiles_mapper import load_dotfiles_mapper

                load_dotfiles_mapper(path=data_path)
            case "data":
                from stackops.scripts.python.helpers.helpers_cloud.backup_config import load_backup_config_file

                load_backup_config_file(path=data_path, empty_as_config=True)
            case "secrets":
                from stackops.secrets.loader import load_secrets_file

                load_secrets_file(secrets_path=data_path)
            case "prompts" | "parallel" | "mcp":
                from stackops.utils.managed_agent_files import validate_agent_managed_file

                validate_agent_managed_file(kind=kind, data_path=data_path)
    except TypeError as error:
        raise ValueError(f"""Invalid {kind} file {data_path}: {error}""") from error
