
from io import StringIO
from typing import Any, Mapping, Union
from pathlib import Path
import json
import pickle
import configparser


PathLike = Union[str, Path]


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


def pwd2key(password: str, salt: bytes | None = None, iterations: int = 10) -> bytes:  # Derive a secret key from a given password and salt"""
    import base64
    if salt is None:
        import hashlib
        m = hashlib.sha256()
        m.update(password.encode(encoding="utf-8"))
        return base64.urlsafe_b64encode(s=m.digest())  # make url-safe bytes required by Ferent.
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    return base64.urlsafe_b64encode(PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations, backend=None).derive(password.encode()))


def encrypt(msg: bytes, key: bytes | None = None, pwd: str | None = None, salted: bool = True, iteration: int | None = None, gen_key: bool = False) -> bytes:
    import base64
    from cryptography.fernet import Fernet

    salt, iteration = None, None
    if pwd is not None:  # generate it from password
        assert (key is None) and (type(pwd) is str), "❌ You can either pass key or pwd, or none of them, but not both."
        import secrets
        iteration = iteration or secrets.randbelow(exclusive_upper_bound=1_000_000)
        salt = secrets.token_bytes(nbytes=16) if salted else None
        key_resolved = pwd2key(password=pwd, salt=salt, iterations=iteration)
    elif key is None:
        if gen_key:
            key_resolved = Fernet.generate_key()
            Path.home().joinpath("dotfiles/creds/data/encrypted_files_key.bytes").write_bytes(key_resolved)
        else:
            try:
                key_resolved = Path.home().joinpath("dotfiles/creds/data/encrypted_files_key.bytes").read_bytes()
                print(f"⚠️ Using key from: {Path.home().joinpath('dotfiles/creds/data/encrypted_files_key.bytes')}")
            except FileNotFoundError as err:
                print("\n" * 3, "~" * 50, """Consider Loading up your dotfiles or pass `gen_key=True` to make and save one.""", "~" * 50, "\n" * 3)
                raise FileNotFoundError(err) from err
    elif isinstance(key, (str, Path)):
        key_resolved = Path(key).read_bytes()  # a path to a key file was passed, read it:
    elif type(key) is bytes:
        key_resolved = key  # key passed explicitly
    else:
        raise TypeError("❌ Key must be either a path, bytes object or None.")
    code = Fernet(key=key_resolved).encrypt(msg)
    if pwd is not None and salt is not None and iteration is not None:
        return base64.urlsafe_b64encode(b"%b%b%b" % (salt, iteration.to_bytes(4, "big"), base64.urlsafe_b64decode(code)))
    return code


def decrypt(token: bytes, key: bytes | None = None, pwd: str | None = None, salted: bool = True) -> bytes:
    import base64
    if pwd is not None:
        assert key is None, "❌ You can either pass key or pwd, or none of them, but not both."
        if salted:
            decoded = base64.urlsafe_b64decode(token)
            salt, iterations, token = decoded[:16], decoded[16:20], base64.urlsafe_b64encode(decoded[20:])
            key_resolved = pwd2key(password=pwd, salt=salt, iterations=int.from_bytes(bytes=iterations, byteorder="big"))
        else:
            key_resolved = pwd2key(password=pwd)  # trailing `;` prevents IPython from caching the result.
    elif type(key) is bytes:
        assert pwd is None, "❌ You can either pass key or pwd, or none of them, but not both."
        key_resolved = key  # passsed explicitly
    elif key is None:
        key_resolved = Path.home().joinpath("dotfiles/creds/data/encrypted_files_key.bytes").read_bytes()  # read from file
    elif isinstance(key, (str, Path)):
        key_resolved = Path(key).read_bytes()  # passed a path to a file containing kwy
    else:
        raise TypeError(f"❌ Key must be either str, P, Path, bytes or None. Recieved: {type(key)}")
    from cryptography.fernet import Fernet
    return Fernet(key=key_resolved).decrypt(token)
