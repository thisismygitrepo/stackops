from pathlib import Path
import platform
import subprocess


def stop_repository_gpg_daemons(repo_root: Path) -> None:
    # Windows GnuPG locks pubring.db.lock against other processes' reads, so
    # tracking the live keyring can break git status/add. POSIX lockfiles do
    # not impose that read restriction.
    if platform.system() != "Windows":
        return

    gpg_home = subprocess.run(
        ["gpgconf", "--list-dirs", "homedir"], check=True, capture_output=True, text=True
    ).stdout.strip()
    gpg_keybox_path = Path(gpg_home).joinpath("public-keys.d", "pubring.db")
    # Follow links from the active GnuPG home, and stop daemons only when their
    # key database resides in the repository being synced.
    if gpg_keybox_path.resolve().is_relative_to(repo_root.expanduser().resolve()):
        subprocess.run(["gpgconf", "--homedir", gpg_home, "--kill", "all"], check=True)
