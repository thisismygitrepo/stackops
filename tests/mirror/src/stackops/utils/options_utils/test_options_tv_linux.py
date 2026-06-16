import os
import subprocess
from pathlib import Path

import pytest

from stackops.utils.options_utils import options_tv_linux


def test_tv_temp_parent_uses_env_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    override_dir = tmp_path / "tv temp base"

    monkeypatch.setenv(options_tv_linux.TV_TEMP_DIR_ENV, str(override_dir))

    assert options_tv_linux._tv_temp_parent() == override_dir
    assert override_dir.is_dir()


@pytest.mark.skipif(os.name == "nt", reason="Linux tv helper uses POSIX symlinked channel configs")
def test_select_from_options_uses_home_tmp_results_for_channel_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    home_dir = tmp_path / "home"
    captured_channel_text: list[str] = []
    captured_temp_dirs: list[Path] = []

    monkeypatch.delenv(options_tv_linux.TV_TEMP_DIR_ENV, raising=False)
    monkeypatch.setattr(options_tv_linux.pathlib.Path, "home", lambda: home_dir)

    def fake_run(
        command: list[str],
        *,
        check: bool,
        stdout: int,
        text: bool,
        env: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
        _ = env
        assert command == ["tv", "temp_options"]
        assert check is False
        assert stdout == subprocess.PIPE
        assert text is True

        channel_link = home_dir / ".config" / "television" / "cable" / "temp_options.toml"
        assert channel_link.is_symlink()
        channel_path = channel_link.resolve(strict=True)
        captured_temp_dirs.append(channel_path.parent)
        captured_channel_text.append(channel_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(command, 0, "1\n", "")

    monkeypatch.setattr(options_tv_linux.subprocess, "run", fake_run)

    selected = options_tv_linux.select_from_options(
        {"first": "# First", "second": "# Second"},
        extension="md",
        multi=False,
        preview_size_percent=50,
    )

    expected_parent = home_dir / "tmp_results" / "tmp_files"
    channel_link = home_dir / ".config" / "television" / "cable" / "temp_options.toml"

    assert selected == "second"
    assert captured_temp_dirs
    assert captured_temp_dirs[0].parent == expected_parent
    assert not captured_temp_dirs[0].exists()
    assert not channel_link.exists()
    assert "preview.sh" in captured_channel_text[0]
    assert str(expected_parent) in captured_channel_text[0]
