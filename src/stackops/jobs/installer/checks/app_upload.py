from hashlib import file_digest
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

from stackops.jobs.installer.checks.constants import SECURITY_UPLOAD_ROOT, SECURITY_UPLOAD_TMP_PREFIX, SECURITY_UPLOAD_TRANSFERS
from stackops.utils.cloud.default_remote import read_default_rclone_remote
from stackops.utils.cloud.rclone_wrapper import get_remote_path, to_cloud


def upload_app(path: Path, expected_sha256: str | None) -> str:
    local_path = path.expanduser().absolute()
    mapped_path = get_remote_path(local_path=local_path, root=SECURITY_UPLOAD_ROOT, os_specific=True, rel2home=True, strict=True)
    with TemporaryDirectory(prefix=SECURITY_UPLOAD_TMP_PREFIX) as temporary_directory:
        snapshot_path = Path(temporary_directory) / local_path.name
        copy2(local_path, snapshot_path)
        with snapshot_path.open("rb") as snapshot:
            content_sha256 = file_digest(snapshot, "sha256").hexdigest()
        if expected_sha256 is not None and content_sha256 != expected_sha256:
            raise ValueError(f"""File contents changed since the VirusTotal scan: {local_path}.""")
        remote_path = mapped_path.parent / local_path.stem / content_sha256 / local_path.name
        share_url = to_cloud(
            local_path=snapshot_path,
            cloud=read_default_rclone_remote(),
            remote_path=remote_path,
            overwrite=False,
            share=True,
            share_options=None,
            verbose=False,
            show_progress=False,
            transfers=SECURITY_UPLOAD_TRANSFERS,
        )
        if not share_url:
            raise RuntimeError(f"""No sharing URL returned for {remote_path.as_posix()}.""")
        return share_url
