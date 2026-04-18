from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

import stackops.utils.path_core as path_core
from stackops.profile import create_shell_profile as create_shell_profile_module
from stackops.settings.shells import bash as bash_shell_assets
from stackops.utils import source_of_truth as source_of_truth_module


@dataclass(slots=True)
class _FakeCompletedProcess:
    returncode: int
    stdout: str
    stderr: str


def test_create_nu_shell_profile_writes_managed_wrapper_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_dir = tmp_path / "nushell"
    copy_calls: list[str] = []

    def fake_copy_assets_to_machine(which: str) -> None:
        copy_calls.append(which)

    monkeypatch.setattr(create_shell_profile_module, "get_nu_shell_profile_path", lambda: config_dir)
    monkeypatch.setattr("stackops.profile.create_helper.copy_assets_to_machine", fake_copy_assets_to_machine)

    create_shell_profile_module.create_nu_shell_profile()

    assert copy_calls == ["settings", "scripts"]
    assert config_dir.joinpath("config.nu").read_text(encoding="utf-8") == (
        create_shell_profile_module.NUSHELL_CONFIG_SOURCE_LINE + "\n"
    )
    assert config_dir.joinpath("env.nu").read_text(encoding="utf-8") == (
        create_shell_profile_module.NUSHELL_ENV_SOURCE_LINE + "\n"
    )


def test_create_default_shell_profile_adds_bash_init_line_and_wsl_history_sync(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile_path = tmp_path / "home" / ".bashrc"
    config_root = Path.home().joinpath(".config", "stackops-test")
    copy_calls: list[str] = []

    def fake_copy_assets_to_machine(which: str) -> None:
        copy_calls.append(which)

    def fake_subprocess_run(
        command: list[str],
        *,
        stdout: int,
        stderr: int,
        text: bool,
        check: bool,
    ) -> _FakeCompletedProcess:
        assert command == ["cat", "/proc/version"]
        assert text is True
        assert check is False
        return _FakeCompletedProcess(
            returncode=0,
            stdout="Linux version 5.15.167.4-microsoft-standard-WSL2",
            stderr="",
        )

    expected_init_script = config_root.joinpath(
        create_shell_profile_module.get_path_reference_library_relative_path(
            module=bash_shell_assets,
            path_reference=create_shell_profile_module.BASH_INIT_PATH_REFERENCE,
        )
    )
    expected_source_line = (
        f"""source {path_core.collapseuser(expected_init_script, placeholder="$HOME")}"""
    )

    monkeypatch.setattr(create_shell_profile_module, "get_shell_profile_path", lambda: profile_path)
    monkeypatch.setattr("stackops.profile.create_helper.copy_assets_to_machine", fake_copy_assets_to_machine)
    monkeypatch.setattr(source_of_truth_module, "CONFIG_ROOT", config_root)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    create_shell_profile_module.create_default_shell_profile()

    shell_profile = profile_path.read_text(encoding="utf-8")

    assert copy_calls == ["settings", "scripts"]
    assert expected_source_line in shell_profile
    assert "\ncd $HOME" in shell_profile
    assert "PROMPT_COMMAND" in shell_profile
