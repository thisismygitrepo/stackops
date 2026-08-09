import json
import os
import tempfile
from pathlib import Path
from stat import S_IMODE

from stackops.secrets.loader import load_secrets_file
from stackops.secrets.models import SecretsFile

PRIVATE_SECRETS_FILE_MODE = 0o600
PRIVATE_SECRETS_DIRECTORY_MODE = 0o700


def _write_temporary_secrets_file(secrets_path: Path, secrets_file: SecretsFile, mode: int) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{secrets_path.name}.", dir=secrets_path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.chmod(temporary_path, mode)
        stream = os.fdopen(descriptor, "w", encoding="utf-8")
        descriptor = -1
        with stream:
            json.dump(secrets_file, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        load_secrets_file(temporary_path)
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)
        raise
    return temporary_path


def create_secrets_file(secrets_path: Path, secrets_file: SecretsFile) -> None:
    secrets_path.parent.mkdir(mode=PRIVATE_SECRETS_DIRECTORY_MODE, parents=True, exist_ok=True)
    temporary_path = _write_temporary_secrets_file(
        secrets_path=secrets_path,
        secrets_file=secrets_file,
        mode=PRIVATE_SECRETS_FILE_MODE,
    )
    try:
        os.link(temporary_path, secrets_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def replace_secrets_file(secrets_path: Path, secrets_file: SecretsFile) -> None:
    temporary_path = _write_temporary_secrets_file(
        secrets_path=secrets_path,
        secrets_file=secrets_file,
        mode=S_IMODE(secrets_path.stat().st_mode),
    )
    try:
        os.replace(temporary_path, secrets_path)
    finally:
        temporary_path.unlink(missing_ok=True)
