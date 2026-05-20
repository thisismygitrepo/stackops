from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
from typing import Final

type Command = list[str]

HOVERED_MARKER: Final[str] = "__YAZI_HOVERED__"
SELECTED_MARKER: Final[str] = "__YAZI_SELECTED__"
CUSTOM_COMMAND_ENV: Final[str] = "STACKOPS_OPEN_DEFAULT_APP_COMMAND"
OPEN_TIMEOUT_SECONDS: Final[int] = 15


@dataclass(frozen=True)
class OpenCandidate:
    label: str
    command: Command
    block: bool = False


def split_marked_arguments(arguments: Sequence[str]) -> tuple[str | None, list[str]]:
    tokens = list(arguments)
    try:
        hovered_marker_index = tokens.index(HOVERED_MARKER)
        selected_marker_index = tokens.index(SELECTED_MARKER)
    except ValueError as error:
        raise ValueError("Missing Yazi argument markers.") from error
    if hovered_marker_index >= selected_marker_index:
        raise ValueError("Yazi argument markers are out of order.")
    hovered_tokens = tokens[hovered_marker_index + 1 : selected_marker_index]
    if len(hovered_tokens) > 1:
        raise ValueError("Expected at most one hovered path.")
    hovered_path = hovered_tokens[0] if hovered_tokens else None
    selected_paths = tokens[selected_marker_index + 1 :]
    return hovered_path, selected_paths


def resolve_targets(arguments: Sequence[str]) -> list[Path]:
    tokens = list(arguments)
    if HOVERED_MARKER in tokens or SELECTED_MARKER in tokens:
        hovered_path, selected_paths = split_marked_arguments(tokens)
        raw_targets = selected_paths if selected_paths else ([hovered_path] if hovered_path else [])
    else:
        raw_targets = tokens
    if not raw_targets:
        raise ValueError("No hovered path or selected paths were provided.")

    targets: list[Path] = []
    for raw_target in raw_targets:
        target_path = Path(raw_target).expanduser()
        if not target_path.exists():
            raise ValueError(f"Target does not exist: {target_path}")
        targets.append(target_path.resolve())
    return targets


def normalize_system_name(system: str | None = None) -> str:
    return (system or platform.system()).lower()


def is_wsl() -> bool:
    if "WSL_DISTRO_NAME" in os.environ:
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def is_termux(environ: Mapping[str, str] = os.environ) -> bool:
    return "TERMUX_VERSION" in environ or Path("/data/data/com.termux").exists()


def convert_wsl_path_to_windows(target_path: Path) -> str:
    wslpath = shutil.which("wslpath")
    if wslpath is None:
        return str(target_path)
    completed = subprocess.run(
        [wslpath, "-w", str(target_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    converted_path = completed.stdout.strip()
    if completed.returncode == 0 and converted_path:
        return converted_path
    return str(target_path)


def build_custom_candidate(
    target_path: Path,
    *,
    environ: Mapping[str, str] = os.environ,
    system: str | None = None,
) -> OpenCandidate | None:
    command_template = environ.get(CUSTOM_COMMAND_ENV)
    if not command_template:
        return None
    system_name = normalize_system_name(system)
    posix = system_name != "windows"
    if "{path}" in command_template:
        command = shlex.split(command_template.format(path=str(target_path)), posix=posix)
    else:
        command = [*shlex.split(command_template, posix=posix), str(target_path)]
    return OpenCandidate(label=CUSTOM_COMMAND_ENV, command=command, block=True)


def windows_candidates(target_path: Path) -> list[OpenCandidate]:
    path_string = str(target_path)
    return [
        OpenCandidate(
            label="PowerShell Start-Process",
            command=[
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "Start-Process -FilePath $args[0]",
                path_string,
            ],
        ),
        OpenCandidate(
            label="PowerShell Core Start-Process",
            command=[
                "pwsh",
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "Start-Process -FilePath $args[0]",
                path_string,
            ],
        ),
        OpenCandidate(label="cmd start", command=["cmd.exe", "/C", "start", "", path_string]),
    ]


def wsl_candidates(target_path: Path) -> list[OpenCandidate]:
    windows_path = convert_wsl_path_to_windows(target_path=target_path)
    return [
        OpenCandidate(label="wslview", command=["wslview", str(target_path)]),
        OpenCandidate(
            label="PowerShell Start-Process",
            command=[
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-Command",
                "Start-Process -FilePath $args[0]",
                windows_path,
            ],
        ),
        OpenCandidate(label="cmd start", command=["cmd.exe", "/C", "start", "", windows_path]),
    ]


def linux_candidates(target_path: Path, *, environ: Mapping[str, str] = os.environ) -> list[OpenCandidate]:
    path_string = str(target_path)
    candidates: list[OpenCandidate] = []
    if is_termux(environ=environ):
        candidates.append(OpenCandidate(label="termux-open", command=["termux-open", path_string]))
    if is_wsl():
        candidates.extend(wsl_candidates(target_path=target_path))
    candidates.extend(
        [
            OpenCandidate(label="xdg-open", command=["xdg-open", path_string]),
            OpenCandidate(label="gio open", command=["gio", "open", path_string]),
            OpenCandidate(label="kde-open6", command=["kde-open6", path_string]),
            OpenCandidate(label="kde-open5", command=["kde-open5", path_string]),
            OpenCandidate(label="kioclient5 exec", command=["kioclient5", "exec", path_string]),
            OpenCandidate(label="kioclient exec", command=["kioclient", "exec", path_string]),
            OpenCandidate(label="exo-open", command=["exo-open", path_string]),
            OpenCandidate(label="mimeopen", command=["mimeopen", "-n", path_string], block=True),
            OpenCandidate(label="run-mailcap", command=["run-mailcap", "--action=view", path_string], block=True),
            OpenCandidate(label="see", command=["see", path_string], block=True),
        ]
    )
    return candidates


def build_default_open_candidates(
    target_path: Path,
    *,
    system: str | None = None,
    environ: Mapping[str, str] = os.environ,
) -> list[OpenCandidate]:
    candidates: list[OpenCandidate] = []
    custom_candidate = build_custom_candidate(target_path=target_path, environ=environ, system=system)
    if custom_candidate is not None:
        candidates.append(custom_candidate)

    system_name = normalize_system_name(system)
    if system_name == "darwin":
        candidates.append(OpenCandidate(label="macOS open", command=["open", str(target_path)]))
    elif system_name == "windows":
        candidates.extend(windows_candidates(target_path=target_path))
    else:
        candidates.extend(linux_candidates(target_path=target_path, environ=environ))
    return candidates


def command_is_available(command: Sequence[str]) -> bool:
    return bool(command and shutil.which(command[0]) is not None)


def run_candidate(candidate: OpenCandidate) -> tuple[bool, str | None]:
    try:
        if candidate.block:
            completed = subprocess.run(candidate.command, check=False)
        else:
            completed = subprocess.run(
                candidate.command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=OPEN_TIMEOUT_SECONDS,
            )
    except OSError as error:
        return False, str(error)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {OPEN_TIMEOUT_SECONDS}s"
    if completed.returncode == 0:
        return True, None
    stderr = getattr(completed, "stderr", "") or ""
    detail = stderr.strip() or f"exited with status {completed.returncode}"
    return False, detail


def open_with_native_windows_default(target_path: Path) -> str | None:
    startfile = getattr(os, "startfile", None)
    if not callable(startfile):
        return "os.startfile is unavailable"
    try:
        startfile(str(target_path))
    except OSError as error:
        return str(error)
    return None


def open_target(target_path: Path, *, system: str | None = None) -> list[str]:
    system_name = normalize_system_name(system)
    errors: list[str] = []
    if system_name == "windows":
        native_error = open_with_native_windows_default(target_path=target_path)
        if native_error is None:
            return []
        errors.append(f"Windows default opener: {native_error}")

    unavailable: list[str] = []
    for candidate in build_default_open_candidates(target_path=target_path, system=system):
        if not command_is_available(candidate.command):
            unavailable.append(candidate.label)
            continue
        ok, error = run_candidate(candidate=candidate)
        if ok:
            return []
        errors.append(f"{candidate.label}: {error}")

    if unavailable:
        errors.append(f"Unavailable openers: {', '.join(unavailable)}")
    return errors


def main(arguments: Sequence[str]) -> int:
    try:
        targets = resolve_targets(arguments)
    except ValueError as error:
        sys.stderr.write(f"{error}\n")
        return 1

    had_error = False
    for target_path in targets:
        errors = open_target(target_path=target_path)
        if not errors:
            continue
        had_error = True
        sys.stderr.write(f"Could not open with the OS default app: {target_path}\n")
        for error in errors:
            sys.stderr.write(f"  - {error}\n")
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
