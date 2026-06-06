import json
from inspect import Parameter, signature
from pathlib import Path
from typing import get_args

import pytest

from stackops.scripts.python.helpers.helpers_devops import cli_self, cli_self_docker


def test_build_docker_options_have_one_letter_aliases() -> None:
    parameters = signature(cli_self.build_docker).parameters
    expected_aliases = {
        "docker_login_name": "-n",
        "docker_account_name": "-a",
        "docker_secret_name": "-N",
        "docker_tags": "-t",
        "docker_login_tags": "-l",
        "docker_secret_tags": "-T",
        "docker_scopes": "-S",
        "docker_token_key": "-k",
        "docker_secrets_path": "-p",
    }

    for parameter_name, alias in expected_aliases.items():
        assert alias in _option_param_decls(parameters[parameter_name])


def test_docker_credentials_use_login_username(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_search_logins(**kwargs: object) -> list[dict[str, object]]:
        calls.append(kwargs)
        if kwargs["keys"] != ("DOCKER_TOKEN",):
            return []
        return [
            {
                "name": "dockerhub",
                "tags": ["docker"],
                "username": "alice",
                "secrets": [
                    {
                        "name": "publish",
                        "tags": ["docker"],
                        "scopes": ["docker"],
                        "keyValues": {"DOCKER_TOKEN": "dummy-token"},
                    }
                ],
            }
        ]

    monkeypatch.setattr(cli_self_docker, "search_logins", fake_search_logins)

    credentials = cli_self_docker.resolve_docker_credentials(
        secrets_path=None,
        login_name=None,
        account_name=None,
        secret_name=None,
        tags=None,
        login_tags=None,
        secret_tags=None,
        scopes=None,
        token_key=None,
    )

    assert credentials.username == "alice"
    assert credentials.token_env_key == "DOCKER_TOKEN"
    assert credentials.key_values == {"DOCKER_TOKEN": "dummy-token"}
    assert calls[0]["tags"] == ("docker",)


def test_docker_credentials_resolve_through_search_logins_with_temp_file(tmp_path: Path) -> None:
    secrets_path = tmp_path / "secrets.json"
    secrets_path.write_text(
        json.dumps(
            {
                "version": "0.5",
                "entries": [
                    {
                        "name": "dockerhub",
                        "tags": ["docker"],
                        "username": "alice",
                        "secrets": [
                            {
                                "name": "publish",
                                "tags": ["docker"],
                                "scopes": ["docker"],
                                "keyValues": {"DOCKER_TOKEN": "dummy-token"},
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    credentials = cli_self_docker.resolve_docker_credentials(
        secrets_path=secrets_path,
        login_name=None,
        account_name=None,
        secret_name=None,
        tags=None,
        login_tags=None,
        secret_tags=None,
        scopes=None,
        token_key=None,
    )

    assert credentials.login_name == "dockerhub"
    assert credentials.secret_name == "publish"
    assert credentials.username == "alice"
    assert credentials.token_env_key == "DOCKER_TOKEN"


def test_rendered_docker_handoff_script_does_not_include_secret_values(tmp_path: Path) -> None:
    script = cli_self_docker.render_build_docker_shell_script(
        variant="slim",
        repo_root=tmp_path / "repo",
        script_path=tmp_path / "repo/jobs/shell/docker_build_and_publish.sh",
        secret_env_path=tmp_path / "handoff.docker.secrets.env.sh",
        docker_username="alice",
        token_env_key="DOCKER_TOKEN",
        credential_env_keys=("DOCKER_TOKEN",),
    )

    assert "dummy-token" not in script
    assert "statistician" not in script
    assert "export DOCKER_IMAGE_NAMESPACE=alice" in script
    assert "export DOCKER_LOGIN_TOKEN_ENV_VAR=DOCKER_TOKEN" in script
    assert "unset DOCKER_TOKEN" in script


def test_docker_publish_script_no_longer_hardcodes_namespace() -> None:
    script = Path("jobs/shell/docker_build_and_publish.sh").read_text(encoding="utf-8")

    assert "statistician" not in script
    assert "DOCKER_IMAGE_NAMESPACE" in script
    assert "docker login" in script


def test_docker_helper_module_does_not_import_typer() -> None:
    script = Path("src/stackops/scripts/python/helpers/helpers_devops/cli_self_docker.py").read_text(encoding="utf-8")

    assert "import typer" not in script
    assert "typer." not in script


def _option_param_decls(parameter: Parameter) -> tuple[str, ...]:
    for metadata in get_args(parameter.annotation)[1:]:
        param_decls = getattr(metadata, "param_decls", ())
        if param_decls:
            return tuple(param_decls)
    raise AssertionError(f"Parameter has no Typer option metadata: {parameter.name}")
