from typing import Final
import os
import shlex
import subprocess
import sys


_CONFIG_ERROR_MARKERS: Final[tuple[str, ...]] = (
    "didn't find section in config file",
    "config file doesn't contain",
    "failed to create file system for",
)
_MISSING_PATH_MARKERS: Final[tuple[str, ...]] = (
    "directory not found",
    "object not found",
    "file not found",
    "no such file or directory",
)


class RcloneCommandError(RuntimeError):
    def __init__(
        self,
        *,
        command: list[str],
        returncode: int,
        stdout: str,
        stderr: str,
        hint: str | None,
    ) -> None:
        self.command = tuple(command)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.hint = hint

        primary_output = stderr if stderr.strip() != "" else stdout
        primary_label = "stderr" if stderr.strip() != "" else "output"
        details: list[str] = [
            "Rclone command failed.",
            f"Command: {_format_command(command)}",
            f"Exit code: {returncode}",
            f"{primary_label}:\n{_format_process_output(primary_output)}",
        ]
        if stderr.strip() != "" and stdout.strip() != "":
            details.append(f"stdout:\n{_format_process_output(stdout)}")
        if hint is not None:
            details.append(f"Hint: {hint}")
        super().__init__("\n\n".join(details))

    @property
    def combined_output(self) -> str:
        if self.stderr.strip() == "":
            return self.stdout
        if self.stdout.strip() == "":
            return self.stderr
        return f"{self.stderr}\n{self.stdout}"


def _format_command(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def _format_process_output(output: str) -> str:
    normalized = output.strip()
    if normalized == "":
        return "<empty>"
    return normalized


def _is_missing_remote_path_output(normalized_output: str) -> bool:
    if any(marker in normalized_output for marker in _CONFIG_ERROR_MARKERS):
        return False
    return any(marker in normalized_output for marker in _MISSING_PATH_MARKERS)


def _rclone_hint(stdout: str, stderr: str) -> str | None:
    normalized_output = f"{stderr}\n{stdout}".lower()
    if any(marker in normalized_output for marker in _CONFIG_ERROR_MARKERS):
        return "The configured rclone remote could not be resolved. Verify the remote name and your rclone config."
    if _is_missing_remote_path_output(normalized_output):
        return "The requested remote path does not exist."
    return None


def _run_rclone(command: list[str], *, show_command: bool, show_progress: bool) -> subprocess.CompletedProcess[str]:
    if show_command:
        print(_format_command(command))

    try:
        if show_progress:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            if process.stdout is None:
                raise RuntimeError(f"Could not capture rclone output for: {_format_command(command)}")
            output_chunks: list[str] = []
            while True:
                chunk = process.stdout.read(1)
                if chunk == "":
                    break
                output_chunks.append(chunk)
                sys.stdout.write(chunk)
                sys.stdout.flush()
            process.stdout.close()
            completed = subprocess.CompletedProcess(command, process.wait(), "".join(output_chunks), "")
        else:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
    except FileNotFoundError as error:
        raise RuntimeError(f"rclone executable not found while running: {_format_command(command)}") from error

    if completed.returncode != 0:
        raise RcloneCommandError(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            hint=_rclone_hint(stdout=completed.stdout, stderr=completed.stderr),
        )
    return completed


def copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
    command = ["rclone", "copyto", in_path, out_path, f"--transfers={transfers}"]
    if show_progress:
        command.append("--progress")
    _run_rclone(command, show_command=show_command, show_progress=show_progress)


def link(*, target: str, show_command: bool) -> str:
    completed = _run_rclone(["rclone", "link", target], show_command=show_command, show_progress=False)
    for line in completed.stdout.splitlines():
        if line.strip() != "":
            return line.strip()
    raise RuntimeError(f"rclone link returned no output for {target}")


def sync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
    command = ["rclone", "sync", source, target, f"--transfers={transfers}", "--verbose"]
    if show_progress:
        command.append("--progress")
    if delete_during:
        command.append("--delete-during")
    _run_rclone(command, show_command=show_command, show_progress=show_progress)


def bisync(*, source: str, target: str, transfers: int, delete_during: bool, show_command: bool, show_progress: bool) -> None:
    command = [
        "rclone",
        "bisync",
        source,
        target,
        "--resync",
        "--remove-empty-dirs",
        f"--transfers={transfers}",
        "--verbose",
    ]
    if show_progress:
        command.append("--progress")
    if delete_during:
        command.append("--delete-during")
    _run_rclone(command, show_command=show_command, show_progress=show_progress)


def is_missing_remote_path_error(error: RcloneCommandError) -> bool:
    return _is_missing_remote_path_output(error.combined_output.lower())