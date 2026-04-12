from __future__ import annotations

import sys
from types import ModuleType

import pytest

from machineconfig.scripts.python.helpers.helpers_utils import file_utils_app as subject


def install_module(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    module: ModuleType,
) -> None:
    monkeypatch.setitem(sys.modules, name, module)


def test_wrapper_functions_delegate_to_underlying_modules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_log: list[str] = []
    python_module = ModuleType("machineconfig.scripts.python.helpers.helpers_utils.python")
    download_module = ModuleType("machineconfig.scripts.python.helpers.helpers_utils.download")
    pdf_module = ModuleType("machineconfig.scripts.python.helpers.helpers_utils.pdf")
    read_db_module = ModuleType("machineconfig.scripts.python.helpers.helpers_utils.read_db_cli_tui")

    def edit_file_with_hx(path: str | None) -> None:
        call_log.append(f"edit:{path}")

    def download(
        url: str | None,
        decompress: bool,
        output: str | None,
        output_dir: str | None,
    ) -> None:
        call_log.append(f"download:{url}:{decompress}:{output}:{output_dir}")

    def merge_pdfs(
        pdfs: list[str],
        output: str | None,
        compress: bool,
    ) -> None:
        call_log.append(f"merge:{pdfs}:{output}:{compress}")

    def compress_pdf(
        pdf_input: str,
        output: str | None,
        quality: int,
        image_dpi: int,
        compress_streams: bool,
        use_objstms: bool,
    ) -> None:
        call_log.append(
            f"compress:{pdf_input}:{output}:{quality}:{image_dpi}:{compress_streams}:{use_objstms}"
        )

    def app(
        path: str | None,
        backend: subject.DatabaseBackend,
        read_only: bool,
        theme: str | None,
        limit: int | None,
    ) -> None:
        call_log.append(f"read-db:{path}:{backend}:{read_only}:{theme}:{limit}")

    setattr(python_module, "edit_file_with_hx", edit_file_with_hx)
    setattr(download_module, "download", download)
    setattr(pdf_module, "merge_pdfs", merge_pdfs)
    setattr(pdf_module, "compress_pdf", compress_pdf)
    setattr(read_db_module, "app", app)
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_utils.python",
        python_module,
    )
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_utils.download",
        download_module,
    )
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_utils.pdf",
        pdf_module,
    )
    install_module(
        monkeypatch,
        "machineconfig.scripts.python.helpers.helpers_utils.read_db_cli_tui",
        read_db_module,
    )

    subject.edit_file_with_hx(path="file.txt")
    subject.download(url="https://example.com", decompress=True, output="out.bin", output_dir=None)
    subject.merge_pdfs(pdfs=["a.pdf", "b.pdf"], output="merged.pdf", compress=True)
    subject.compress_pdf(
        pdf_input="input.pdf",
        output="compressed.pdf",
        quality=70,
        image_dpi=144,
        compress_streams=False,
        use_objstms=True,
    )
    subject.read_db_cli_tui(
        path="db.sqlite",
        backend="rainfrog",
        read_only=True,
        theme="forest",
        limit=20,
    )

    assert call_log == [
        "edit:file.txt",
        "download:https://example.com:True:out.bin:None",
        "merge:['a.pdf', 'b.pdf']:merged.pdf:True",
        "compress:input.pdf:compressed.pdf:70:144:False:True",
        "read-db:db.sqlite:rainfrog:True:forest:20",
    ]


def test_get_app_registers_public_commands_and_aliases() -> None:
    app = subject.get_app()
    command_names = {command.name for command in app.registered_commands}

    assert {
        "edit",
        "e",
        "download",
        "d",
        "pdf-merge",
        "p",
        "pm",
        "pdf-compress",
        "c",
        "pc",
        "read-db",
        "r",
        "db",
    }.issubset(command_names)
