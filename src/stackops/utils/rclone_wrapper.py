from pathlib import Path
import platform
from urllib.parse import parse_qs, quote, urlparse

from stackops.utils import rclone as rclone_utils


def _absolute_path(path: Path) -> Path:
    return path.expanduser().absolute()


def _sanitize_remote_path(path: Path) -> str:
    as_posix = path.as_posix()
    if as_posix.startswith("/"):
        return as_posix[1:]
    return as_posix


def google_drive_direct_download_url(*, share_url: str) -> str | None:
    parsed_url = urlparse(share_url)
    if parsed_url.netloc.lower() != "drive.google.com":
        return None

    file_id: str | None = None
    if parsed_url.path == "/open":
        values = parse_qs(parsed_url.query).get("id")
        if values:
            file_id = values[0]
    else:
        path_parts = [part for part in parsed_url.path.split("/") if part]
        if len(path_parts) >= 3 and path_parts[0] == "file" and path_parts[1] == "d":
            file_id = path_parts[2]

    if file_id is None or file_id == "":
        return None
    return f"https://drive.google.com/uc?export=download&id={quote(file_id, safe='')}"


def _print_share_urls(*, share_url: str) -> None:
    print(f"🔗 SHARE URL: {share_url}")
    direct_download_url = google_drive_direct_download_url(share_url=share_url)
    if direct_download_url is not None:
        print(f"⬇️ DIRECT DOWNLOAD URL: {direct_download_url}")


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
    share_options: rclone_utils.ShareLinkOptions | None,
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
    share_url = rclone_utils.link(
        target=f"{cloud}:{remote_path.as_posix()}",
        remote_name=cloud,
        share_options=share_options,
        show_command=verbose,
    )
    if verbose:
        _print_share_urls(share_url=share_url)
    return share_url


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
