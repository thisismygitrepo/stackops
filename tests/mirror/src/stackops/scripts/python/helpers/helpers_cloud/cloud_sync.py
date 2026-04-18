from __future__ import annotations

import sys
from dataclasses import dataclass
from types import ModuleType

import pytest

import stackops.utils.code as code_utils
from stackops.scripts.python.helpers.helpers_cloud import cloud_sync


@dataclass(frozen=True, slots=True)
class RunShellInvocation:
    script: str
    display_script: bool
    clean_env: bool


@dataclass(frozen=True, slots=True)
class WrapperInvocation:
    cloud: str
    rclone_cmd: str
    cloud_brand: str


def _install_parse_module(monkeypatch: pytest.MonkeyPatch, *, cloud: str, resolved_source: str, resolved_target: str) -> None:
    module = ModuleType("helpers2")

    def parse_cloud_source_target(
        cloud_config_explicit: object, cloud_config_defaults: object, cloud_config_name: str | None, source: str, target: str
    ) -> tuple[str, str, str]:
        _ = cloud_config_explicit, cloud_config_defaults, cloud_config_name, source, target
        return cloud, resolved_source, resolved_target

    setattr(module, "parse_cloud_source_target", parse_cloud_source_target)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_cloud.helpers2", module)


def test_main_runs_plain_rclone_sync_when_verbose_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_parse_module(monkeypatch, cloud="remote-a", resolved_source="/local/report", resolved_target="remote-a:backup/report")
    cloud_mount_module = ModuleType("cloud_mount")

    def get_mprocs_mount_txt(cloud: str, rclone_cmd: str, cloud_brand: str) -> str:
        _ = cloud, rclone_cmd, cloud_brand
        raise AssertionError("verbose wrapper should not be used")

    setattr(cloud_mount_module, "get_mprocs_mount_txt", get_mprocs_mount_txt)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_cloud.cloud_mount", cloud_mount_module)

    calls: list[RunShellInvocation] = []

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> None:
        calls.append(RunShellInvocation(script=script, display_script=display_script, clean_env=clean_env))

    monkeypatch.setattr(code_utils, "run_shell_script", fake_run_shell_script)

    cloud_sync.main(
        source="ignored",
        target="ignored",
        config=None,
        transfers=7,
        root="root",
        key=None,
        pwd=None,
        encrypt=False,
        zip_=False,
        bisync=False,
        delete=True,
        verbose=False,
    )

    assert calls == [
        RunShellInvocation(
            script='rclone sync -P "/local/report" "remote-a:backup/report" --delete-during --transfers=7 --progress --transfers=7 --verbose --delete-during',
            display_script=True,
            clean_env=False,
        )
    ]


def test_main_wraps_bisync_command_when_verbose_is_true(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_parse_module(monkeypatch, cloud="remote-b", resolved_source="remote-b:/docs", resolved_target="/local/docs")
    wrapper_calls: list[WrapperInvocation] = []
    cloud_mount_module = ModuleType("cloud_mount")

    def get_mprocs_mount_txt(cloud: str, rclone_cmd: str, cloud_brand: str) -> str:
        wrapper_calls.append(WrapperInvocation(cloud=cloud, rclone_cmd=rclone_cmd, cloud_brand=cloud_brand))
        return "wrapped-script"

    setattr(cloud_mount_module, "get_mprocs_mount_txt", get_mprocs_mount_txt)
    monkeypatch.setitem(sys.modules, "stackops.scripts.python.helpers.helpers_cloud.cloud_mount", cloud_mount_module)

    calls: list[RunShellInvocation] = []

    def fake_run_shell_script(script: str, display_script: bool, clean_env: bool) -> None:
        calls.append(RunShellInvocation(script=script, display_script=display_script, clean_env=clean_env))

    monkeypatch.setattr(code_utils, "run_shell_script", fake_run_shell_script)

    cloud_sync.main(
        source="ignored",
        target="ignored",
        config=None,
        transfers=3,
        root="root",
        key=None,
        pwd=None,
        encrypt=False,
        zip_=False,
        bisync=True,
        delete=False,
        verbose=True,
    )

    assert wrapper_calls == [
        WrapperInvocation(
            cloud="remote-b",
            rclone_cmd="rclone bisync 'remote-b:/docs' '/local/docs' --resync --progress --transfers=3 --verbose",
            cloud_brand="Unknown",
        )
    ]
    assert calls == [RunShellInvocation(script="wrapped-script", display_script=True, clean_env=False)]
