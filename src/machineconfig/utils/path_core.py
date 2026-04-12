from __future__ import annotations

from pathlib import Path
import shutil

from machineconfig.utils.accessories import randstr

type PathLike = str | Path
type OptionalPathLike = str | Path | None

__all__ = ["collapseuser", "copy", "delete_path", "move", "resolve", "with_name"]


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


def resolve(path: PathLike, *, strict: bool = False) -> Path:
    path_obj = Path(path)
    try:
        return path_obj.resolve(strict=strict)
    except OSError:
        return path_obj


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
