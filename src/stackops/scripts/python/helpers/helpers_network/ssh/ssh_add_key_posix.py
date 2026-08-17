from collections.abc import Sequence
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_public_keys import PublicKeyRecord, update_authorized_keys


def add_ssh_keys_posix(records: Sequence[PublicKeyRecord]) -> tuple[Path, int]:
    ssh_directory = Path.home().joinpath(".ssh")
    authorized_keys = ssh_directory.joinpath("authorized_keys")
    ssh_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    ssh_directory.chmod(0o700)
    authorized_keys.touch(exist_ok=True, mode=0o600)
    authorized_keys.chmod(0o600)
    added_count = update_authorized_keys(path=authorized_keys, records=records)
    authorized_keys.chmod(0o600)
    return authorized_keys, added_count
