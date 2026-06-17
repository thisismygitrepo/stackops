from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import file_utils_app, scrape, surya


def test_scrape_forwards_extra_args_from_typer_context(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_extra_args: list[list[str]] = []

    def fake_run_scrape(
        *,
        url: str,
        output_path: str,
        selector: str | None,
        wait_selector: str | None,
        wait: int | None,
        timeout: int | None,
        enable_resources: bool,
        package_spec: str,
        extra_args: list[str] | None,
    ) -> int:
        assert url == "https://opencode.ai/"
        assert output_path == "m.md"
        assert selector == "article"
        assert wait_selector == "article"
        assert wait == 2000
        assert timeout == 60000
        assert enable_resources
        assert package_spec == "scrapling[shell]"
        captured_extra_args.append([] if extra_args is None else extra_args)
        return 0

    monkeypatch.setattr(scrape, "run_scrape", fake_run_scrape)

    result = CliRunner().invoke(file_utils_app.get_app(), ["scrape", "https://opencode.ai/", "m.md", "--extract-links"])

    assert result.exit_code == 0, result.output
    assert captured_extra_args == [["--extract-links"]]


def test_surya_forwards_extra_args_from_typer_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    data_path = tmp_path.joinpath("page.png")
    data_path.write_bytes(b"fake image")
    resolved_data_path = data_path.resolve()
    captured_extra_args: list[list[str]] = []

    def fake_run_surya(
        *,
        data_path: str,
        task: file_utils_app.SuryaTask,
        output_dir: str | None,
        page_range: str | None,
        images: bool,
        debug: bool,
        keep_server: bool,
        skip_table_detection: bool,
        package_spec: str,
        extra_args: list[str] | None,
    ) -> int:
        assert data_path == str(resolved_data_path)
        assert task == "ocr"
        assert output_dir is None
        assert page_range is None
        assert not images
        assert not debug
        assert not keep_server
        assert not skip_table_detection
        assert package_spec == "surya-ocr"
        captured_extra_args.append([] if extra_args is None else extra_args)
        return 0

    monkeypatch.setattr(surya, "run_surya", fake_run_surya)

    result = CliRunner().invoke(file_utils_app.get_app(), ["ocr", str(data_path), "--force"])

    assert result.exit_code == 0, result.output
    assert captured_extra_args == [["--force"]]
