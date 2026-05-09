from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import agents_impl


def test_confirm_existing_agents_dir_cleanup_asks_before_deleting(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    prompts: list[tuple[str, bool]] = []

    monkeypatch.setattr(agents_impl.sys.stdin, "isatty", lambda: True)

    def fake_confirm(message: str, default: bool) -> bool:
        prompts.append((message, default))
        return True

    monkeypatch.setattr(agents_impl.typer, "confirm", fake_confirm)

    agents_impl._confirm_existing_agents_dir_cleanup(
        agents_dir_obj=agents_dir,
    )

    assert prompts == [
        (
            f"Agents directory already exists and will be deleted to create a clean workspace:\n{agents_dir}\nContinue?",
            False,
        )
    ]


def test_confirm_existing_agents_dir_cleanup_rejects_non_interactive_delete(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    monkeypatch.setattr(agents_impl.sys.stdin, "isatty", lambda: False)

    with pytest.raises(RuntimeError, match="Refusing to delete an existing agents directory in non-interactive mode"):
        agents_impl._confirm_existing_agents_dir_cleanup(
            agents_dir_obj=agents_dir,
        )


def test_confirm_existing_agents_dir_cleanup_aborts_when_user_declines(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()

    monkeypatch.setattr(agents_impl.sys.stdin, "isatty", lambda: True)

    def fake_confirm(message: str, default: bool) -> bool:
        del message, default
        return False

    monkeypatch.setattr(agents_impl.typer, "confirm", fake_confirm)

    with pytest.raises(RuntimeError, match="Aborted: kept existing agents directory"):
        agents_impl._confirm_existing_agents_dir_cleanup(agents_dir_obj=agents_dir)
