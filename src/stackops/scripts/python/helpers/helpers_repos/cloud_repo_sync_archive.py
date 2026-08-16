from pathlib import Path


def _cleanup_temp_paths(paths: tuple[Path, ...]) -> None:
    from stackops.utils.path_core import delete_path

    for temp_path in paths:
        delete_path(temp_path, verbose=False)


def get_repo_remote_archive_path(repo_root: Path) -> Path:
    from stackops.utils.cloud import rclone_wrapper

    base_remote_path = rclone_wrapper.get_remote_path(local_path=repo_root, root="myhome", os_specific=False, rel2home=True, strict=True)
    return Path(f"{base_remote_path.as_posix()}.zip.gpg")


def upload_repo_archive(repo_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> None:
    import stackops.utils.files.compression as path_compression
    from stackops.utils.cloud import rclone_wrapper
    from stackops.utils.io import encrypt_file_asymmetric, encrypt_file_symmetric

    archive_path = path_compression.zip_path(
        repo_root, path=None, folder=None, name=None, arcname=None, inplace=False, verbose=True, content=False, orig=False, mode="w"
    )
    if pwd is None:
        encrypted_archive_path = encrypt_file_asymmetric(file_path=archive_path)
    else:
        encrypted_archive_path = encrypt_file_symmetric(file_path=archive_path, pwd=pwd)
    try:
        rclone_wrapper.to_cloud(
            local_path=encrypted_archive_path, cloud=cloud, remote_path=remote_path, share=False, share_options=None, verbose=True, transfers=10
        )
    finally:
        _cleanup_temp_paths(paths=(archive_path, encrypted_archive_path))


def download_repo_archive(repo_remote_root: Path, cloud: str, remote_path: Path, pwd: str | None) -> Path:
    import stackops.utils.files.compression as path_compression
    from stackops.utils.cloud import rclone_wrapper
    from stackops.utils.io import decrypt_file_asymmetric, decrypt_file_symmetric
    from stackops.utils.path_core import delete_path

    encrypted_archive_path = Path(f"{repo_remote_root}.zip.gpg")
    rclone_wrapper.from_cloud(local_path=encrypted_archive_path, cloud=cloud, remote_path=remote_path, transfers=10, verbose=True)
    if pwd is None:
        archive_path = decrypt_file_asymmetric(file_path=encrypted_archive_path)
    else:
        archive_path = decrypt_file_symmetric(file_path=encrypted_archive_path, pwd=pwd)
    delete_path(encrypted_archive_path, verbose=False)
    return path_compression.unzip_path(
        archive_path,
        folder=None,
        path=None,
        name=None,
        verbose=True,
        content=True,
        inplace=True,
        overwrite=True,
        orig=False,
        pwd=None,
        tmp=False,
        pattern=None,
        merge=False,
    )
