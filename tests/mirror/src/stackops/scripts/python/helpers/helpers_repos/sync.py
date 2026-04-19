

from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_repos import sync as sync_module


class FakeTempFile:
    def __init__(self, path: Path) -> None:
        self.name = str(path)
        self._path = path

    def write(self, data: str) -> int:
        self._path.write_text(data, encoding="utf-8")
        return len(data)

    def __enter__(self) -> FakeTempFile:
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        return None


def test_get_zellij_cmd_preserves_current_literal_template() -> None:
    command = sync_module.get_zellij_cmd(wd1=Path("/tmp/local"), wd2=Path("/tmp/remote"))

    assert "{wd1}" in command
    assert "{wd2}" in command
    assert "git status" in command


def test_get_wt_cmd_embeds_both_paths() -> None:
    command = sync_module.get_wt_cmd(
        wd1=sync_module.PathExtended("/tmp/local"),
        wd2=sync_module.PathExtended("/tmp/remote"),
    )

    assert "/tmp/local" in command
    assert "/tmp/remote" in command
    assert "split-pane" in command


def test_inspect_repos_writes_platform_specific_script(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    script_path = tmp_path / "inspect.sh"
    panels: list[object] = []

    monkeypatch.setattr(sync_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(sync_module, "get_zellij_cmd", lambda wd1, wd2: f"inspect {wd1} {wd2}")
    monkeypatch.setattr(sync_module.console, "print", lambda value: panels.append(value))
    import tempfile

    monkeypatch.setattr(
        tempfile,
        "NamedTemporaryFile",
        lambda mode, suffix, delete, encoding: FakeTempFile(script_path),
    )

    sync_module.inspect_repos(repo_local_root="/tmp/local", repo_remote_root="/tmp/remote")

    assert script_path.read_text(encoding="utf-8") == "inspect /tmp/local /tmp/remote"
    assert panels


def test_inspect_repos_rejects_unknown_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sync_module.platform, "system", lambda: "Plan9")

    with pytest.raises(NotImplementedError, match="Platform Plan9 not implemented"):
        sync_module.inspect_repos(repo_local_root="/tmp/local", repo_remote_root="/tmp/remote")
