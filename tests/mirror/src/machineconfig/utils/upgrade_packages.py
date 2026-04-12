from __future__ import annotations

from pathlib import Path

import pytest

from machineconfig.utils import upgrade_packages as sut
import machineconfig.utils.code


def test_generate_uv_add_commands_writes_expected_script(tmp_path: Path) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    output_path = tmp_path / "upgrade.sh"
    pyproject_path.write_text(
        """
[project]
dependencies = ["requests>=1", "rich==2"]
version = "8.09"

[project.optional-dependencies]
test = ["pytest>=7"]

[dependency-groups]
dev = ["ruff>=0.1"]
lint = ["pyright>=1"]
""".strip()
        + "\n",
        encoding="utf-8",
    )

    sut.generate_uv_add_commands(pyproject_path=pyproject_path, output_path=output_path)

    script = output_path.read_text(encoding="utf-8")
    assert "uv add --no-cache 'requests' 'rich'" in script
    assert "uv add --no-cache --optional test 'pytest'" in script
    assert "uv add --no-cache --dev 'ruff'" in script
    assert "uv add --no-cache --group lint 'pyright'" in script


def test_resolve_cleanup_targets_deduplicates_inputs_and_preserves_both_scopes() -> None:
    pyproject_data: sut.PyprojectTable = {"project": {"optional-dependencies": {"dev": ["pytest>=7"]}}, "dependency-groups": {"dev": ["ruff>=0.1"]}}

    cleanup_targets = sut.resolve_cleanup_targets(pyproject_data=pyproject_data, group_names=["dev", "dev"])

    assert cleanup_targets == [
        sut.CleanupTarget(kind="optional-dependency", group_name="dev", packages=("pytest",)),
        sut.CleanupTarget(kind="dependency-group", group_name="dev", packages=("ruff",)),
    ]


def test_resolve_cleanup_targets_rejects_unknown_group() -> None:
    with pytest.raises(ValueError, match="Unknown dependency group"):
        sut.resolve_cleanup_targets(pyproject_data={}, group_names=["missing"])


def test_extract_package_name_and_remove_command_handle_dev_group() -> None:
    assert sut.extract_package_name("tool @ git+https://example.com/tool.git ; python_version > '3.11'") == "tool"
    assert sut.build_uv_remove_command(sut.CleanupTarget(kind="dependency-group", group_name="dev", packages=("ruff", "pytest"))) == [
        "uv",
        "remove",
        "--dev",
        "ruff",
        "pytest",
        "--no-sync",
    ]


def test_upgrade_machine_config_version_updates_repo_files_and_syncs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pyproject_path = tmp_path / "pyproject.toml"
    script_path = tmp_path / "script.py"
    shell_path = tmp_path / "deploy.sh"
    dockerfile_path = tmp_path / "Dockerfile.dev"
    pyproject_path.write_text(
        """
[project]
name = "demo"
version = "8.09"
dependencies = ["machineconfig>=8.09"]

[project.optional-dependencies]
extra = ["x>=1"]

[dependency-groups]
dev = ["y>=2"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    script_path.write_text('REQ = "machineconfig>=8.09"\nEXTRA = "machineconfig[extra]>=8.09"\n', encoding="utf-8")
    shell_path.write_text('echo "machineconfig[dev]>=8.09"\n', encoding="utf-8")
    dockerfile_path.write_text('RUN echo "machineconfig>=8.09"\n', encoding="utf-8")
    recorded_commands: list[str] = []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(machineconfig.utils.code, "exit_then_run_shell_script", lambda command: recorded_commands.append(command))

    sut.upgrade_machine_config_version()

    assert 'version = "8.10"' in pyproject_path.read_text(encoding="utf-8")
    assert "machineconfig>=8.10" in script_path.read_text(encoding="utf-8")
    assert "machineconfig[extra]>=8.10" in script_path.read_text(encoding="utf-8")
    assert "machineconfig[dev]>=8.10" in shell_path.read_text(encoding="utf-8")
    assert "machineconfig>=8.10" in dockerfile_path.read_text(encoding="utf-8")
    assert recorded_commands == [f"cd {tmp_path}; uv sync"]
