from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

import machineconfig.utils.source_of_truth as source_of_truth
from machineconfig.utils.path_extended import PathExtended


MODULE_NAME = "machineconfig.scripts.python.helpers.helpers_croshell.start_slidev"


@dataclass(frozen=True, slots=True)
class SubprocessInvocation:
    args: str | list[str]
    capture_output: bool | None
    check: bool | None
    text: bool | None
    shell: bool | None
    cwd: PathExtended | None


def _load_module(monkeypatch: pytest.MonkeyPatch, config_root: Path) -> ModuleType:
    slidev_components = PathExtended(config_root).joinpath(".cache/slidev/components")
    slidev_components.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(source_of_truth, "CONFIG_ROOT", config_root)
    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def test_execute_with_shell_uses_powershell_on_windows(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module(monkeypatch, tmp_path.joinpath("config"))
    calls: list[SubprocessInvocation] = []

    def fake_platform_system() -> str:
        return "Windows"

    def fake_subprocess_run(
        args: str | list[str],
        capture_output: bool | None = None,
        check: bool | None = None,
        text: bool | None = None,
        shell: bool | None = None,
        cwd: PathExtended | None = None,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(
            SubprocessInvocation(
                args=args,
                capture_output=capture_output,
                check=check,
                text=text,
                shell=shell,
                cwd=cwd,
            )
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    def fake_response_print(self: object) -> object:
        return self

    monkeypatch.setattr(module.platform, "system", fake_platform_system)
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(module.Response, "print", fake_response_print)

    response = module._execute_with_shell("echo hi")

    assert response.returncode == 0
    assert calls == [
        SubprocessInvocation(
            args=["powershell", "-Command", "echo hi"],
            capture_output=True,
            check=False,
            text=True,
            shell=None,
            cwd=None,
        )
    ]


def test_jupyter_to_markdown_normalizes_slide_breaks(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module(monkeypatch, tmp_path.joinpath("config"))
    notebook_path = PathExtended(tmp_path.joinpath("report.ipynb"))
    notebook_path.write_text("{}", encoding="utf-8")
    presentation_dir = notebook_path.parent.joinpath("presentation")
    presentation_dir.mkdir(parents=True, exist_ok=True)
    presentation_dir.joinpath("slides_raw.md").write_text(
        "first\n\n\n\nsecond\n\n---\n\n\n\nthird\n",
        encoding="utf-8",
    )
    commands: list[str] = []

    def fake_execute_with_shell(command: str) -> object:
        commands.append(command)
        return object()

    monkeypatch.setattr(module, "_execute_with_shell", fake_execute_with_shell)

    result = module.jupyter_to_markdown(notebook_path)

    assert result == presentation_dir
    assert presentation_dir.joinpath("slides.md").read_text(encoding="utf-8") == "first\n\n---\n\nsecond\n\n---\n\nthird\n"
    assert commands == [
        f"jupyter nbconvert --to markdown --no-prompt --no-input --output-dir {presentation_dir} --output slides_raw.md {notebook_path}",
        f"jupyter nbconvert --to html --no-prompt --no-input --output-dir {presentation_dir} {notebook_path}",
    ]


def test_main_copies_single_markdown_file_and_runs_slidev(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _load_module(monkeypatch, tmp_path.joinpath("config"))
    report_dir = PathExtended(tmp_path.joinpath("report"))
    report_dir.mkdir(parents=True, exist_ok=True)
    report_dir.joinpath("deck.md").write_text("# deck\n", encoding="utf-8")
    subprocess_calls: list[SubprocessInvocation] = []
    printed_code: list[str] = []
    address_module = ModuleType("address")

    def select_lan_ipv4(prefer_vpn: bool) -> str | None:
        assert prefer_vpn is False
        return "192.0.2.15"

    def fake_subprocess_run(
        args: str | list[str],
        capture_output: bool | None = None,
        check: bool | None = None,
        text: bool | None = None,
        shell: bool | None = None,
        cwd: PathExtended | None = None,
    ) -> subprocess.CompletedProcess[str]:
        subprocess_calls.append(
            SubprocessInvocation(
                args=args,
                capture_output=capture_output,
                check=check,
                text=text,
                shell=shell,
                cwd=cwd,
            )
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    def fake_print_code(code: str, lexer: str, desc: str) -> None:
        _ = lexer, desc
        printed_code.append(code)

    def fake_platform_node() -> str:
        return "demo-host"

    setattr(address_module, "select_lan_ipv4", select_lan_ipv4)
    monkeypatch.setitem(
        sys.modules,
        "machineconfig.scripts.python.helpers.helpers_network.address",
        address_module,
    )
    monkeypatch.setattr(module.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(module, "print_code", fake_print_code)
    monkeypatch.setattr(module.platform, "node", fake_platform_node)

    module.main(directory=str(report_dir), jupyter_file=None)

    slides_path = module.SLIDEV_REPO.joinpath("slides.md")

    assert slides_path.exists()
    assert slides_path.read_text(encoding="utf-8") == "# deck\n"
    assert subprocess_calls == [
        SubprocessInvocation(
            args="bun run dev slides.md -- --remote",
            capture_output=None,
            check=None,
            text=None,
            shell=True,
            cwd=module.SLIDEV_REPO,
        )
    ]
    assert printed_code == ["bun run dev slides.md -- --remote"]
