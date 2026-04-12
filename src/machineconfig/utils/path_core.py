from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.parse import parse_qs, unquote, urlparse

from machineconfig.utils.accessories import randstr

type PathLike = str | os.PathLike[str]
type OptionalPathLike = PathLike | None

__all__ = [
    "PathLike",
    "OptionalPathLike",
    "collapseuser",
    "copy",
    "delete_path",
    "download",
    "move",
    "resolve",
    "symlink_to",
    "timestamp",
    "tmp",
    "tmpdir",
    "tmpfile",
    "validate_name",
    "with_name",
]


def _emit(message: str, *, verbose: bool) -> None:
    if not verbose:
        return
    try:
        print(message)
    except UnicodeEncodeError:
        print("path_core warning: UnicodeEncodeError, could not print message.")


def delete_path(target: PathLike, *, verbose: bool) -> None:
    target_path = Path(target).expanduser()
    if not target_path.exists():
        target_path.unlink(missing_ok=True)
        _emit(f"❌ Could NOT DELETE nonexisting file {target_path!r}.", verbose=verbose)
        return
    if target_path.is_file() or target_path.is_symlink():
        target_path.unlink(missing_ok=True)
    else:
        shutil.rmtree(target_path, ignore_errors=False)
    _emit(f"🗑️ ❌ DELETED {target_path!r}.", verbose=verbose)


def _home_path() -> Path:
    return Path.home()


def _is_user_admin() -> bool:
    if os.name == "nt":
        import ctypes

        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except (AttributeError, OSError):
            return False
    return os.getuid() == 0


def resolve(path: PathLike, *, strict: bool = False) -> Path:
    path_obj = Path(path)
    try:
        return path_obj.resolve(strict=strict)
    except OSError:
        return path_obj


def validate_name(astring: str, *, replace: str = "_") -> str:
    return re.sub(r"[^-a-zA-Z0-9_.()]+", replace, str(astring))


def timestamp(*, fmt: str | None = None, name: str | None = None) -> str:
    prefix = f"{name}_" if name is not None else ""
    return prefix + datetime.now().strftime(fmt or "%Y-%m-%d-%I-%M-%S-%p-%f")


def collapseuser(path: PathLike, *, strict: bool = True, placeholder: str = "~") -> Path:
    path_obj = Path(path)
    if str(path_obj).startswith(placeholder):
        return path_obj
    home_path = _home_path()
    resolved_path = resolve(path_obj.expanduser().absolute(), strict=strict)
    try:
        relative_path = resolved_path.relative_to(home_path)
    except ValueError as error:
        if strict:
            raise ValueError(f"`{home_path}` is not in the subpath of `{path_obj}`") from error
        return path_obj
    return Path(placeholder) / relative_path


def _resolve_destination(
    source: Path,
    *,
    folder: OptionalPathLike = None,
    name: str | None = None,
    path: OptionalPathLike = None,
    default_name: str,
    rel2it: bool = False,
) -> Path:
    if path is not None:
        if folder is not None or name is not None:
            raise ValueError("If `path` is passed, `folder` and `name` cannot be passed.")
        raw_path = source.joinpath(path) if rel2it else Path(path)
        destination = resolve(Path(raw_path).expanduser(), strict=False)
        if destination.is_dir():
            raise ValueError(f"`path` passed is a directory. Use `folder` instead. `{destination}`")
        return destination
    raw_folder: PathLike = source.parent if folder is None else folder
    folder_path = source.joinpath(raw_folder) if rel2it else Path(raw_folder)
    destination_folder = resolve(Path(folder_path).expanduser(), strict=False)
    destination_name = default_name if name is None else name
    return destination_folder / destination_name


def _append_destination(source: Path, *, append: str) -> Path:
    stem = source.name.split(".")[0]
    suffixes = "".join(source.suffixes)
    return source.parent / f"{stem}{append}{suffixes}"


def _sanitize_candidate_filename(name: str) -> str | None:
    candidate = Path(name).name.strip()
    if candidate in {"", ".", ".."}:
        return None
    return candidate


def _filename_from_content_disposition(header_value: str | None) -> str | None:
    if header_value is None:
        return None
    parts = [segment.strip() for segment in header_value.split(";")]
    for part in parts:
        lower = part.lower()
        if lower.startswith("filename*="):
            value = part.split("=", 1)[1].strip().strip('"')
            if "''" in value:
                value = value.split("''", 1)[1]
            decoded = unquote(value)
            sanitized = _sanitize_candidate_filename(decoded)
            if sanitized is not None:
                return sanitized
        if lower.startswith("filename="):
            value = part.split("=", 1)[1].strip().strip('"')
            decoded = unquote(value)
            sanitized = _sanitize_candidate_filename(decoded)
            if sanitized is not None:
                return sanitized
    return None


def _filename_from_url(source_url: str) -> str | None:
    parsed = urlparse(source_url)
    url_candidate = _sanitize_candidate_filename(unquote(Path(parsed.path).name))
    if url_candidate is not None:
        return url_candidate
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    for key, values in query_params.items():
        lower_key = key.lower()
        if "name" in lower_key or "file" in lower_key:
            for value in values:
                sanitized = _sanitize_candidate_filename(unquote(value))
                if sanitized is not None:
                    return sanitized
    return None


def download(
    url: PathLike,
    *,
    folder: OptionalPathLike = None,
    name: str | None = None,
    allow_redirects: bool = True,
    timeout: int | None = None,
    params: object | None = None,
) -> Path:
    import requests

    request_url = str(url)
    response = requests.get(request_url, allow_redirects=allow_redirects, timeout=timeout, params=params)
    response.raise_for_status()
    filename = name
    if filename is None:
        filename = _filename_from_content_disposition(response.headers.get("content-disposition"))
    if filename is None:
        filename = _filename_from_url(response.url)
    if filename is None:
        filename = _filename_from_url(request_url)
    if filename is None:
        filename = validate_name(Path(request_url).name or "downloaded_file")
    destination_root = Path.home().joinpath("Downloads") if folder is None else Path(folder).expanduser()
    destination = destination_root.joinpath(filename)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(response.content)
    return destination


def with_name(
    source: PathLike,
    *,
    name: str,
    verbose: bool = True,
    inplace: bool = False,
    overwrite: bool = False,
    orig: bool = False,
    strict: bool = True,
) -> Path:
    source_path = Path(source)
    destination = source_path.parent / name
    if not inplace:
        return source_path if orig else destination
    if not source_path.exists():
        raise FileNotFoundError(f"`inplace` flag is only relevant if the path exists. It doesn't {source_path}")
    if overwrite and destination.exists():
        delete_path(destination, verbose=verbose)
    if not overwrite and destination.exists():
        if strict:
            raise FileExistsError(f"RENAMING failed. File `{destination}` already exists.")
        _emit(
            f"SKIPPED RENAMING {source_path!r} -> {destination!r} because FileExistsError and strict=False policy.",
            verbose=verbose,
        )
        return source_path if orig else destination
    source_path.rename(destination)
    _emit(f"RENAMED {source_path!r} -> {destination!r}", verbose=verbose)
    return source_path if orig else destination


def move(
    source: PathLike,
    *,
    folder: OptionalPathLike = None,
    name: str | None = None,
    path: OptionalPathLike = None,
    rel2it: bool = False,
    overwrite: bool = False,
    verbose: bool = True,
    parents: bool = True,
    content: bool = False,
) -> Path:
    source_path = Path(source).expanduser()
    destination = _resolve_destination(
        Path(source),
        folder=folder,
        name=name,
        path=path,
        default_name=source_path.absolute().name,
        rel2it=rel2it,
    )
    if parents:
        destination.parent.mkdir(parents=True, exist_ok=True)
    source_resolved = resolve(source_path, strict=False)
    if content:
        if not source_resolved.is_dir():
            raise NotADirectoryError(f"When `content` is True, path must be a directory. It is not: `{source}`")
        for child in source_resolved.glob("*"):
            move(child, folder=destination.parent, overwrite=overwrite, verbose=verbose, parents=parents, content=False)
        return destination
    if overwrite:
        temporary_path = source_resolved.rename(destination.parent.absolute() / randstr())
        delete_path(destination, verbose=verbose)
        temporary_path.rename(destination)
    else:
        try:
            source_resolved.rename(destination)
        except OSError:
            shutil.move(str(source_resolved), str(destination))
    _emit(f"MOVED {Path(source)!r} -> {destination!r}", verbose=verbose)
    return destination


def symlink_to(
    source: PathLike,
    *,
    target: PathLike,
    verbose: bool = True,
    overwrite: bool = False,
    orig: bool = False,
    strict: bool = True,
) -> Path:
    source_path = Path(source).expanduser()
    source_path.parent.mkdir(parents=True, exist_ok=True)
    target_path = resolve(Path(target).expanduser(), strict=False)
    if strict and not target_path.exists():
        raise FileNotFoundError(f"Target path `{target}` (aka `{target_path}`) doesn't exist. This would create a broken link.")
    if overwrite and (source_path.is_symlink() or source_path.exists()):
        delete_path(source_path, verbose=verbose)
    if os.name == "nt" and not _is_user_admin():
        import win32com.shell.shell  # type: ignore[import-not-found]

        win32com.shell.shell.ShellExecuteEx(
            lpVerb="runas",
            lpFile=sys.executable,
            lpParameters=(
                f""" -c "from pathlib import Path; """
                f"""Path(r'{source_path}').symlink_to(r'{target_path}', target_is_directory={target_path.is_dir()!r})" """
            ),
        )
        time.sleep(1)
    else:
        source_path.symlink_to(target_path, target_is_directory=target_path.is_dir())
    _emit(f"LINKED {source_path!r} -> {target_path!r}", verbose=verbose)
    return source_path if orig else target_path


def tmp(*, folder: OptionalPathLike = None, file: str | None = None, root: PathLike = "~/tmp_results") -> Path:
    base = Path(root).expanduser()
    if folder is not None:
        base = base.joinpath(folder)
    if file is not None:
        base = base.joinpath(file)
    target_path = base.parent if file is not None else base
    target_path.mkdir(parents=True, exist_ok=True)
    return base


def tmpdir(*, prefix: str = "") -> Path:
    prefix_segment = f"{prefix}_" if prefix != "" else ""
    return tmp(folder=Path("tmp_dirs").joinpath(f"{prefix_segment}{randstr()}"))


def tmpfile(
    *,
    name: str | None = None,
    suffix: str = "",
    folder: OptionalPathLike = None,
    tstamp: bool = False,
    noun: bool = False,
) -> Path:
    name_concrete = name or randstr(noun=noun)
    timestamp_segment = f"_{timestamp()}" if tstamp else ""
    folder_value: PathLike = Path("tmp_files") if folder is None else folder
    return tmp(folder=folder_value, file=f"{name_concrete}_{randstr()}{timestamp_segment}{suffix}")


def copy(
    source: PathLike,
    *,
    folder: OptionalPathLike = None,
    name: str | None = None,
    path: OptionalPathLike = None,
    content: bool = False,
    verbose: bool = True,
    append: str | None = None,
    overwrite: bool = False,
    orig: bool = False,
) -> Path:
    source_path = Path(source)
    destination = _resolve_destination(
        source_path,
        folder=folder,
        name=name,
        path=path,
        default_name=source_path.name,
        rel2it=False,
    )
    destination = resolve(destination.expanduser(), strict=False)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_resolved = resolve(source_path.expanduser(), strict=False)
    if destination == source_resolved:
        destination = _append_destination(
            source_resolved,
            append=append if append is not None else f"_copy_{randstr()}",
        )
    if overwrite and destination.exists() and not content:
        delete_path(destination, verbose=False)
    if destination.exists() and not overwrite and not content:
        raise FileExistsError(f"Destination already exists: {destination!r}")
    if source_resolved.is_file():
        shutil.copy(str(source_resolved), str(destination))
        _emit(f"COPIED {source_resolved!r} -> {destination!r}", verbose=verbose)
        return source_path if orig else destination
    if source_resolved.is_dir():
        destination_root = destination.parent if content else destination
        shutil.copytree(str(source_resolved), str(destination_root))
        _emit(
            f"COPIED {'content of ' if content else ''}{source_resolved!r} -> {destination_root!r}",
            verbose=verbose,
        )
        return source_path if orig else destination_root
    raise FileNotFoundError(f"Could NOT COPY. Not a file nor a directory: {source_resolved!r}.")
