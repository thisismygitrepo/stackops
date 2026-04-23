
from io import StringIO
from pathlib import Path
from typing import Any, Mapping, Union
import configparser
import json
import os
import pickle
import shlex
import subprocess
import sys


PathLike = Union[str, Path]


class GpgCommandError(RuntimeError):
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

        details: list[str] = [
            "GPG command failed.",
            f"Command: {_format_command(command)}",
            f"Exit code: {returncode}",
            f"stderr:\n{_format_process_output(stderr)}",
        ]
        if stdout.strip() != "":
            details.append(f"stdout:\n{_format_process_output(stdout)}")
        if hint is not None:
            details.append(f"Hint: {hint}")
        super().__init__("\n\n".join(details))


def _format_command(command: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(command)
    return shlex.join(command)


def _format_process_output(output: str) -> str:
    normalized = output.strip()
    if normalized == "":
        return "<empty>"
    return normalized


def _gpg_hint(stderr: str, pwd: str | None) -> str | None:
    normalized = stderr.lower()
    if pwd is None and "no secret key" in normalized:
        return "No matching private key is available in the current GPG keyring. If this file was password-encrypted, rerun the command with --password so stackops uses loopback passphrase mode."
    if pwd is None and (
        "inappropriate ioctl for device" in normalized
        or "no pinentry" in normalized
        or "cannot open '/dev/tty'" in normalized
        or "can't connect to the agent" in normalized
    ):
        return "GPG could not prompt for a passphrase in this terminal session. Ensure gpg-agent and pinentry are working, or rerun the command with --password if the file uses symmetric encryption."
    if pwd is not None and ("bad session key" in normalized or "bad passphrase" in normalized):
        return "The provided password was rejected by GPG. Verify --password and try again."
    if pwd is not None and "no secret key" in normalized:
        return "This file appears to require a private GPG key rather than the supplied password. Retry without --password if the file was encrypted for your keypair."
    return None


def build_gpg_environment() -> dict[str, str]:
    env = dict(os.environ)
    if env.get("GPG_TTY"):
        return env
    ttyname = getattr(os, "ttyname", None)
    if ttyname is None:
        return env
    try:
        if sys.stdin.isatty():
            env["GPG_TTY"] = ttyname(sys.stdin.fileno())
    except (AttributeError, OSError, ValueError):
        return env
    return env


def _ensure_parent(path: PathLike) -> Path:
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    return path_obj


def save_pickle(obj: Any, path: PathLike, verbose: bool = False) -> Path:
    path_obj = _ensure_parent(path)
    path_obj.write_bytes(pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL))
    if verbose:
        print(f"Saved pickle -> {path_obj}")
    return Path(path_obj)


def save_json(obj: Any, path: PathLike, indent: int | None = None, verbose: bool = False) -> Path:
    path_obj = _ensure_parent(path)
    json_text = json.dumps(obj, indent=indent, ensure_ascii=False)
    path_obj.write_text(f"{json_text}\n", encoding="utf-8")
    if verbose:
        print(f"Saved json -> {path_obj}")
    return Path(path_obj)


def save_ini(path: PathLike, obj: Mapping[str, Mapping[str, Any]], verbose: bool = False) -> Path:
    cp = configparser.ConfigParser()
    for section, values in obj.items():
        cp[section] = {str(k): str(v) for k, v in values.items()}
    path_obj = _ensure_parent(path)
    buffer = StringIO()
    cp.write(buffer)
    path_obj.write_text(buffer.getvalue(), encoding="utf-8")
    if verbose:
        print(f"Saved ini -> {path_obj}")
    return Path(path_obj)


def read_ini(path: "Path", encoding: str | None = None):
    path_obj = Path(path)
    if not path_obj.exists() or path_obj.is_dir():
        raise FileNotFoundError(f"File not found or is a directory: {path}")
    res = configparser.ConfigParser()
    res.read_string(path_obj.read_text(encoding=encoding))
    return res


def remove_c_style_comments(text: str) -> str:
    result: list[str] = []
    index = 0
    in_string = False
    escaping = False

    while index < len(text):
        current = text[index]
        next_index = index + 1
        next_character = text[next_index] if next_index < len(text) else ""

        if in_string:
            result.append(current)
            if escaping:
                escaping = False
            elif current == "\\":
                escaping = True
            elif current == '"':
                in_string = False
            index += 1
            continue

        if current == '"':
            in_string = True
            result.append(current)
            index += 1
            continue

        if current == "/" and next_character == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue

        if current == "/" and next_character == "*":
            index += 2
            while index < len(text):
                if text[index] == "*" and index + 1 < len(text) and text[index + 1] == "/":
                    index += 2
                    break
                if text[index] in "\r\n":
                    result.append(text[index])
                index += 1
            continue

        result.append(current)
        index += 1

    return "".join(result)


def read_json(path: "Path", r: bool = False, **kwargs: Any) -> Any:
    from stackops.utils.files.read import read_json as _read_json
    return _read_json(path, r=r, **kwargs)


def from_pickle(path: Path) -> Any:
    return pickle.loads(path.read_bytes())


def _ensure_file(path: PathLike) -> Path:
    path_obj = Path(path).expanduser()
    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {path_obj}")
    if not path_obj.is_file():
        raise IsADirectoryError(f"Expected a file path, got: {path_obj}")
    return path_obj.resolve()


def _encrypted_gpg_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.gpg")


def _decrypted_gpg_path(path: Path) -> Path:
    if path.name.endswith(".gpg"):
        return path.with_name(path.name.removesuffix(".gpg"))
    return path.with_name(f"decrypted_{path.name}")


def _run_gpg(command: list[str], pwd: str | None = None) -> None:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            input=None if pwd is None else f"{pwd}\n",
            env=build_gpg_environment(),
        )
    except FileNotFoundError as error:
        raise RuntimeError(f"GPG executable not found while running: {_format_command(command)}") from error

    if completed.returncode != 0:
        raise GpgCommandError(
            command=command,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            hint=_gpg_hint(stderr=completed.stderr, pwd=pwd),
        )


def encrypt_file_symmetric(file_path: PathLike, pwd: str) -> Path:
    source = _ensure_file(file_path)
    output_path = _encrypted_gpg_path(source)
    _run_gpg(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase-fd",
            "0",
            "--symmetric",
            "--cipher-algo",
            "AES256",
            "--output",
            str(output_path),
            str(source),
        ],
        pwd=pwd,
    )
    return output_path


def decrypt_file_symmetric(file_path: PathLike, pwd: str) -> Path:
    source = _ensure_file(file_path)
    output_path = _decrypted_gpg_path(source)
    _run_gpg(
        [
            "gpg",
            "--batch",
            "--yes",
            "--pinentry-mode",
            "loopback",
            "--passphrase-fd",
            "0",
            "--decrypt",
            "--output",
            str(output_path),
            str(source),
        ],
        pwd=pwd,
    )
    return output_path


def encrypt_file_asymmetric(file_path: PathLike) -> Path:
    source = _ensure_file(file_path)
    output_path = _encrypted_gpg_path(source)
    _run_gpg(
        [
            "gpg",
            "--batch",
            "--yes",
            "--default-recipient-self",
            "--encrypt",
            "--output",
            str(output_path),
            str(source),
        ]
    )
    return output_path


def decrypt_file_asymmetric(file_path: PathLike) -> Path:
    source = _ensure_file(file_path)
    output_path = _decrypted_gpg_path(source)
    _run_gpg(
        [
            "gpg",
            "--batch",
            "--yes",
            "--decrypt",
            "--output",
            str(output_path),
            str(source),
        ]
    )
    return output_path
