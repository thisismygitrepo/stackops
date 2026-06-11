import json
from pathlib import Path

import pytest
import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets_actions as actions
from stackops.utils.schemas.secrets.secrets_loader import load_secrets_file
from stackops.utils.schemas.secrets.secrets_types import Login, SecretRecord, SecretsFile


def test_subset_secrets_file_append_adds_selected_entries_to_existing_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "output.json"
    _write_secrets_file(
        source_path,
        _secrets_file(
            schema="./source.schema.json",
            entries=[
                _login(name="alpha", env_key="ALPHA_TOKEN", value="alpha-value"),
                _login(name="beta", env_key="BETA_TOKEN", value="beta-value"),
            ],
        ),
    )
    _write_secrets_file(
        output_path,
        _secrets_file(
            schema="./output.schema.json",
            entries=[_login(name="existing", env_key="EXISTING_TOKEN", value="existing-value")],
        ),
    )

    monkeypatch.setattr(actions, "_choose_subset_login_indices", _choose_second_login)

    actions.subset_secrets_file(source_path=source_path, output_path=output_path, output_mode="append", preview_secrets=False)

    output_file = load_secrets_file(output_path)
    assert output_file["$schema"] == "./output.schema.json"
    assert [entry["name"] for entry in output_file["entries"]] == ["existing", "beta"]


def test_subset_secrets_file_create_refuses_existing_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "output.json"
    secrets_file = _secrets_file(schema="./secrets.schema.json", entries=[_login(name="alpha", env_key="ALPHA_TOKEN", value="alpha-value")])
    _write_secrets_file(source_path, secrets_file)
    _write_secrets_file(output_path, secrets_file)

    with pytest.raises(typer.Exit) as exc_info:
        actions.subset_secrets_file(source_path=source_path, output_path=output_path, output_mode="create", preview_secrets=False)

    assert exc_info.value.exit_code == 1
    assert "Pass --append to add entries or --overwrite to replace it." in capsys.readouterr().out


def test_subset_secrets_file_append_requires_existing_output(tmp_path: Path) -> None:
    source_path = tmp_path / "source.json"
    output_path = tmp_path / "output.json"
    _write_secrets_file(
        source_path,
        _secrets_file(schema="./secrets.schema.json", entries=[_login(name="alpha", env_key="ALPHA_TOKEN", value="alpha-value")]),
    )

    with pytest.raises(typer.Exit) as exc_info:
        actions.subset_secrets_file(source_path=source_path, output_path=output_path, output_mode="append", preview_secrets=False)

    assert exc_info.value.exit_code == 1


def _choose_second_login(*, secrets_file: SecretsFile, source_path: Path, preview_secrets: bool) -> list[int]:
    assert source_path.exists()
    assert not preview_secrets
    assert len(secrets_file["entries"]) == 2
    return [1]


def _write_secrets_file(path: Path, secrets_file: SecretsFile) -> None:
    path.write_text(json.dumps(secrets_file, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _secrets_file(*, schema: str, entries: list[Login]) -> SecretsFile:
    return {"$schema": schema, "version": "0.5", "entries": entries}


def _login(*, name: str, env_key: str, value: str) -> Login:
    secret: SecretRecord = {"name": f"{name}-secret", "tags": [], "scopes": [], "keyValues": {env_key: value}}
    return {"name": name, "secrets": [secret]}
