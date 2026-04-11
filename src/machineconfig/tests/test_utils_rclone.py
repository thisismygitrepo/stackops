import subprocess

import pytest

import machineconfig.utils.rclone as rclone_module


class _FakeStdout:
    def __init__(self, content: str) -> None:
        self._content = content
        self._index = 0

    def read(self, size: int) -> str:
        if self._index >= len(self._content):
            return ""
        end_index = self._index + size
        chunk = self._content[self._index:end_index]
        self._index = end_index
        return chunk

    def close(self) -> None:
        return None


class _FakePopen:
    def __init__(self, command: list[str], output: str) -> None:
        self.command = command
        self.stdout = _FakeStdout(output)

    def wait(self) -> int:
        return 0


def test_copyto_surfaces_rclone_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["rclone", "copyto", "local.txt", "demo:archive/plain.txt", "--transfers=4"]
        assert check is False
        assert capture_output is True
        assert text is True
        return subprocess.CompletedProcess(command, 3, "", "Failed to copy: object not found\n")

    monkeypatch.setattr(rclone_module.subprocess, "run", fake_run)

    with pytest.raises(rclone_module.RcloneCommandError) as exc_info:
        rclone_module.copyto(
            in_path="local.txt",
            out_path="demo:archive/plain.txt",
            transfers=4,
            show_command=False,
            show_progress=False,
        )

    error_text = str(exc_info.value)
    assert "Command: rclone copyto local.txt demo:archive/plain.txt --transfers=4" in error_text
    assert "Failed to copy: object not found" in error_text
    assert "The requested remote path does not exist." in error_text


def test_copyto_prints_command_and_progress(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    captured_command: dict[str, list[str]] = {}

    def fake_popen(
        command: list[str],
        *,
        stdout: int | None,
        stderr: int | None,
        text: bool,
        bufsize: int,
    ) -> _FakePopen:
        captured_command["value"] = command
        assert stdout == subprocess.PIPE
        assert stderr == subprocess.STDOUT
        assert text is True
        assert bufsize == 1
        return _FakePopen(command, "Transferred: 1 / 1, 100%\n")

    monkeypatch.setattr(rclone_module.subprocess, "Popen", fake_popen)

    rclone_module.copyto(
        in_path="local.txt",
        out_path="demo:archive/plain.txt",
        transfers=2,
        show_command=True,
        show_progress=True,
    )

    assert captured_command["value"] == [
        "rclone",
        "copyto",
        "local.txt",
        "demo:archive/plain.txt",
        "--transfers=2",
        "--progress",
    ]
    captured = capsys.readouterr()
    assert "rclone copyto local.txt demo:archive/plain.txt --transfers=2 --progress" in captured.out
    assert "Transferred: 1 / 1, 100%" in captured.out