from typing import Final, Literal, TypedDict, TypeAlias
import json
import os
import shlex
import subprocess
import sys

ShareScope: TypeAlias = Literal["anonymous", "organization"]
ShareScopeChoice: TypeAlias = Literal["anonymous", "a", "organization", "o"]
ShareLinkType: TypeAlias = Literal["view", "edit", "embed"]
ShareLinkTypeChoice: TypeAlias = Literal["view", "v", "edit", "e", "embed", "m"]
SHARE_SCOPES_DISPLAY: Final[str] = "anonymous, a, organization, o"
SHARE_LINK_TYPES_DISPLAY: Final[str] = "view, v, edit, e, embed, m"


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
_REMOTE_WRAPPER_BACKENDS: Final[frozenset[str]] = frozenset({"alias", "crypt", "chunker", "hasher"})


class ShareLinkOptions(TypedDict):
    scope: ShareScope | None
    link_type: ShareLinkType | None


class RcloneConfigError(RuntimeError):
    pass


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


def parse_share_scope(value: object, *, label: str = "share scope") -> ShareScope:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be one of: {SHARE_SCOPES_DISPLAY}.")
    token = value.strip().lower()
    match token:
        case "anonymous" | "a":
            return "anonymous"
        case "organization" | "o":
            return "organization"
        case _:
            raise ValueError(f"{label} must be one of: {SHARE_SCOPES_DISPLAY}.")


def parse_share_link_type(value: object, *, label: str = "share link type") -> ShareLinkType:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be one of: {SHARE_LINK_TYPES_DISPLAY}.")
    token = value.strip().lower()
    match token:
        case "view" | "v":
            return "view"
        case "edit" | "e":
            return "edit"
        case "embed" | "m":
            return "embed"
        case _:
            raise ValueError(f"{label} must be one of: {SHARE_LINK_TYPES_DISPLAY}.")


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


def _rclone_config_dump() -> dict[str, dict[str, object]]:
    try:
        completed = _run_rclone(["rclone", "config", "dump"], show_command=False, show_progress=False)
    except RcloneCommandError:
        raise RcloneConfigError("Could not read rclone config metadata.") from None

    try:
        raw_config = json.loads(completed.stdout)
    except json.JSONDecodeError:
        raise RcloneConfigError("Rclone config metadata was not valid JSON.") from None

    if not isinstance(raw_config, dict):
        raise RcloneConfigError("Rclone config metadata must be a JSON object.")

    config: dict[str, dict[str, object]] = {}
    for remote_name, remote_config in raw_config.items():
        if isinstance(remote_name, str) and isinstance(remote_config, dict):
            config[remote_name] = remote_config
    return config


def _remote_name_from_remote_spec(remote_spec: str) -> str | None:
    if ":" not in remote_spec or (len(remote_spec) > 1 and remote_spec[1] == ":"):
        return None
    remote_name_with_config = remote_spec.split(":", 1)[0]
    remote_name = remote_name_with_config.split(",", 1)[0]
    if remote_name == "":
        return None
    return remote_name


def _resolve_remote_backend_type(*, remote_name: str, config: dict[str, dict[str, object]], seen_remote_names: frozenset[str]) -> str:
    if remote_name in seen_remote_names:
        raise RcloneConfigError(f"Rclone remote '{remote_name}' has a recursive wrapper configuration.")

    remote_config = config.get(remote_name)
    if remote_config is None:
        raise RcloneConfigError(f"Rclone remote '{remote_name}' was not found in rclone config.")

    raw_backend_type = remote_config.get("type")
    if not isinstance(raw_backend_type, str) or raw_backend_type == "":
        raise RcloneConfigError(f"Rclone remote '{remote_name}' does not declare a backend type.")

    backend_type = raw_backend_type.lower()
    if backend_type not in _REMOTE_WRAPPER_BACKENDS:
        return backend_type

    raw_wrapped_remote = remote_config.get("remote")
    if not isinstance(raw_wrapped_remote, str) or raw_wrapped_remote.strip() == "":
        raise RcloneConfigError(f"Rclone wrapper remote '{remote_name}' does not declare a wrapped remote.")

    wrapped_remote_name = _remote_name_from_remote_spec(raw_wrapped_remote)
    if wrapped_remote_name is None:
        raise RcloneConfigError(f"Rclone wrapper remote '{remote_name}' has an invalid wrapped remote reference.")

    return _resolve_remote_backend_type(
        remote_name=wrapped_remote_name, config=config, seen_remote_names=seen_remote_names | frozenset({remote_name})
    )


def remote_backend_type(*, remote_name: str) -> str:
    return _resolve_remote_backend_type(remote_name=remote_name, config=_rclone_config_dump(), seen_remote_names=frozenset())


def _share_link_backend_flags(*, remote_name: str, share_options: ShareLinkOptions) -> list[str]:
    backend_type = remote_backend_type(remote_name=remote_name)
    match backend_type:
        case "onedrive":
            command: list[str] = []
            if share_options["scope"] is not None:
                command.append(f"--onedrive-link-scope={share_options['scope']}")
            if share_options["link_type"] is not None:
                command.append(f"--onedrive-link-type={share_options['link_type']}")
            return command
        case _:
            unsupported_options: list[str] = []
            if share_options["scope"] not in {None, "anonymous"}:
                unsupported_options.append(f"--share-scope {share_options['scope']}")
            if share_options["link_type"] not in {None, "view"}:
                unsupported_options.append(f"--share-type {share_options['link_type']}")
            if unsupported_options:
                raise RcloneConfigError(f"Share option(s) {', '.join(unsupported_options)} are not supported for rclone backend '{backend_type}'.")
            return []


def copyto(*, in_path: str, out_path: str, transfers: int, show_command: bool, show_progress: bool) -> None:
    command = ["rclone", "copyto", in_path, out_path, f"--transfers={transfers}"]
    if show_progress:
        command.append("--progress")
    _run_rclone(command, show_command=show_command, show_progress=show_progress)


def link(*, target: str, remote_name: str, share_options: ShareLinkOptions | None, show_command: bool) -> str:
    command = (
        ["rclone", "link", *_share_link_backend_flags(remote_name=remote_name, share_options=share_options), target]
        if share_options is not None
        else ["rclone", "link", target]
    )
    completed = _run_rclone(command, show_command=show_command, show_progress=False)
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
