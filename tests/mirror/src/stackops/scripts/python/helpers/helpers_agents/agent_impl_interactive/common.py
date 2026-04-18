# pyright: reportPrivateUsage=false
from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents.agent_impl_interactive import common


def test_choose_optional_option_prioritizes_current_then_none(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_options: list[str] = []

    def fake_choose_required_option(*, options: tuple[str, ...] | list[str], msg: str, header: str) -> str:
        captured_options.extend(options)
        return common.NONE_LABEL

    monkeypatch.setattr(common, "choose_required_option", fake_choose_required_option)

    result = common.choose_optional_option(options=["alpha", "beta"], current="beta", msg="Pick", header="Header")

    assert result is None
    assert captured_options == ["beta", common.NONE_LABEL, "alpha"]


def test_prompt_text_retries_until_required_value(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    responses = iter(["", " chosen "])

    def fake_input(prompt: str = "") -> str:
        return next(responses)

    monkeypatch.setattr("builtins.input", fake_input)

    result = common.prompt_text(label="Prompt", current=None, required=True, hint="")
    captured = capsys.readouterr()

    assert result == "chosen"
    assert "Prompt is required." in captured.out


def test_editor_scratch_path_uses_repo_tmp_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def fake_get_repo_root(_cwd: Path) -> Path:
        return tmp_path

    def fake_randstr(*, length: int, lower: bool, upper: bool, digits: bool, punctuation: bool) -> str:
        assert length == 6
        assert lower is True
        assert upper is False
        assert digits is False
        assert punctuation is False
        return "abcdef"

    monkeypatch.setattr(common, "get_repo_root", fake_get_repo_root)
    monkeypatch.setattr(common, "randstr", fake_randstr)

    result = common._editor_scratch_path(label="two words", suffix=".md")

    assert result == tmp_path / ".ai" / "tmp_scripts" / "agent_impl_interactive" / "two_words_abcdef.md"
    assert result.parent.is_dir()


def test_prompt_existing_path_retries_until_existing_file(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    existing_dir = tmp_path / "context_dir"
    existing_dir.mkdir()
    existing_file = tmp_path / "context.txt"
    existing_file.write_text("context", encoding="utf-8")
    responses = iter(["missing.txt", str(existing_dir), str(existing_file)])

    def fake_input(prompt: str = "") -> str:
        return next(responses)

    monkeypatch.setattr("builtins.input", fake_input)

    result = common.prompt_existing_path(label="context path", current=None, must_be_file=True)
    captured = capsys.readouterr()

    assert result == str(existing_file.resolve())
    assert "context path does not exist:" in captured.out
    assert "context path must be a file:" in captured.out


def test_prompt_separator_decodes_escape_sequences_without_editor(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_discover_editor_command() -> list[str] | None:
        return None

    def fake_input(prompt: str = "") -> str:
        return r"\n---"

    monkeypatch.setattr(common, "_discover_editor_command", fake_discover_editor_command)
    monkeypatch.setattr("builtins.input", fake_input)

    assert common.prompt_separator(current="---") == "\n---"


def test_separator_is_applicable_for_context_path_counts_text_files(tmp_path: Path) -> None:
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    first_text_file = context_dir / "a.md"
    first_text_file.write_text("alpha", encoding="utf-8")

    assert common.separator_is_applicable_for_context_path(context_dir) is True

    second_text_file = context_dir / "b.txt"
    second_text_file.write_text("beta", encoding="utf-8")

    assert common.separator_is_applicable_for_context_path(context_dir) is False
