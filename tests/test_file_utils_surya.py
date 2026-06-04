import sys

from typer.testing import CliRunner


def test_file_app_surya_registration_is_lazy() -> None:
    sys.modules.pop("stackops.scripts.python.helpers.helpers_utils.surya", None)

    from stackops.scripts.python.helpers.helpers_utils.file_utils_app import get_app

    get_app()

    assert "stackops.scripts.python.helpers.helpers_utils.surya" not in sys.modules


def test_surya_command_builder_uses_uv_with_surya_package() -> None:
    from stackops.scripts.python.helpers.helpers_utils.surya import build_surya_command

    command = build_surya_command(
        data_path="/tmp/input.pdf",
        task="table",
        output_dir="/tmp/out",
        page_range="0,2-3",
        images=True,
        debug=True,
        keep_server=True,
        skip_table_detection=True,
        package_spec="surya-ocr",
        extra_args=["--task_name", "ocr_without_boxes"],
        uv_executable="uv",
    )

    assert command == [
        "uv",
        "run",
        "--no-project",
        "--with",
        "surya-ocr",
        "surya_table",
        "/tmp/input.pdf",
        "--output_dir",
        "/tmp/out",
        "--page_range",
        "0,2-3",
        "--images",
        "--debug",
        "--keep_server",
        "--skip_table_detection",
        "--task_name",
        "ocr_without_boxes",
    ]


def test_surya_cli_validates_then_defers_to_impl(monkeypatch, tmp_path) -> None:
    from stackops.scripts.python.helpers.helpers_utils import surya as surya_impl
    from stackops.scripts.python.helpers.helpers_utils.file_utils_app import get_app

    input_file = tmp_path / "scan.pdf"
    input_file.write_bytes(b"%PDF-1.4\n")
    output_dir = tmp_path / "surya-results"
    calls: list[dict[str, object]] = []

    def fake_run_surya(**kwargs) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(surya_impl, "run_surya", fake_run_surya)

    result = CliRunner().invoke(
        get_app(),
        [
            "ocr",
            str(input_file),
            "--task",
            "layout",
            "--output-dir",
            str(output_dir),
            "--page-range",
            "0",
            "--images",
            "--",
            "--max-num-seqs",
            "8",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "data_path": str(input_file.resolve()),
            "task": "layout",
            "output_dir": str(output_dir.resolve()),
            "page_range": "0",
            "images": True,
            "debug": False,
            "keep_server": False,
            "skip_table_detection": False,
            "package_spec": "surya-ocr",
            "extra_args": ["--max-num-seqs", "8"],
        }
    ]


def test_surya_short_alias_is_o(monkeypatch, tmp_path) -> None:
    from stackops.scripts.python.helpers.helpers_utils import surya as surya_impl
    from stackops.scripts.python.helpers.helpers_utils.file_utils_app import get_app

    input_file = tmp_path / "scan.pdf"
    input_file.write_bytes(b"%PDF-1.4\n")
    calls: list[dict[str, object]] = []

    def fake_run_surya(**kwargs) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(surya_impl, "run_surya", fake_run_surya)

    result = CliRunner().invoke(get_app(), ["o", str(input_file)])

    assert result.exit_code == 0, result.output
    assert calls[0]["data_path"] == str(input_file.resolve())
