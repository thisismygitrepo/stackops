import pytest

from stackops.scripts.python import agents


def test_apply_headroom_uses_resolved_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return "/opt/bin/headroom"

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    command = agents._apply_headroom(command=["codex", "--dangerously-bypass-approvals-and-sandbox"], agent="codex", headroom=True)

    assert command == ["/opt/bin/headroom", "wrap", "codex", "--", "--dangerously-bypass-approvals-and-sandbox"]


def test_apply_headroom_rejects_missing_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return None

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    with pytest.raises(ValueError, match="Required command not found: headroom"):
        agents._apply_headroom(command=["codex"], agent="codex", headroom=True)


def test_apply_headroom_rejects_unsupported_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_which(command: str) -> str | None:
        assert command == "headroom"
        return "/opt/bin/headroom"

    monkeypatch.setattr(agents.shutil, "which", fake_which)

    with pytest.raises(ValueError, match="headroom does not support opencode"):
        agents._apply_headroom(command=["omp"], agent="opencode", headroom=True)
