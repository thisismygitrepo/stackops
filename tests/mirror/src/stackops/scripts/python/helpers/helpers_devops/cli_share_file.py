import pytest
from typer.testing import CliRunner

from stackops.scripts.python.helpers.helpers_devops import cli_nw


def test_receive_accepts_linux_style_exported_croc_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    monkeypatch.setattr(
        "platform.system",
        lambda: "Linux",
    )
    monkeypatch.setattr(
        "stackops.utils.code.print_code",
        lambda code, lexer, desc, subtitle="": captured.update(
            {"printed_code": code, "printed_lexer": lexer, "printed_desc": desc, "printed_subtitle": subtitle}
        ),
    )
    monkeypatch.setattr(
        "stackops.utils.code.exit_then_run_shell_script",
        lambda script, strict=False: captured.update({"executed_script": script, "strict": str(strict)}),
    )

    result = CliRunner().invoke(
        cli_nw.get_app(),
        ["receive", "--", "export", "CROC_SECRET=7121-donor-olympic-bicycle", "croc", "--relay", "10.17.62.206:443", "--yes"],
    )

    assert result.exit_code == 0
    expected_script = """export CROC_SECRET=7121-donor-olympic-bicycle
croc --relay 10.17.62.206:443 --yes"""
    assert captured["executed_script"] == expected_script
    assert captured["printed_code"] == expected_script
    assert captured["printed_lexer"] == "bash"


def test_receive_keeps_rejecting_extra_arguments_after_plain_secret_code() -> None:
    result = CliRunner().invoke(
        cli_nw.get_app(),
        ["receive", "--", "7121-donor-olympic-bicycle", "croc"],
    )

    assert result.exit_code == 1
    assert "Unexpected extra argument after croc receive code: croc" in result.stderr
