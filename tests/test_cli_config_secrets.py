import json
import re
import subprocess
from pathlib import Path

from typer.testing import CliRunner

from stackops.scripts.python.devops import get_app
from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets


def test_devops_config_help_lists_secrets_command() -> None:
    result = CliRunner().invoke(get_app(), ["c", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "secrets" in result.output
    assert "Define env vars from .stackops/secrets/secrets.json" in result.output


def test_devops_config_secrets_help_lists_edit_and_path_options() -> None:
    result = CliRunner().invoke(get_app(), ["c", "secrets", "--help"], env={"COLUMNS": "220"})

    assert result.exit_code == 0, result.output
    assert "[TERMS]..." in result.output
    assert "Case-insensitive terms used to select one secret bundle" in result.output
    assert "--path" in result.output
    assert "-p" in result.output
    assert "--edit" in result.output
    assert "-e" in result.output
    assert "--interactive" in result.output
    assert "-i" in result.output
    assert "--verbose" in result.output
    assert "-v" in result.output
    assert "--name" in result.output
    assert "-n" in result.output
    assert "--tag" in result.output
    assert "-t" in result.output
    assert "--key" in result.output
    assert "-k" in result.output
    assert "devops config secrets --name aws-dev --tag iam-access-key" in result.output


def test_devops_config_secrets_writes_non_sensitive_handoff_for_unique_keyvalues() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(get_app(), ["c", "secrets", "aws", "dev", "iam-access-key"], env={"OP_PROGRAM_PATH": str(op_path)})

        assert result.exit_code == 0, result.output
        assert "Prepared 3 env variable(s): AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION" in result.output
        assert "AKIA_TEST" not in result.output
        assert "secret-value" not in result.output

        loader_script = op_path.read_text(encoding="utf-8")
        assert "secret-value" not in loader_script
        env_path = _env_path_from_loader(loader_script)
        assert env_path.exists()
        env_script = env_path.read_text(encoding="utf-8")
        assert "export AWS_ACCESS_KEY_ID=AKIA_TEST" in env_script
        assert "export AWS_SECRET_ACCESS_KEY=secret-value" in env_script
        assert "export AWS_DEFAULT_REGION=us-east-1" in env_script


def test_devops_config_secrets_verbose_prints_selection_without_secret_values() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(
            get_app(),
            ["c", "secrets", "-v", "aws", "dev", "iam-access-key"],
            env={"OP_PROGRAM_PATH": str(op_path)},
        )

        assert result.exit_code == 0, result.output
        assert "Selected secret bundle:" in result.output
        assert "Bundle: aws-dev / iam-access-key" in result.output
        assert f"Source: {Path.cwd() / '.stackops' / 'secrets' / 'secrets.json'}" in result.output
        assert "JSON path: entries[1].secrets[0].keyValues" in result.output
        assert "Entry tags: aws, dev" in result.output
        assert "Secret tags: iam-access-key" in result.output
        assert "Scope: development" in result.output
        assert "Defining env vars:" in result.output
        assert "AWS_ACCESS_KEY_ID" in result.output
        assert "AWS_SECRET_ACCESS_KEY" in result.output
        assert "AWS_DEFAULT_REGION" in result.output
        assert "AKIA_TEST" not in result.output
        assert "secret-value" not in result.output


def test_devops_config_secrets_rejects_ambiguous_keyvalues_without_writing_handoff() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(get_app(), ["c", "secrets", "aws", "dev"], env={"OP_PROGRAM_PATH": str(op_path)})

        assert result.exit_code == 1, result.output
        assert "Selection did not identify a unique keyValues entry" in result.output
        assert "matched 2 entries" in result.output
        assert "aws-dev / iam-access-key -> AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION" in result.output
        assert "aws-dev / session-token -> AWS_SESSION_TOKEN" in result.output
        assert "AKIA_TEST" not in result.output
        assert "secret-value" not in result.output
        assert not op_path.exists()


def test_devops_config_secrets_requires_shell_handoff() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())

        result = runner.invoke(get_app(), ["c", "secrets", "github", "token"], env={"OP_PROGRAM_PATH": ""})

        assert result.exit_code == 1, result.output
        assert "OP_PROGRAM_PATH is not set" in result.output


def test_devops_config_secrets_uses_custom_path_for_keyvalues() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        custom_path = Path("private") / "team-secrets.json"
        custom_path.parent.mkdir(parents=True, exist_ok=True)
        custom_path.write_text(json.dumps(_secrets_payload()), encoding="utf-8")
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(
            get_app(),
            ["c", "secrets", "--path", str(custom_path), "github", "personal-access-token"],
            env={"OP_PROGRAM_PATH": str(op_path)},
        )

        assert result.exit_code == 0, result.output
        assert "Prepared 1 env variable(s): GITHUB_TOKEN" in result.output
        loader_script = op_path.read_text(encoding="utf-8")
        env_path = _env_path_from_loader(loader_script)
        assert "export GITHUB_TOKEN=ghp_test" in env_path.read_text(encoding="utf-8")


def test_devops_config_secrets_uses_exact_selectors_without_query_terms() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(
            get_app(),
            ["c", "secrets", "--name", "aws-dev", "--tag", "session-token"],
            env={"OP_PROGRAM_PATH": str(op_path)},
        )

        assert result.exit_code == 0, result.output
        assert "Prepared 1 env variable(s): AWS_SESSION_TOKEN" in result.output
        env_path = _env_path_from_loader(op_path.read_text(encoding="utf-8"))
        assert "export AWS_SESSION_TOKEN=session-value" in env_path.read_text(encoding="utf-8")


def test_devops_config_secrets_exact_selectors_can_be_combined_with_query_terms() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(
            get_app(),
            ["c", "secrets", "--key", "AWS_ACCESS_KEY_ID", "aws"],
            env={"OP_PROGRAM_PATH": str(op_path)},
        )

        assert result.exit_code == 0, result.output
        assert "Prepared 3 env variable(s): AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION" in result.output
        env_path = _env_path_from_loader(op_path.read_text(encoding="utf-8"))
        assert "export AWS_ACCESS_KEY_ID=AKIA_TEST" in env_path.read_text(encoding="utf-8")


def test_devops_config_secrets_interactive_picker_selects_keyvalues(monkeypatch) -> None:
    from stackops.utils.options_utils import tv_options

    def choose_session_token(
        options_to_preview_mapping: dict[str, object],
        extension: str | None,
        multi: bool,
        preview_size_percent: float,
    ) -> str | None:
        assert extension == "md"
        assert multi is False
        assert preview_size_percent == 60.0
        assert len(options_to_preview_mapping) == 2
        assert all("aws-dev /" in label for label in options_to_preview_mapping)
        previews_text = "\n".join(str(preview) for preview in options_to_preview_mapping.values())
        assert "session-value" not in previews_text
        assert "secret-value" not in previews_text
        return next(label for label in options_to_preview_mapping if "session-token" in label)

    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", choose_session_token)

    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_secrets_file(_secrets_payload())
        op_path = Path.cwd() / "handoff.sh"

        result = runner.invoke(
            get_app(),
            ["c", "secrets", "--interactive", "aws"],
            env={"OP_PROGRAM_PATH": str(op_path)},
        )

        assert result.exit_code == 0, result.output
        assert "Prepared 1 env variable(s): AWS_SESSION_TOKEN" in result.output
        env_path = _env_path_from_loader(op_path.read_text(encoding="utf-8"))
        assert "export AWS_SESSION_TOKEN=session-value" in env_path.read_text(encoding="utf-8")


def test_devops_config_secrets_edit_opens_custom_path_and_creates_template(monkeypatch) -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        opened: list[list[str]] = []
        custom_path = Path("private") / "team-secrets.json"

        monkeypatch.setattr(cli_config_secrets.shutil, "which", lambda editor: f"/usr/bin/{editor}")

        def fake_run(args: list[str], check: bool) -> subprocess.CompletedProcess[str]:
            opened.append(args)
            assert check is False
            return subprocess.CompletedProcess(args=args, returncode=0)

        monkeypatch.setattr(cli_config_secrets.subprocess, "run", fake_run)

        result = runner.invoke(get_app(), ["c", "secrets", "--edit", "--path", str(custom_path), "--editor", "nano"])

        assert result.exit_code == 0, result.output
        assert opened == [["/usr/bin/nano", str(Path.cwd() / custom_path)]]
        created = custom_path.read_text(encoding="utf-8")
        assert '"$schema": "./secrets.schema.json"' in created
        assert '"entries"' in created
        assert (custom_path.parent / "secrets.schema.json").exists()


def _write_secrets_file(payload: dict[str, object]) -> None:
    secrets_path = Path(".stackops") / "secrets" / "secrets.json"
    secrets_path.parent.mkdir(parents=True, exist_ok=True)
    secrets_path.write_text(json.dumps(payload), encoding="utf-8")


def _env_path_from_loader(loader_script: str) -> Path:
    match = re.search(r"_stackops_secret_env_file='?([^'\n]+)'?", loader_script)
    assert match is not None, loader_script
    return Path(match.group(1))


def _secrets_payload() -> dict[str, object]:
    return {
        "version": "0.2",
        "entries": [
            {
                "name": "github-personal",
                "tags": ["github", "personal"],
                "username": "octocat",
                "secrets": [
                    {
                        "tags": ["personal-access-token"],
                        "scope": ["repo", "workflow"],
                        "keyValues": {"GITHUB_TOKEN": "ghp_test"},
                    }
                ],
            },
            {
                "name": "aws-dev",
                "tags": ["aws", "dev"],
                "profile": "dev",
                "secrets": [
                    {
                        "tags": ["iam-access-key"],
                        "scope": "development",
                        "keyValues": {
                            "AWS_ACCESS_KEY_ID": "AKIA_TEST",
                            "AWS_SECRET_ACCESS_KEY": "secret-value",
                            "AWS_DEFAULT_REGION": "us-east-1",
                        },
                    },
                    {
                        "tags": ["session-token"],
                        "scope": "development",
                        "keyValues": {"AWS_SESSION_TOKEN": "session-value"},
                    },
                ],
            },
        ],
    }
