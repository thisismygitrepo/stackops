import sys

from typer.testing import CliRunner


def test_file_app_scrape_registration_is_lazy() -> None:
    sys.modules.pop("stackops.scripts.python.helpers.helpers_utils.scrape", None)

    from stackops.scripts.python.helpers.helpers_utils.file_utils_app import get_app

    get_app()

    assert "stackops.scripts.python.helpers.helpers_utils.scrape" not in sys.modules


def test_scrape_command_builder_matches_scrapling_example() -> None:
    from stackops.scripts.python.helpers.helpers_utils.scrape import build_scrape_command

    command = build_scrape_command(
        url="https://x.com/julien_c/status/2062524414034423969",
        output_path="f.md",
        wait_selector="article",
        wait=2000,
        timeout=60000,
        enable_resources=True,
        selector="article",
    )

    assert command == [
        "uvx",
        "scrapling[shell]",
        "extract",
        "stealthy-fetch",
        "https://x.com/julien_c/status/2062524414034423969",
        "f.md",
        "--wait-selector",
        "article",
        "--wait",
        "2000",
        "--timeout",
        "60000",
        "--enable-resources",
        "-s",
        "article",
    ]


def test_scrape_cli_validates_then_defers_to_impl(monkeypatch) -> None:
    from stackops.scripts.python.helpers.helpers_utils import scrape as scrape_impl
    from stackops.scripts.python.helpers.helpers_utils.file_utils_app import get_app

    calls: list[dict[str, object]] = []

    def fake_run_scrape(**kwargs) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(scrape_impl, "run_scrape", fake_run_scrape)

    result = CliRunner().invoke(
        get_app(),
        [
            "scrape",
            "https://example.com/post",
            "post.md",
            "--wait-selector",
            "article",
            "--wait",
            "2000",
            "--timeout",
            "60000",
            "--enable-resources",
            "-s",
            "article",
            "--",
            "--debug",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [
        {
            "url": "https://example.com/post",
            "output_path": "post.md",
            "selector": "article",
            "wait_selector": "article",
            "wait": 2000,
            "timeout": 60000,
            "enable_resources": True,
            "package_spec": "scrapling[shell]",
            "extra_args": ["--debug"],
        }
    ]


def test_scrape_short_alias_is_s(monkeypatch) -> None:
    from stackops.scripts.python.helpers.helpers_utils import scrape as scrape_impl
    from stackops.scripts.python.helpers.helpers_utils.file_utils_app import get_app

    calls: list[dict[str, object]] = []

    def fake_run_scrape(**kwargs) -> int:
        calls.append(kwargs)
        return 0

    monkeypatch.setattr(scrape_impl, "run_scrape", fake_run_scrape)

    result = CliRunner().invoke(get_app(), ["s", "https://example.com/post"])

    assert result.exit_code == 0, result.output
    assert calls[0]["url"] == "https://example.com/post"
    assert calls[0]["output_path"] == "f.md"
