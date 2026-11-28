import json
import os
import secrets
import shutil
import string
import subprocess
import sys
import time
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp

import typer

SECRET_ALPHABET = string.ascii_letters + string.digits
SECRET_LENGTH = 32
SENDER_RETRY_GAP_SECONDS = 10.0
NO_SENDER_YET_MARKER = "local discovery failed"


def receive_with_proposed_secrets(*, output_json: bool) -> None:
    from stackops.scripts.python.helpers.helpers_devops.cli_data_encrypt import (
        _decrypt_to_output,  # pyright: ignore[reportPrivateUsage]
        _match_archive_suffix,  # pyright: ignore[reportPrivateUsage]
        _stripped_artifact_name,  # pyright: ignore[reportPrivateUsage]
    )
    from stackops.utils.path_core import tmp

    if shutil.which("croc") is None:
        typer.echo("❌ Error: croc is not installed. Add --install-dep to install it.", err=True)
        raise typer.Exit(code=1)
    if shutil.which("gpg") is None:
        typer.echo("❌ Error: gpg is not installed; it is needed to decrypt what arrives.", err=True)
        raise typer.Exit(code=1)

    code = "".join(secrets.choice(SECRET_ALPHABET) for _ in range(SECRET_LENGTH))
    password = "".join(secrets.choice(SECRET_ALPHABET) for _ in range(SECRET_LENGTH))
    send_command = f"devops network send <path> --code {code} --encryption symmetric --password {password}"
    if output_json:
        typer.echo(json.dumps({"status": "waiting", "code": code, "password": password, "send_command": send_command}))
    else:
        import qrcode

        qr = qrcode.QRCode(error_correction=qrcode.ERROR_CORRECT_L, border=4)
        qr.add_data(send_command)
        qr.make(fit=True)
        drawing = StringIO()
        qr.print_ascii(out=drawing, tty=False, invert=False)
        for row in drawing.getvalue().splitlines():
            typer.echo(f"\x1b[30;107m{row}\x1b[0m")
        typer.echo("📱 Scan it: it holds the send command with the code and password. Run that where the file is, with <path> replaced.", err=True)
    typer.echo("⏳ Waiting for the sender. It can start any time; press Ctrl-C to stop.", err=True)

    staging_root = Path(mkdtemp(prefix=".stackops-receive-", dir=tmp(folder="stackops/data", file=None, root="~/tmp_results")))
    arguments = ["croc", "--yes", "--out", str(staging_root)]
    environment = dict(os.environ)
    if os.name == "nt":
        arguments.append(code)
    else:
        environment["CROC_SECRET"] = code

    reported_problem: str | None = None
    try:
        while True:
            with NamedTemporaryFile(mode="wb", delete_on_close=False) as log, Path(log.name).open(mode="rb") as log_reader:
                process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=environment)  # pylint: disable=consider-using-with  # reaped in the finally block below
                try:
                    transfer_started = False
                    while True:
                        returncode = process.poll()
                        transfer_started = transfer_started or any(staging_root.iterdir())
                        if transfer_started:
                            sys.stderr.buffer.write(log_reader.read())
                            sys.stderr.buffer.flush()
                        if returncode is not None:
                            break
                        time.sleep(0.2)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait()
                attempt_output = Path(log.name).read_text(encoding="utf-8", errors="replace").replace("\r", "\n").strip()
            if transfer_started and returncode == 0:
                break
            if transfer_started:
                typer.echo(f"❌ Error: The transfer broke off before the file was complete (croc exit code {returncode}).", err=True)
                shutil.rmtree(staging_root)
                raise typer.Exit(code=1)
            if returncode == 0:
                typer.echo(attempt_output, err=True)
                typer.echo("❌ Error: croc finished but delivered no file. --propose receives files and folders only.", err=True)
                shutil.rmtree(staging_root)
                raise typer.Exit(code=1)
            problem = attempt_output.splitlines()[-1] if attempt_output != "" else f"croc exited with code {returncode}"
            if NO_SENDER_YET_MARKER not in problem and problem != reported_problem:
                typer.echo(f"⚠️ croc: {problem} (still retrying)", err=True)
                reported_problem = problem
            time.sleep(SENDER_RETRY_GAP_SECONDS)
    except KeyboardInterrupt:
        shutil.rmtree(staging_root)
        raise typer.Exit(code=130) from None

    decrypted_paths: list[str] = []
    for received in sorted(staging_root.iterdir()):
        if not received.is_file() or received.suffix != ".gpg":
            typer.echo(f"❌ Error: The sender did not use --encryption symmetric, so there is nothing to decrypt. Received as sent: {received}", err=True)
            raise typer.Exit(code=1)
        inner_name = received.name.removesuffix(".gpg")
        archive_suffix = _match_archive_suffix(inner_name)
        output_path = Path.cwd() / _stripped_artifact_name(inner_name, archive_suffix=archive_suffix)
        try:
            _decrypt_to_output(source=received, mode="symmetric", pwd=password, archive_suffix=archive_suffix, output_path=output_path, overwrite=False)
        except (OSError, ValueError, RuntimeError) as failure:
            typer.echo(f"❌ Error: {failure}", err=True)
            typer.echo(f"The encrypted file is kept at {received}. Decrypt it elsewhere with: devops data decrypt {received} --output <new path>", err=True)
            raise typer.Exit(code=1) from failure
        decrypted_paths.append(str(output_path))
    shutil.rmtree(staging_root)
    if output_json:
        typer.echo(json.dumps({"status": "completed", "paths": decrypted_paths}))
    else:
        for decrypted_path in decrypted_paths:
            typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Received and decrypted ==> {decrypted_path}")
