from __future__ import annotations

import sys
from types import ModuleType

import pytest
import typer

from machineconfig.scripts.python.helpers.helpers_utils import machine_utils_app as subject


def install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def test_wrappers_and_mount_device_delegate_to_underlying_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_log: list[str] = []
    procs_module = ModuleType("machineconfig.utils.procs")
    python_module = ModuleType("machineconfig.scripts.python.helpers.helpers_utils.python")
    cli_config_mount_module = ModuleType("machineconfig.scripts.python.helpers.helpers_devops.cli_config_mount")
    helpers_devops_module = ModuleType("machineconfig.scripts.python.helpers.helpers_devops")

    class ProcessManager:
        def choose_and_kill(self, search_by: str) -> None:
            call_log.append(f"kill:{search_by}")

    def tui_env(which: subject.EnvironmentSelector, tui: bool) -> None:
        call_log.append(f"env:{which}:{tui}")

    def get_machine_specs(hardware: bool) -> None:
        call_log.append(f"specs:{hardware}")

    def list_devices() -> None:
        call_log.append("list-devices")

    def mount_interactive() -> None:
        call_log.append("mount-interactive")

    def mount_device(
        device_query: str,
        mount_point: str,
        read_only: bool,
        backend: subject.MountBackendOption,
    ) -> None:
        call_log.append(f"mount:{device_query}:{mount_point}:{read_only}:{backend}")

    setattr(procs_module, "ProcessManager", ProcessManager)
    setattr(python_module, "tui_env", tui_env)
    setattr(python_module, "get_machine_specs", get_machine_specs)
    setattr(cli_config_mount_module, "list_devices", list_devices)
    setattr(cli_config_mount_module, "mount_interactive", mount_interactive)
    setattr(cli_config_mount_module, "mount_device", mount_device)
    setattr(helpers_devops_module, "cli_config_mount", cli_config_mount_module)
    install_module(monkeypatch, "machineconfig.utils.procs", procs_module)
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_utils.python",
        python_module,
    )
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_devops.cli_config_mount",
        cli_config_mount_module,
    )
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_devops",
        helpers_devops_module,
    )

    subject.kill_process(interactive=True, search_by="C")
    subject.tui_env(which="PATH", tui=True)
    subject.get_machine_specs(hardware=True)
    subject.list_devices()
    subject.mount_device(
        device_query="disk1",
        mount_point="/mnt/disk1",
        interactive=False,
        read_only=True,
        backend="udisksctl",
    )
    subject.mount_device(
        device_query=None,
        mount_point=None,
        interactive=True,
        read_only=False,
        backend="mount",
    )

    assert call_log == [
        "kill:cpu",
        "env:PATH:True",
        "specs:True",
        "list-devices",
        "mount:disk1:/mnt/disk1:True:udisksctl",
        "mount-interactive",
    ]


def test_mount_device_requires_explicit_arguments_when_not_interactive() -> None:
    with pytest.raises(typer.Exit) as exc_info:
        subject.mount_device(
            device_query=None,
            mount_point=None,
            interactive=False,
            read_only=False,
            backend="mount",
        )

    assert exc_info.value.exit_code == 2


def test_get_app_registers_public_commands_and_aliases() -> None:
    app = subject.get_app()
    command_names = {command.name for command in app.registered_commands}

    assert {
        "kill-process",
        "k",
        "environment",
        "v",
        "get-machine-specs",
        "g",
        "list-devices",
        "l",
        "mount",
        "m",
    }.issubset(command_names)
