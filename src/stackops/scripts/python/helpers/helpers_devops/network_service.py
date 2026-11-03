from dataclasses import dataclass
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import sys
import re
from urllib import error, request
from urllib.parse import urlsplit

import typer


def install_service_dependency(name: str) -> None:
    result = subprocess.run(["devops", "software", "install", name], stdin=subprocess.DEVNULL, stdout=sys.stderr, stderr=sys.stderr, check=False)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)


@dataclass(frozen=True)
class ServiceProcess:
    name: str
    process: subprocess.Popen[bytes]
    log_path: Path


def start_service(name: str, arguments: list[str], background: bool, environment: dict[str, str] | None) -> ServiceProcess:
    directory = Path.home() / ".cache" / "stackops" / "network-services"
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f"{name}-", suffix=".log", dir=directory, delete=False) as log:
        process = subprocess.Popen(
            arguments, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
            env=environment, start_new_session=background and os.name != "nt",
            creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if background and os.name == "nt" else 0,
        )
        return ServiceProcess(name=name, process=process, log_path=Path(log.name))


def stop_services(services: list[ServiceProcess]) -> None:
    for service in services:
        if service.process.poll() is None:
            service.process.terminate()
    for service in services:
        try:
            service.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            service.process.kill()
            service.process.wait()


def require_free_port(host: str, port: int) -> None:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as probe:
        try:
            probe.bind((host, port))
        except OSError as failure:
            raise RuntimeError(f"Port {host}:{port} is unavailable: {failure}") from failure


def wait_for_service(service: ServiceProcess, host: str, port: int, timeout: float) -> None:
    probe_host = "127.0.0.1" if host == "0.0.0.0" else "::1" if host == "::" else host
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service.process.poll() is not None:
            raise RuntimeError(f"{service.name} exited with code {service.process.returncode}; see {service.log_path}.")
        try:
            with socket.create_connection((probe_host, port), timeout=min(0.2, timeout)):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError(f"{service.name} did not become ready within {timeout:g}s; see {service.log_path}.")


def wait_for_ngrok(service: ServiceProcess, port: int, timeout: float) -> str:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if service.process.poll() is not None:
            raise RuntimeError(f"ngrok exited with code {service.process.returncode}; see {service.log_path}.")
        try:
            with request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=min(1, timeout)) as response:
                payload = json.load(response)
            tunnels = payload.get("tunnels", []) if isinstance(payload, dict) else []
            for tunnel in tunnels:
                if not isinstance(tunnel, dict):
                    continue
                config = tunnel.get("config")
                address = config.get("addr") if isinstance(config, dict) else None
                public_url = tunnel.get("public_url")
                if isinstance(address, str) and address.rsplit(":", 1)[-1] == str(port) and isinstance(public_url, str):
                    return public_url
        except (error.URLError, OSError, ValueError):
            pass
        time.sleep(0.1)
    raise RuntimeError(f"ngrok did not report the tunnel within {timeout:g}s; see {service.log_path}.")


def run_network_service(
    *, name: str, arguments: list[str], host: str, port: int, url: str,
    over_internet: bool, background: bool, output_json: bool, timeout: float, url_from_log: bool,
) -> None:
    services: list[ServiceProcess] = []
    leave_running = False
    try:
        require_free_port(host, port)
        service = start_service(name, arguments, background, None)
        services.append(service)
        wait_for_service(service, host, port, timeout)
        if url_from_log:
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                text = service.log_path.read_text(encoding="utf-8", errors="replace")
                match = re.search(rf"https?://[^\s]+:{port}/[^\s\x1b]+", text)
                if match is not None:
                    url = match.group(0)
                    break
                if service.process.poll() is not None:
                    raise RuntimeError(f"{name} exited before reporting its URL; see {service.log_path}.")
                time.sleep(0.1)
            else:
                raise RuntimeError(f"{name} did not report its URL; see {service.log_path}.")
        public_url: str | None = None
        if over_internet:
            tunnel = start_service("ngrok", ["ngrok", "http", str(port)], background, None)
            services.append(tunnel)
            public_url = wait_for_ngrok(tunnel, port, timeout)
            public_url = public_url.rstrip("/") + urlsplit(url).path
        receipt = {"status": "ready", "url": url, "public_url": public_url, "background": background, "processes": [{"name": item.name, "pid": item.process.pid, "log_path": str(item.log_path)} for item in services]}
        if output_json:
            typer.echo(json.dumps(receipt))
        else:
            typer.echo(f"Ready: {public_url or url}")
            for item in services:
                typer.echo(f"{item.name}: PID {item.process.pid}, log {item.log_path}")
        if background:
            leave_running = True
            return
        while True:
            for item in services:
                code = item.process.poll()
                if code is not None:
                    if code != 0:
                        raise RuntimeError(f"{item.name} exited with code {code}; see {item.log_path}.")
                    return
            time.sleep(0.2)
    except KeyboardInterrupt:
        raise typer.Exit(130) from None
    except (OSError, RuntimeError) as failure:
        typer.echo(str(failure), err=True)
        raise typer.Exit(1) from None
    finally:
        if not leave_running:
            stop_services(services)
