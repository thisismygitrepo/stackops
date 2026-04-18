from __future__ import annotations

import bz2
import gzip
import lzma
from pathlib import Path
import tarfile
from typing import Literal
import zipfile

from stackops.utils.accessories import randstr
from stackops.utils.code import run_lambda_function
from stackops.utils.path_core import delete_path

type FileMode = Literal["r", "w", "x", "a"]

DECOMPRESS_SUPPORTED_FORMATS: tuple[str, ...] = (
    ".tar.gz",
    ".tgz",
    ".tar",
    ".gz",
    ".tar.bz",
    ".tbz",
    ".tar.xz",
    ".zip",
    ".7z",
    ".tar.bz2",
    ".tbz2",
    ".xz",
)


def _emit(message: str, verbose: bool) -> None:
    if not verbose:
        return
    try:
        print(message)
    except UnicodeEncodeError:
        print("path_compression warning: UnicodeEncodeError, could not print message.")


def _resolve_output_path(source: Path, *, folder: Path | None, name: str | None, path: Path | None, default_name: str) -> Path:
    if path is not None:
        if folder is not None or name is not None:
            raise ValueError("If `path` is passed, `folder` and `name` cannot be passed.")
        resolved_path = path.expanduser().resolve()
        if resolved_path.is_dir():
            raise ValueError(f"`path` passed is a directory. Use `folder` instead. `{resolved_path}`")
        return resolved_path
    resolved_folder = (source.parent if folder is None else folder).expanduser().resolve()
    resolved_name = default_name if name is None else name
    return resolved_folder / resolved_name


def _finalize_result(*, source: Path, result: Path, orig: bool, inplace: bool, verbose: bool, message: str) -> Path:
    _emit(message, verbose)
    if inplace:
        delete_path(source, verbose=False)
        _emit(f"DELETED 🗑️❌ {source!r}.", verbose)
    return source if orig else result


def _archive_root(source: Path, arcname: str | None) -> Path:
    if arcname is None:
        return Path(source.name)
    arcname_path = Path(arcname)
    return arcname_path if arcname_path.name == source.name else arcname_path / source.name


def _iter_archive_members(source: Path) -> list[Path]:
    return sorted(source.rglob("*"), key=lambda candidate: candidate.as_posix())


def _split_embedded_archive_path(source: Path) -> tuple[Path, Path | None]:
    parts = source.expanduser().parts
    for index, part in enumerate(parts):
        if ".zip" in part or ".7z" in part:
            archive_path = Path(*parts[: index + 1]).expanduser().resolve()
            remainder = parts[index + 1 :]
            if len(remainder) == 0:
                return archive_path, None
            return archive_path, Path(*remainder)
    return source.expanduser().resolve(), None


def _strip_suffix(name: str, suffix: str, replacement: str = "") -> str:
    if not name.endswith(suffix):
        raise ValueError(f"`{name}` does not end with `{suffix}`.")
    return f"{name[: -len(suffix)]}{replacement}"


def _default_unbz_name(source: Path) -> str:
    return source.name.replace(".bz", "").replace(".tbz", ".tar")


def _extract_7z_archive(archive_path: Path, destination: Path) -> None:
    archive_path_str = str(archive_path)
    destination_str = str(destination)

    def unzip_7z(archive_path_raw: str, dest_dir_raw: str) -> None:
        import py7zr  # type: ignore[reportMissingTypeStubs]

        archive_path_obj = Path(archive_path_raw)
        destination_obj = Path(dest_dir_raw)
        if not archive_path_obj.is_file():
            raise FileNotFoundError(f"Archive file not found: {archive_path_obj!r}")
        destination_obj.mkdir(parents=True, exist_ok=True)
        with py7zr.SevenZipFile(str(archive_path_obj), mode="r") as archive:
            archive.extractall(path=str(destination_obj))

    run_lambda_function(lambda: unzip_7z(archive_path_raw=archive_path_str, dest_dir_raw=destination_str), uv_with=["py7zr"], uv_project_dir=None)


def zip_path(
    source: Path,
    *,
    path: Path | None,
    folder: Path | None,
    name: str | None,
    arcname: str | None,
    inplace: bool,
    verbose: bool,
    content: bool,
    orig: bool,
    mode: FileMode,
) -> Path:
    source_resolved = source.expanduser().resolve()
    if not source_resolved.exists():
        raise FileNotFoundError(source_resolved)
    destination = _resolve_output_path(source_resolved, folder=folder, name=name, path=path, default_name=source_resolved.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output_zip = destination if destination.suffix == ".zip" else destination.with_name(f"{destination.name}.zip")
    archive_root = _archive_root(source_resolved, arcname)
    with zipfile.ZipFile(output_zip, mode=mode) as archive:
        if source_resolved.is_file():
            archive.write(filename=source_resolved, arcname=archive_root.as_posix(), compress_type=zipfile.ZIP_DEFLATED)
        elif source_resolved.is_dir():
            if not content and not any(source_resolved.iterdir()):
                archive.writestr(f"{archive_root.as_posix().rstrip('/')}/", "")
            for member in _iter_archive_members(source_resolved):
                relative_member = member.relative_to(source_resolved)
                archive_name = relative_member if content else archive_root / relative_member
                if member.is_dir():
                    archive.writestr(f"{archive_name.as_posix().rstrip('/')}/", "")
                    continue
                archive.write(member, archive_name.as_posix(), compress_type=zipfile.ZIP_DEFLATED)
        else:
            raise ValueError(f"Cannot zip non-file non-directory path: {source_resolved!r}")
    return _finalize_result(
        source=source_resolved,
        result=output_zip,
        orig=orig,
        inplace=inplace,
        verbose=verbose,
        message=f"ZIPPED {source_resolved!r} ==> {output_zip!r}",
    )


def unzip_path(
    source: Path,
    *,
    folder: Path | None,
    path: Path | None,
    name: str | None,
    verbose: bool,
    content: bool,
    inplace: bool,
    overwrite: bool,
    orig: bool,
    pwd: str | None,
    tmp: bool,
    pattern: str | None,
    merge: bool,
) -> Path:
    if merge:
        raise AssertionError("I have not implemented this yet")
    if path is not None:
        raise AssertionError("I have not implemented this yet")
    if pattern is not None:
        raise NotImplementedError("`pattern` is not implemented.")
    if tmp:
        tmp_folder = Path.home().joinpath("tmp_results", "tmp_unzips", randstr())
        tmp_folder.mkdir(parents=True, exist_ok=True)
        return unzip_path(
            source=source,
            folder=tmp_folder,
            path=None,
            name=name,
            verbose=verbose,
            content=True,
            inplace=inplace,
            overwrite=overwrite,
            orig=orig,
            pwd=pwd,
            tmp=False,
            pattern=None,
            merge=False,
        ).joinpath(source.stem)

    archive_path, embedded_member = _split_embedded_archive_path(source)
    target_name = embedded_member.as_posix() if embedded_member is not None else (None if name is None else Path(name).as_posix())
    destination_root = archive_path.parent / archive_path.stem if folder is None else folder.expanduser().resolve() / archive_path.stem
    extraction_root = destination_root.parent if content else destination_root
    extraction_root.mkdir(parents=True, exist_ok=True)
    if archive_path.suffix == ".7z":
        raise NotImplementedError("I have not implemented this yet")

    with zipfile.ZipFile(archive_path, "r") as archive:
        if overwrite:
            if target_name is not None:
                delete_path(extraction_root / target_name, verbose=True)
            elif content:
                top_level_entries = {Path(entry).parts[0] for entry in archive.namelist() if entry != "" and len(Path(entry).parts) > 0}
                for entry in sorted(top_level_entries):
                    delete_path(extraction_root / entry, verbose=True)
            else:
                delete_path(destination_root, verbose=True)
        password = None if pwd is None else pwd.encode()
        if target_name is None:
            archive.extractall(path=extraction_root, pwd=password)
            result = extraction_root
        else:
            archive.extract(member=target_name, path=extraction_root, pwd=password)
            result = extraction_root / target_name
    return _finalize_result(
        source=archive_path, result=result, orig=orig, inplace=inplace, verbose=verbose, message=f"UNZIPPED {archive_path!r} ==> {result!r}"
    )


def untar_path(source: Path, *, folder: Path | None, name: str | None, path: Path | None, inplace: bool, orig: bool, verbose: bool) -> Path:
    source_resolved = source.expanduser().resolve()
    destination = _resolve_output_path(source_resolved, folder=folder, name=name, path=path, default_name=_strip_suffix(source_resolved.name, ".tar"))
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(source_resolved, "r") as archive:
        archive.extractall(path=destination)
    return _finalize_result(
        source=source_resolved,
        result=destination,
        orig=orig,
        inplace=inplace,
        verbose=verbose,
        message=f"UNTARRED {source_resolved!r} ==> {destination!r}",
    )


def ungz_path(source: Path, *, folder: Path | None, name: str | None, path: Path | None, inplace: bool, orig: bool, verbose: bool) -> Path:
    source_resolved = source.expanduser().resolve()
    destination = _resolve_output_path(source_resolved, folder=folder, name=name, path=path, default_name=_strip_suffix(source_resolved.name, ".gz"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(gzip.decompress(source_resolved.read_bytes()))
    return _finalize_result(
        source=source_resolved,
        result=destination,
        orig=orig,
        inplace=inplace,
        verbose=verbose,
        message=f"UNGZED {source_resolved!r} ==> {destination!r}",
    )


def unxz_path(source: Path, *, folder: Path | None, name: str | None, path: Path | None, inplace: bool, orig: bool, verbose: bool) -> Path:
    source_resolved = source.expanduser().resolve()
    destination = _resolve_output_path(source_resolved, folder=folder, name=name, path=path, default_name=_strip_suffix(source_resolved.name, ".xz"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(lzma.decompress(source_resolved.read_bytes()))
    return _finalize_result(
        source=source_resolved,
        result=destination,
        orig=orig,
        inplace=inplace,
        verbose=verbose,
        message=f"UNXZED {source_resolved!r} ==> {destination!r}",
    )


def unbz_path(source: Path, *, folder: Path | None, name: str | None, path: Path | None, inplace: bool, orig: bool, verbose: bool) -> Path:
    source_resolved = source.expanduser().resolve()
    destination = _resolve_output_path(source_resolved, folder=folder, name=name, path=path, default_name=_default_unbz_name(source_resolved))
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(bz2.decompress(source_resolved.read_bytes()))
    return _finalize_result(
        source=source_resolved,
        result=destination,
        orig=orig,
        inplace=inplace,
        verbose=verbose,
        message=f"UNBZED {source_resolved!r} ==> {destination!r}",
    )


def decompress_path(source: Path, *, folder: Path | None, name: str | None, path: Path | None, inplace: bool, orig: bool, verbose: bool) -> Path:
    source_resolved = source.expanduser().resolve()
    source_name = source_resolved.name
    if source_name.endswith(".tar.gz") or source_name.endswith(".tgz"):
        tar_path = ungz_path(source_resolved, folder=None, name=f"tmp_{randstr()}.tar", path=None, inplace=inplace, orig=False, verbose=verbose)
        return untar_path(tar_path, folder=folder, name=name, path=path, inplace=True, orig=orig, verbose=verbose)
    if source_name.endswith(".tar"):
        return untar_path(source_resolved, folder=folder, name=name, path=path, inplace=inplace, orig=orig, verbose=verbose)
    if source_name.endswith(".gz"):
        return ungz_path(source_resolved, folder=folder, name=name, path=path, inplace=inplace, orig=orig, verbose=verbose)
    if source_name.endswith(".tar.bz") or source_name.endswith(".tbz") or source_name.endswith(".tar.bz2"):
        tar_path = unbz_path(source_resolved, folder=None, name=f"tmp_{randstr()}.tar", path=None, inplace=inplace, orig=False, verbose=verbose)
        return untar_path(tar_path, folder=folder, name=name, path=path, inplace=True, orig=orig, verbose=verbose)
    if source_name.endswith(".tar.xz"):
        tar_path = unxz_path(source_resolved, folder=None, name=f"tmp_{randstr()}.tar", path=None, inplace=inplace, orig=False, verbose=verbose)
        return untar_path(tar_path, folder=folder, name=name, path=path, inplace=True, orig=orig, verbose=verbose)
    if source_name.endswith(".zip"):
        return unzip_path(
            source_resolved,
            folder=folder,
            path=path,
            name=name,
            verbose=verbose,
            content=False,
            inplace=inplace,
            overwrite=False,
            orig=orig,
            pwd=None,
            tmp=False,
            pattern=None,
            merge=False,
        )
    if source_name.endswith(".7z"):
        destination = _resolve_output_path(source_resolved, folder=folder, name=name, path=path, default_name=_strip_suffix(source_name, ".7z"))
        destination.mkdir(parents=True, exist_ok=True)
        _extract_7z_archive(source_resolved, destination)
        return _finalize_result(
            source=source_resolved,
            result=destination,
            orig=orig,
            inplace=inplace,
            verbose=verbose,
            message=f"DECOMPRESSED {source_resolved!r} ==> {destination!r}",
        )
    raise ValueError(f"Cannot decompress file with unknown extension: {source_resolved}")


__all__ = [
    "DECOMPRESS_SUPPORTED_FORMATS",
    "FileMode",
    "decompress_path",
    "unbz_path",
    "ungz_path",
    "untar_path",
    "unxz_path",
    "unzip_path",
    "zip_path",
]
