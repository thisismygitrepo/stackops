
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
        return "No matching private key is available in the current GPG keyring. If this file was password-encrypted, rerun the command with --password so machineconfig uses loopback passphrase mode."
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
    try:
        if sys.stdin.isatty():
            env["GPG_TTY"] = os.ttyname(sys.stdin.fileno())
    except OSError:
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
    import re
    url_pattern = r'https?://[^\s]*'
    urls = re.findall(url_pattern, text)
    url_map = {url: f"__URL{index}__" for index, url in enumerate(urls)}
    for url, placeholder in url_map.items():
        text = text.replace(url, placeholder)
    text = re.sub(r'//.*', '', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    for url, placeholder in url_map.items():
        text = text.replace(placeholder, url)
    return text


def read_json(path: "Path", r: bool = False, **kwargs: Any) -> Any:
    from machineconfig.utils.files.read import read_json as _read_json
    return _read_json(path, r=r, **kwargs)


def from_pickle(path: Path) -> Any:
    return pickle.loads(path.read_bytes())


# def pwd2key(password: str, salt: bytes | None = None, iterations: int = 10) -> bytes:  # Derive a secret key from a given password and salt"""
#     import base64
#     if salt is None:
#         import hashlib
#         m = hashlib.sha256()
#         m.update(password.encode(encoding="utf-8"))
#         return base64.urlsafe_b64encode(s=m.digest())  # make url-safe bytes required by Ferent.
#     from cryptography.hazmat.primitives import hashes
#     from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
#     return base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations, backend=None).derive(password.encode()))


# def encrypt(msg: bytes, key: bytes | None = None, pwd: str | None = None, salted: bool = True, iteration: int | None = None, gen_key: bool = False) -> bytes:
#     import base64
#     from cryptography.fernet import Fernet

#     salt, iteration = None, None
#     if pwd is not None:  # generate it from password
#         assert (key is None) and (type(pwd) is str), "❌ You can either pass key or pwd, or none of them, but not both."
#         import secrets
#         iteration = iteration or secrets.randbelow(exclusive_upper_bound=1_000_000)
#         salt = secrets.token_bytes(nbytes=16) if salted else None
#         key_resolved = pwd2key(password=pwd, salt=salt, iterations=iteration)
#     elif key is None:
#         if gen_key:
#             key_resolved = Fernet.generate_key()
#             Path.home().joinpath("dotfiles/creds/data/encrypted_files_key.bytes").write_bytes(key_resolved)
#         else:
#             try:
#                 key_resolved = Path.home().joinpath("dotfiles/creds/data/encrypted_files_key.bytes").read_bytes()
#                 print(f"⚠️ Using key from: {Path.home().joinpath('dotfiles/creds/data/encrypted_files_key.bytes')}")
#             except FileNotFoundError as err:
#                 print("\n" * 3, "~" * 50, """Consider Loading up your dotfiles or pass `gen_key=True` to make and save one.""", "~" * 50, "\n" * 3)
#                 raise FileNotFoundError(err) from err
#     elif isinstance(key, (str, Path)):
#         key_resolved = Path(key).read_bytes()  # a path to a key file was passed, read it:
#     elif type(key) is bytes:
#         key_resolved = key  # key passed explicitly
#     else:
#         raise TypeError("❌ Key must be either a path, bytes object or None.")
#     code = Fernet(key=key_resolved).encrypt(msg)
#     if pwd is not None and salt is not None and iteration is not None:
#         return base64.urlsafe_b64encode(b"%b%b%b" % (salt, iteration.to_bytes(4, "big"), base64.urlsafe_b64decode(code)))
#     return code


# def decrypt(token: bytes, key: bytes | None = None, pwd: str | None = None, salted: bool = True) -> bytes:
#     import base64
#     if pwd is not None:
#         assert key is None, "❌ You can either pass key or pwd, or none of them, but not both."
#         if salted:
#             decoded = base64.urlsafe_b64decode(token)
#             salt, iterations, token = decoded[:16], decoded[16:20], base64.urlsafe_b64encode(decoded[20:])
#             key_resolved = pwd2key(password=pwd, salt=salt, iterations=int.from_bytes(bytes=iterations, byteorder="big"))
#         else:
#             key_resolved = pwd2key(password=pwd)  # trailing `;` prevents IPython from caching the result.
#     elif type(key) is bytes:
#         assert pwd is None, "❌ You can either pass key or pwd, or none of them, but not both."
#         key_resolved = key  # passsed explicitly
#     elif key is None:
#         key_resolved = Path.home().joinpath("dotfiles/creds/data/encrypted_files_key.bytes").read_bytes()  # read from file
#     elif isinstance(key, (str, Path)):
#         key_resolved = Path(key).read_bytes()  # passed a path to a file containing kwy
#     else:
#         raise TypeError(f"❌ Key must be either str, P, Path, bytes or None. Recieved: {type(key)}")
#     from cryptography.fernet import Fernet
#     return Fernet(key=key_resolved).decrypt(token)


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
