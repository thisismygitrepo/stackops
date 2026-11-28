import shutil
from pathlib import Path
from tempfile import mkdtemp

import typer

from stackops.utils.cloud.encryption import EncryptionMode


def stage_encrypted_payload(*, path: str, mode: EncryptionMode, pwd: str | None, recipient: str | None) -> Path:
    from stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt import (
        _default_encrypted_output,  # pyright: ignore[reportPrivateUsage]
        _encrypt_to_output,  # pyright: ignore[reportPrivateUsage]
    )
    from stackops.utils.cli_utils.secret_input import read_secret_input
    from stackops.utils.path_core import tmp

    source = Path(path).expanduser().absolute()
    if not source.exists():
        typer.echo(f"❌ Error: Path does not exist: {source}", err=True)
        raise typer.Exit(code=1)
    if mode == "symmetric":
        pwd = read_secret_input(value=pwd, file=None, env=None, prompt="🔑 Enter symmetric GPG encryption password: ")
    staging_root = Path(mkdtemp(prefix=".stackops-send-", dir=tmp(folder="stackops/data", file=None, root="~/tmp_results")))
    encrypted_path = staging_root / _default_encrypted_output(source, compression="zip").name
    try:
        _encrypt_to_output(source=source, mode=mode, pwd=pwd, recipient=recipient, compression="zip", output_path=encrypted_path, overwrite=False)
    except (OSError, ValueError, RuntimeError) as failure:
        shutil.rmtree(staging_root)
        typer.echo(f"❌ Error: {failure}", err=True)
        raise typer.Exit(code=1) from failure
    return encrypted_path
