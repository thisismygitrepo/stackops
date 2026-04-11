from pathlib import Path
import platform

from machineconfig.utils import rclone as rclone_utils


def _absolute_path(path: Path) -> Path:
    return path.expanduser().absolute()


def _sanitize_remote_path(path: Path) -> str:
    as_posix = path.as_posix()
    if as_posix.startswith("/"):
        return as_posix[1:]
    return as_posix


def get_remote_path(
    *,
    local_path: Path,
    root: str | None,
    os_specific: bool,
    rel2home: bool,
    strict: bool,
) -> Path:
    local_path_resolved = _absolute_path(local_path)
    remote_path_source = local_path_resolved
    if rel2home:
        try:
            remote_path_source = local_path_resolved.relative_to(Path.home())
        except ValueError:
            if strict:
                raise
    remote_prefix = platform.system().lower() if os_specific else "generic_os"
    remote_suffix = _sanitize_remote_path(remote_path_source)
    if root is None:
        return Path(f"{remote_prefix}/{remote_suffix}")
    return Path(f"{root}/{remote_prefix}/{remote_suffix}")


def to_cloud(
    *,
    local_path: Path,
    cloud: str,
    remote_path: Path,
    share: bool,
    verbose: bool,
    transfers: int,
) -> str | None:
    local_path_resolved = _absolute_path(local_path)
    if verbose:
        print(f"⬆️ UPLOADING {local_path_resolved!r} TO {cloud}:{remote_path.as_posix()}")
    rclone_utils.copyto(
        in_path=local_path_resolved.as_posix(),
        out_path=f"{cloud}:{remote_path.as_posix()}",
        transfers=transfers,
        show_command=verbose,
        show_progress=verbose,
    )
    if verbose:
        print(f"{'⬆️' * 5} UPLOAD COMPLETED.")
    if not share:
        return None
    if verbose:
        print("🔗 SHARING FILE")
    return rclone_utils.link(target=f"{cloud}:{remote_path.as_posix()}", show_command=verbose)


def from_cloud(
    *,
    local_path: Path,
    cloud: str,
    remote_path: Path,
    transfers: int,
    verbose: bool,
) -> Path:
    local_path_resolved = _absolute_path(local_path)
    local_path_resolved.parent.mkdir(parents=True, exist_ok=True)
    rclone_utils.copyto(
        in_path=f"{cloud}:{remote_path.as_posix()}",
        out_path=local_path_resolved.as_posix(),
        transfers=transfers,
        show_command=verbose,
        show_progress=verbose,
    )
    return local_path_resolved


def sync_to_cloud(
    *,
    local_path: Path,
    cloud: str,
    remote_path: Path,
    sync_up: bool,
    sync_down: bool,
    transfers: int,
    delete: bool,
    verbose: bool,
) -> Path:
    local_path_resolved = _absolute_path(local_path)
    local_path_resolved.parent.mkdir(parents=True, exist_ok=True)
    remote_target = f"{cloud}:{remote_path.as_posix()}"
    local_target = local_path_resolved.as_posix()
    if sync_up:
        source = local_target
        target = remote_target
    else:
        source = remote_target
        target = local_target

    if not sync_down and not sync_up:
        if verbose:
            print(f"SYNCING 🔄️ {source} {'<>' * 7} {target}")
        rclone_utils.bisync(
            source=source,
            target=target,
            transfers=transfers,
            delete_during=delete,
            show_command=verbose,
            show_progress=verbose,
        )
        return local_path_resolved

    if verbose:
        print(f"SYNCING 🔄️ {source} {'>' * 15} {target}")
    rclone_utils.sync(
        source=source,
        target=target,
        transfers=transfers,
        delete_during=delete,
        show_command=verbose,
        show_progress=verbose,
    )
    return local_path_resolved
