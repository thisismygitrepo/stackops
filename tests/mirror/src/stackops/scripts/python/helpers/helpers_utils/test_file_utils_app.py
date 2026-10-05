from pathlib import Path

import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_utils import file_utils_app, pdf, scrape


@pytest.mark.parametrize(("arguments", "enabled"), [([], True), (["--no-enable-resources"], False), (["-e"], False)])
def test_scrape_resources_default_on_with_single_opt_out(
    arguments: list[str], enabled: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[bool] = []

    def capture_scrape(
        *, url: str, output_path: str, selector: str | None, wait_selector: str | None,
        wait: int | None, timeout: int | None, enable_resources: bool, package_spec: str, extra_args: list[str],
    ) -> int:
        assert (url, output_path, selector, wait_selector) == ("https://example.com", "f.md", "article", "article")
        assert (wait, timeout, package_spec, extra_args) == (2000, 60000, "scrapling[shell]", [])
        calls.append(enable_resources)
        return 0

    monkeypatch.setattr(scrape, "run_scrape", capture_scrape)
    result = CliRunner().invoke(file_utils_app.get_app(), ["scrape", "https://example.com", *arguments])

    assert result.exit_code == 0, result.output
    assert calls == [enabled]


@pytest.mark.parametrize(
    ("arguments", "stream_opt_outs"),
    [([], (False, False)), (["--no-compress-streams"], (True, False)), (["-S"], (False, True))],
)
def test_pdf_compression_forwards_opt_outs(
    arguments: list[str], stream_opt_outs: tuple[bool, bool], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    input_path = tmp_path / "input.pdf"
    input_path.write_bytes(b"sample")
    calls: list[tuple[bool, bool]] = []

    def capture_compression(
        pdf_input: str, output: str | None, quality: int, image_dpi: int,
        no_compress_streams: bool, no_object_streams: bool,
    ) -> None:
        assert (pdf_input, output, quality, image_dpi) == (str(input_path), None, 85, 0)
        calls.append((no_compress_streams, no_object_streams))

    monkeypatch.setattr(pdf, "compress_pdf", capture_compression)
    result = CliRunner().invoke(file_utils_app.get_app(), ["pdf-compress", str(input_path), *arguments])

    assert result.exit_code == 0, result.output
    assert calls == [stream_opt_outs]
