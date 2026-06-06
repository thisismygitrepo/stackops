from inspect import Parameter, signature
from pathlib import Path
from typing import get_args

import click
import pytest
import typer

from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets
from stackops.scripts.python.helpers.helpers_devops.cli_config_secrets_candidates import (
    SecretCandidate,
    _candidate_preview,
    build_secret_candidates,
)


def test_secrets_source_defaults_to_both() -> None:
    assert signature(cli_config_secrets.secrets).parameters["secrets_source"].default == "both"


def test_secret_options_have_expected_short_aliases() -> None:
    parameters = signature(cli_config_secrets.secrets).parameters
    expected_aliases = {
        "secrets_path": "-p",
        "secrets_source": "-s",
        "edit": "-e",
        "editor": "-E",
        "interactive": "-i",
        "preview_secrets": "-P",
        "verbose": "-v",
        "login_name": "-n",
        "secret_name": "-N",
        "tags": "-t",
        "login_tags": "-l",
        "secret_tags": "-T",
        "scopes": "-S",
        "keys": "-k",
    }

    for parameter_name, alias in expected_aliases.items():
        assert alias in _option_param_decls(parameters[parameter_name])


def test_secret_source_aliases_resolve_without_reading_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local_path = tmp_path / "local-secrets.json"
    global_path = tmp_path / "global-secrets.json"
    monkeypatch.setattr(cli_config_secrets, "_resolve_global_secrets_path", lambda: global_path)

    assert cli_config_secrets._resolve_secret_sources(secrets_path=local_path, secrets_source="l") == [
        cli_config_secrets.SecretsFileSource(name="local", path=local_path)
    ]
    assert cli_config_secrets._resolve_secret_sources(secrets_path=None, secrets_source="g") == [
        cli_config_secrets.SecretsFileSource(name="global", path=global_path)
    ]
    assert cli_config_secrets._resolve_secret_sources(secrets_path=local_path, secrets_source="b") == [
        cli_config_secrets.SecretsFileSource(name="local", path=local_path),
        cli_config_secrets.SecretsFileSource(name="global", path=global_path),
    ]


def test_bare_edit_keeps_local_source_default(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    resolved_sources: list[cli_config_secrets.SecretsSource] = []
    edited_paths: list[Path] = []
    local_path = tmp_path / "local-secrets.json"

    def resolve_sources(*, secrets_path: Path | None, secrets_source: cli_config_secrets.SecretsSource) -> list[cli_config_secrets.SecretsFileSource]:
        resolved_sources.append(secrets_source)
        assert secrets_path is None
        return [cli_config_secrets.SecretsFileSource(name="local", path=local_path)]

    monkeypatch.setattr(cli_config_secrets, "_resolve_secret_sources", resolve_sources)
    monkeypatch.setattr(cli_config_secrets, "_edit_secrets_file", lambda *, secrets_path, editor: edited_paths.append(secrets_path))

    cli_config_secrets.secrets(ctx=_FakeContext(click.core.ParameterSource.DEFAULT), edit=True)

    assert resolved_sources == ["local"]
    assert edited_paths == [local_path]


def test_both_source_warns_and_skips_missing_source(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing_local_path = tmp_path / "missing-local.json"
    global_path = tmp_path / "global-secrets.json"
    global_path.write_text("not read because loader is monkeypatched", encoding="utf-8")
    loaded_paths: list[Path] = []
    dummy_candidate = _dummy_secret_candidate()

    def load_candidates(secrets_path: Path, *, source_name: str | None = None) -> list[SecretCandidate]:
        loaded_paths.append(secrets_path)
        return [dummy_candidate]

    monkeypatch.setattr(cli_config_secrets, "load_secret_candidates", load_candidates)

    candidates = cli_config_secrets._load_secret_candidates_from_sources(
        [
            cli_config_secrets.SecretsFileSource(name="local", path=missing_local_path),
            cli_config_secrets.SecretsFileSource(name="global", path=global_path),
        ]
    )

    captured = capsys.readouterr()
    assert loaded_paths == [global_path]
    assert candidates == [dummy_candidate]
    assert "Warning: Secrets file not found for local source:" in captured.err
    assert str(missing_local_path) in captured.err


def test_single_source_missing_file_still_errors(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-local.json"

    with pytest.raises(typer.Exit):
        cli_config_secrets._load_secret_candidates_from_sources([cli_config_secrets.SecretsFileSource(name="local", path=missing_path)])


def test_jq_login_entry_command_points_to_login_entry(tmp_path: Path) -> None:
    candidate = _dummy_secret_candidate(json_path="entries[7].secrets[2].keyValues")
    secrets_path = tmp_path / "team secrets.json"

    command = cli_config_secrets._jq_login_entry_command(candidate=candidate, secrets_path=secrets_path)

    assert command == f"jq '.entries[7]' '{secrets_path}'"


def test_interactive_selection_prints_jq_login_entry_hint(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    candidate = _dummy_secret_candidate(json_path="entries[3].secrets[0].keyValues")

    monkeypatch.setattr(
        cli_config_secrets,
        "_resolve_secret_sources",
        lambda *, secrets_path, secrets_source: [cli_config_secrets.SecretsFileSource(name="global", path=Path("unused.json"))],
    )
    monkeypatch.setattr(cli_config_secrets, "_load_secret_candidates_from_sources", lambda secret_sources: [candidate])
    monkeypatch.setattr(cli_config_secrets, "resolve_candidate", lambda **kwargs: candidate)
    monkeypatch.setattr(cli_config_secrets, "_write_env_handoff", lambda key_values: None)

    cli_config_secrets.secrets(ctx=_FakeContext(click.core.ParameterSource.DEFAULT), interactive=True)

    captured = capsys.readouterr()
    assert "Selected login entry jq:" in captured.out
    assert "jq '.entries[3]' .stackops/secrets/secrets.json" in captured.out


def test_interactive_preview_hides_secret_values_by_default() -> None:
    candidate = _dummy_secret_candidate()

    preview = _candidate_preview(candidate)

    assert "API_TOKEN" in preview
    assert "token-value" not in preview
    assert "nested-value" not in preview
    assert "OTHER_TOKEN" not in preview
    assert "login-metadata-value" not in preview


def test_interactive_preview_can_include_secret_values_and_whole_login_entry() -> None:
    candidate = _dummy_secret_candidate()

    preview = _candidate_preview(candidate, include_secret_values=True)

    assert "## Secret values" in preview
    assert "## Login entry" in preview
    assert '"API_TOKEN": "token-value"' in preview
    assert '"nested": "nested-value"' in preview
    assert '"accountName": "example-account"' in preview
    assert '"login-metadata-key": "login-metadata-value"' in preview
    assert '"OTHER_TOKEN": "other-token-value"' in preview


def test_build_secret_candidates_attaches_whole_login_entry_for_preview() -> None:
    candidate = build_secret_candidates(
        {
            "version": "1",
            "entries": [
                {
                    "name": "example",
                    "tags": ["service"],
                    "accountName": "example-account",
                    "metadata": {"login-metadata-key": "login-metadata-value"},
                    "secrets": [
                        {
                            "name": "api",
                            "tags": ["dev"],
                            "scopes": ["read"],
                            "keyValues": {"API_TOKEN": "token-value"},
                        },
                        {
                            "name": "other-api",
                            "tags": ["prod"],
                            "scopes": ["write"],
                            "keyValues": {"OTHER_TOKEN": "other-token-value"},
                        },
                    ],
                }
            ],
        }
    )[0]

    preview = _candidate_preview(candidate, include_secret_values=True)

    assert '"accountName": "example-account"' in preview
    assert '"login-metadata-key": "login-metadata-value"' in preview
    assert '"OTHER_TOKEN": "other-token-value"' in preview


def _dummy_secret_candidate(*, json_path: str = "entries[0].secrets[0].keyValues") -> SecretCandidate:
    return SecretCandidate(
        json_path=json_path,
        login_name="example",
        login_tags=("service",),
        secret_name="api",
        secret_tags=("dev",),
        scopes=("read",),
        key_values={"API_TOKEN": "token-value", "STRUCTURED": {"nested": "nested-value"}},
        searchable_values=("example", "api", "API_TOKEN", "STRUCTURED"),
        login_entry={
            "name": "example",
            "tags": ["service"],
            "accountName": "example-account",
            "metadata": {"login-metadata-key": "login-metadata-value"},
            "secrets": [
                {
                    "name": "api",
                    "tags": ["dev"],
                    "scopes": ["read"],
                    "keyValues": {"API_TOKEN": "token-value", "STRUCTURED": {"nested": "nested-value"}},
                },
                {
                    "name": "other-api",
                    "tags": ["prod"],
                    "scopes": ["write"],
                    "keyValues": {"OTHER_TOKEN": "other-token-value"},
                },
            ],
        },
        source_name="local",
        source_path=Path(".stackops/secrets/secrets.json"),
    )


class _FakeContext:
    def __init__(self, parameter_source: click.core.ParameterSource) -> None:
        self.parameter_source = parameter_source

    def get_parameter_source(self, param_name: str) -> click.core.ParameterSource:
        assert param_name == "secrets_source"
        return self.parameter_source


def _option_param_decls(parameter: Parameter) -> tuple[str, ...]:
    for metadata in get_args(parameter.annotation)[1:]:
        param_decls = getattr(metadata, "param_decls", ())
        if param_decls:
            return tuple(param_decls)
    raise AssertionError(f"Parameter has no Typer option metadata: {parameter.name}")
