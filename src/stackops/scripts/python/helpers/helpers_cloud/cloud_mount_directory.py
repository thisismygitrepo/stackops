import errno
import subprocess
from pathlib import Path
from typing import Literal


def prepare_unix_mount_directory(mount_path: Path, system_name: Literal["Linux", "Darwin"]) -> bool:
    recovered = False
    try:
        mount_path.stat()
    except FileNotFoundError:
        pass
    except OSError as error:
        if system_name != "Linux" or error.errno != errno.ENOTCONN:
            raise
        subprocess.run(["fusermount3", "-uz", str(mount_path)], check=True)
        recovered = True

    mount_path.mkdir(parents=True, exist_ok=True)
    mount_path.stat()
    return recovered
