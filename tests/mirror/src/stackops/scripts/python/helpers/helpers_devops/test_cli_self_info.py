from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

import pytest
import typer

from stackops.scripts.python.helpers.helpers_devops import cli_self_docker, cli_self_info, cli_self_repo


@dataclass(frozen=True)
class DockerInvocation:
    command: tuple[str, ...]
    cwd: Path
    environment: dict[str, str]
    check: bool


@dataclass(frozen=True)
class ProcessResult:
    returncode: int


@pytest.fixture
def docker_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    script_path = tmp_path / "jobs" / "shell" / "docker_build_and_publish.sh"
    script_path.parent.mkdir(parents=True)
    script_path.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    monkeypatch.setattr(cli_self_repo, "developer_repo_root", lambda: tmp_path)
    monkeypatch.delenv("DOCKER_TOKEN", raising=False)
    monkeypatch.delenv("DOCKER_IMAGE_NAMESPACE", raising=False)
    monkeypatch.delenv("DOCKER_LOGIN_TOKEN_ENV_VAR", raising=False)
    return tmp_path


def test_build_without_publish_does_not_resolve_credentials(docker_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    invocations: list[DockerInvocation] = []

    def run_docker_script(command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> ProcessResult:
        invocations.append(DockerInvocation(command=tuple(command), cwd=cwd, environment=dict(env), check=check))
        return ProcessResult(returncode=0)

    def decline_publish(_prompt: str, *, default: bool) -> bool:
        assert default is False
        return False

    def reject_credential_resolution(**_selectors: object) -> NoReturn:
        raise AssertionError("Docker credentials must not be resolved for a local-only build.")

    monkeypatch.setattr(cli_self_info.subprocess, "run", run_docker_script)
    monkeypatch.setattr(cli_self_info.typer, "confirm", decline_publish)
    monkeypatch.setattr(cli_self_docker, "resolve_docker_credentials", reject_credential_resolution)

    cli_self_info.build_docker(
        variant="slim",
        docker_login_name="docker",
        docker_account_name=None,
        docker_secret_name=None,
        docker_secret_tags=None,
        docker_scopes=None,
        docker_token_key=None,
        docker_secrets_path=docker_repo / "missing-secrets.json",
    )

    assert len(invocations) == 1
    build_invocation = invocations[0]
    assert build_invocation.cwd == docker_repo
    assert build_invocation.check is False
    assert build_invocation.environment["STACKOPS_DOCKER_ACTION"] == "build"
    assert build_invocation.environment["VARIANT"] == "slim"
    assert "DOCKER_TOKEN" not in build_invocation.environment
    assert "DOCKER_IMAGE_NAMESPACE" not in build_invocation.environment
    assert "DOCKER_LOGIN_TOKEN_ENV_VAR" not in build_invocation.environment


def test_publish_resolves_credentials_after_successful_build_and_confirmation(docker_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    invocations: list[DockerInvocation] = []
    credentials = cli_self_docker.DockerCredentials(
        login_name="docker",
        secret_name="docker-hub",
        username="aalsaffa",
        token_env_key="DOCKER_TOKEN",
        key_values={"DOCKER_TOKEN": "secret-token", "DOCKER_METADATA": {"scope": "push"}},
    )

    def run_docker_script(command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> ProcessResult:
        action = env["STACKOPS_DOCKER_ACTION"]
        events.append(action)
        invocations.append(DockerInvocation(command=tuple(command), cwd=cwd, environment=dict(env), check=check))
        return ProcessResult(returncode=0)

    def confirm_publish(_prompt: str, *, default: bool) -> bool:
        assert default is False
        events.append("confirm")
        return True

    def resolve_credentials(**_selectors: object) -> cli_self_docker.DockerCredentials:
        events.append("credentials")
        return credentials

    monkeypatch.setattr(cli_self_info.subprocess, "run", run_docker_script)
    monkeypatch.setattr(cli_self_info.typer, "confirm", confirm_publish)
    monkeypatch.setattr(cli_self_docker, "resolve_docker_credentials", resolve_credentials)

    cli_self_info.build_docker(
        variant="slim",
        docker_login_name="docker",
        docker_account_name=None,
        docker_secret_name=None,
        docker_secret_tags=None,
        docker_scopes=None,
        docker_token_key=None,
        docker_secrets_path=docker_repo / "secrets.json",
    )

    assert events == ["build", "confirm", "credentials", "publish"]
    assert len(invocations) == 2
    assert "DOCKER_TOKEN" not in invocations[0].environment
    publish_environment = invocations[1].environment
    assert publish_environment["DOCKER_IMAGE_NAMESPACE"] == "aalsaffa"
    assert publish_environment["DOCKER_LOGIN_TOKEN_ENV_VAR"] == "DOCKER_TOKEN"
    assert publish_environment["DOCKER_TOKEN"] == "secret-token"
    assert publish_environment["DOCKER_METADATA"] == '{"scope":"push"}'


def test_failed_build_does_not_prompt_or_resolve_credentials(docker_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_build(_command: list[str], *, cwd: Path, env: dict[str, str], check: bool) -> ProcessResult:
        assert cwd == docker_repo
        assert env["STACKOPS_DOCKER_ACTION"] == "build"
        assert check is False
        return ProcessResult(returncode=17)

    def reject_confirmation(_prompt: str, *, default: bool) -> NoReturn:
        _ = default
        raise AssertionError("A failed build must not prompt for registry upload.")

    def reject_credential_resolution(**_selectors: object) -> NoReturn:
        raise AssertionError("A failed build must not resolve Docker credentials.")

    monkeypatch.setattr(cli_self_info.subprocess, "run", fail_build)
    monkeypatch.setattr(cli_self_info.typer, "confirm", reject_confirmation)
    monkeypatch.setattr(cli_self_docker, "resolve_docker_credentials", reject_credential_resolution)

    with pytest.raises(typer.Exit) as raised_exit:
        cli_self_info.build_docker(
            variant="ai",
            docker_login_name="docker",
            docker_account_name=None,
            docker_secret_name=None,
            docker_secret_tags=None,
            docker_scopes=None,
            docker_token_key=None,
            docker_secrets_path=docker_repo / "missing-secrets.json",
        )

    assert raised_exit.value.exit_code == 17
