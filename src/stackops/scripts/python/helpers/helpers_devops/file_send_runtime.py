import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
from typing import Literal, cast

import typer


def send_with_receipts(
    *, path: str | None, text: str | None, code: str | None,
    backend: Literal["wormhole", "w", "croc", "c"], zip_folder: bool,
    qrcode: bool, timeout: float | None, output_json: bool,
) -> None:
    environment = dict(os.environ)
    relay: str | None = None
    if backend in {"croc", "c"}:
        from stackops.utils.network.address import select_lan_ipv4

        address = select_lan_ipv4(prefer_vpn=False)
        if address is None:
            raise typer.BadParameter("Could not determine the LAN IPv4 address for the relay.")
        relay = f"{address}:443"
        code = code or secrets.token_hex(16)
        arguments = ["croc", "--relay", relay, "--yes", "send"]
        if os.name == "nt":
            arguments.extend(["--code", code])
        else:
            environment["CROC_SECRET"] = code
        if zip_folder:
            arguments.append("--zip")
        if qrcode:
            arguments.append("--qrcode")
    else:
        arguments = ["uvx", "--from", "magic-wormhole", "wormhole", "send"]
        if code is not None:
            arguments.extend(["--code", code])
    if text is not None:
        arguments.extend(["--text", text])
    elif path is not None:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            raise typer.BadParameter(f"Transfer path does not exist: {target}")
        arguments.append(str(target))

    with tempfile.NamedTemporaryFile(mode="w+b", delete_on_close=False) as log:
        try:
            process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=environment)
        except OSError as failure:
            typer.echo(f"Unable to start transfer: {failure}", err=True)
            raise typer.Exit(1) from None
        deadline = None if timeout is None else time.monotonic() + timeout
        announced = False
        display_offset = 0
        try:
            while True:
                output = Path(log.name).read_text(encoding="utf-8", errors="replace")
                if len(output) > display_offset:
                    sys.stderr.write(output[display_offset:])
                    sys.stderr.flush()
                    display_offset = len(output)
                if code is None:
                    match = re.search(r"Wormhole code is:\s*([A-Za-z0-9-]+)", output)
                    if match is not None:
                        code = cast(str, match.group(1))
                if code is not None and not announced:
                    if output_json:
                        typer.echo(json.dumps({"status": "waiting", "backend": "croc" if backend in {"croc", "c"} else "wormhole", "code": code, "relay": relay, "pid": process.pid}))
                    else:
                        typer.echo(f"Transfer code: {code}" + (f" (relay {relay})" if relay else ""), err=True)
                    announced = True
                returncode = process.poll()
                if returncode is not None:
                    if output_json:
                        typer.echo(json.dumps({"status": "completed" if returncode == 0 else "failed", "code": code, "returncode": returncode}))
                    if returncode != 0:
                        raise typer.Exit(returncode if returncode > 0 else 128 - returncode)
                    return
                if deadline is not None and time.monotonic() >= deadline:
                    if output_json:
                        typer.echo(json.dumps({"status": "timed_out", "code": code, "pid": process.pid}))
                    typer.echo(f"Transfer exceeded {timeout}s.", err=True)
                    raise typer.Exit(124)
                time.sleep(0.1)
        except KeyboardInterrupt:
            raise typer.Exit(130) from None
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
