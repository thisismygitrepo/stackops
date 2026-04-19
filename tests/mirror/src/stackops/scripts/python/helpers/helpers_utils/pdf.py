

from pathlib import Path
import sys
from types import ModuleType

import pytest

from stackops.scripts.python.helpers.helpers_utils import pdf as subject


def install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def test_merge_pdfs_builds_uv_command_and_runs_shell_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_log: list[str] = []
    meta_module = ModuleType("stackops.utils.meta")
    code_module = ModuleType("stackops.utils.code")

    def lambda_to_python_script(
        fn: object,
        in_global: bool,
        import_module: bool,
    ) -> str:
        call_log.append(f"lambda:{callable(fn)}:{in_global}:{import_module}")
        return "generated script"

    def get_uv_command_executing_python_script(
        python_script: str,
        uv_with: list[str],
        uv_project_dir: Path | None,
    ) -> tuple[list[str], Path]:
        call_log.append(f"uv:{python_script}:{uv_with}:{uv_project_dir}")
        return (["uv", "run", "generated.py"], Path("/tmp/generated.py"))

    def run_shell_script(
        command: list[str],
        display_script: bool,
        clean_env: bool,
    ) -> None:
        call_log.append(f"run:{command}:{display_script}:{clean_env}")

    setattr(meta_module, "lambda_to_python_script", lambda_to_python_script)
    setattr(code_module, "get_uv_command_executing_python_script", get_uv_command_executing_python_script)
    setattr(code_module, "run_shell_script", run_shell_script)
    install_module(monkeypatch, "stackops.utils.meta", meta_module)
    install_module(monkeypatch, "stackops.utils.code", code_module)

    subject.merge_pdfs(
        pdfs=["a.pdf", "b.pdf"],
        output="merged.pdf",
        compress=True,
    )

    assert call_log == [
        "lambda:True:True:False",
        "uv:generated script:['pypdf']:None",
        "run:['uv', 'run', 'generated.py']:True:False",
    ]


def test_compress_pdf_builds_uv_command_and_runs_shell_script(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_log: list[str] = []
    meta_module = ModuleType("stackops.utils.meta")
    code_module = ModuleType("stackops.utils.code")

    def lambda_to_python_script(
        fn: object,
        in_global: bool,
        import_module: bool,
    ) -> str:
        call_log.append(f"lambda:{callable(fn)}:{in_global}:{import_module}")
        return "compress script"

    def get_uv_command_executing_python_script(
        python_script: str,
        uv_with: list[str],
        uv_project_dir: Path | None,
    ) -> tuple[list[str], Path]:
        call_log.append(f"uv:{python_script}:{uv_with}:{uv_project_dir}")
        return (["uv", "run", "compress.py"], Path("/tmp/compress.py"))

    def run_shell_script(
        command: list[str],
        display_script: bool,
        clean_env: bool,
    ) -> None:
        call_log.append(f"run:{command}:{display_script}:{clean_env}")

    setattr(meta_module, "lambda_to_python_script", lambda_to_python_script)
    setattr(code_module, "get_uv_command_executing_python_script", get_uv_command_executing_python_script)
    setattr(code_module, "run_shell_script", run_shell_script)
    install_module(monkeypatch, "stackops.utils.meta", meta_module)
    install_module(monkeypatch, "stackops.utils.code", code_module)

    subject.compress_pdf(
        pdf_input="input.pdf",
        output="compressed.pdf",
        quality=80,
        image_dpi=144,
        compress_streams=True,
        use_objstms=False,
    )

    assert call_log == [
        "lambda:True:True:False",
        "uv:compress script:['pymupdf']:None",
        "run:['uv', 'run', 'compress.py']:True:False",
    ]
