from collections import Counter
from dataclasses import dataclass
import json
from pathlib import Path
import re
import shlex
import subprocess
from typing import cast


SSH_HOST_PATTERN = re.compile(r"^[A-Za-z0-9_.@:-]+$")
SYSTEMD_SERVICE_PATTERN = re.compile(r"^[A-Za-z0-9@_.-]+$")


@dataclass(frozen=True)
class TunnelHealth:
    connector_count: int
    edge_session_count: int
    edge_sessions_per_connector: tuple[int, ...]
    versions: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class ConnectorHostStatus:
    host: str
    service_active: bool
    version: str
    config_valid: bool
    route_coverage: tuple[tuple[str, bool], ...]


def validate_ssh_host(host: str) -> None:
    if SSH_HOST_PATTERN.fullmatch(host) is None:
        raise ValueError(f"Invalid SSH host {host!r}.")


def validate_service_name(service_name: str) -> None:
    if SYSTEMD_SERVICE_PATTERN.fullmatch(service_name) is None:
        raise ValueError(f"Invalid systemd service name {service_name!r}.")


def _local_argument(argument: str) -> str:
    if argument.startswith("~/"):
        return str(Path(argument).expanduser())
    return argument


def _remote_argument(argument: str) -> str:
    if argument.startswith("~/"):
        return f'"$HOME"/{shlex.quote(argument[2:])}'
    return shlex.quote(argument)


def run_host_command(
    command: tuple[str, ...], host: str | None, capture_output: bool, interactive: bool, timeout_seconds: int | None
) -> subprocess.CompletedProcess[str]:
    if host is None:
        local_command = [_local_argument(argument) for argument in command]
        return subprocess.run(local_command, capture_output=capture_output, text=True, check=False, timeout=timeout_seconds)

    validate_ssh_host(host)
    remote_command = " ".join(_remote_argument(argument) for argument in command)
    ssh_command = ["ssh"]
    if interactive:
        ssh_command.append("-tt")
    else:
        ssh_command.extend(("-o", "BatchMode=yes"))
    ssh_command.extend((host, remote_command))
    return subprocess.run(ssh_command, capture_output=capture_output, text=True, check=False, timeout=timeout_seconds)


def require_success(result: subprocess.CompletedProcess[str], description: str) -> str:
    if result.returncode == 0:
        return result.stdout
    detail = result.stderr.strip() or result.stdout.strip() or f"exit status {result.returncode}"
    raise RuntimeError(f"{description} failed: {detail}")


def read_host_file(host: str | None, path: str) -> str:
    result = run_host_command(("cat", "--", path), host=host, capture_output=True, interactive=False, timeout_seconds=30)
    return require_success(result, f"Reading {path}")


def parse_tunnel_health(raw_json: str) -> TunnelHealth:
    loaded: object = json.loads(raw_json)
    if not isinstance(loaded, dict):
        raise ValueError("Tunnel information must be a JSON object.")
    root = cast(dict[str, object], loaded)
    raw_connectors = root.get("conns")
    if not isinstance(raw_connectors, list):
        raise ValueError("Tunnel information has no connector list.")

    versions: Counter[str] = Counter()
    edge_session_counts: list[int] = []
    for index, raw_connector in enumerate(cast(list[object], raw_connectors)):
        if not isinstance(raw_connector, dict):
            raise ValueError(f"Connector {index} must be a JSON object.")
        connector = cast(dict[str, object], raw_connector)
        version = connector.get("version")
        edge_sessions = connector.get("conns")
        if not isinstance(version, str) or not isinstance(edge_sessions, list):
            raise ValueError(f"Connector {index} has invalid version or edge sessions.")
        versions[version] += 1
        edge_session_counts.append(len(edge_sessions))

    return TunnelHealth(
        connector_count=len(edge_session_counts),
        edge_session_count=sum(edge_session_counts),
        edge_sessions_per_connector=tuple(sorted(edge_session_counts)),
        versions=tuple(sorted(versions.items())),
    )


def get_tunnel_health(tunnel_name: str, cloudflared_binary: str) -> TunnelHealth:
    result = run_host_command(
        (cloudflared_binary, "tunnel", "info", "--output", "json", tunnel_name), host=None, capture_output=True, interactive=False, timeout_seconds=30
    )
    return parse_tunnel_health(require_success(result, f"Inspecting tunnel {tunnel_name}"))


def inspect_connector_host(
    host: str | None, hostnames: tuple[str, ...], cloudflared_binary: str, config_path: str, service_name: str
) -> ConnectorHostStatus:
    validate_service_name(service_name)
    label = host or "local"
    active_result = run_host_command(
        ("systemctl", "is-active", "--quiet", service_name), host=host, capture_output=True, interactive=False, timeout_seconds=15
    )
    version_result = run_host_command((cloudflared_binary, "--version"), host=host, capture_output=True, interactive=False, timeout_seconds=15)
    version_output = require_success(version_result, f"Reading cloudflared version on {label}")
    version_match = re.search(r"cloudflared version ([^ ]+)", version_output)
    if version_match is None:
        raise ValueError(f"Could not parse cloudflared version on {label}.")

    validate_result = run_host_command(
        (cloudflared_binary, "--config", config_path, "tunnel", "ingress", "validate"),
        host=host,
        capture_output=True,
        interactive=False,
        timeout_seconds=15,
    )
    route_coverage: list[tuple[str, bool]] = []
    for hostname in hostnames:
        rule_result = run_host_command(
            (cloudflared_binary, "--config", config_path, "tunnel", "ingress", "rule", f"https://{hostname}/"),
            host=host,
            capture_output=True,
            interactive=False,
            timeout_seconds=15,
        )
        route_coverage.append((hostname, rule_result.returncode == 0 and f"hostname: {hostname}" in rule_result.stdout))

    return ConnectorHostStatus(
        host=label,
        service_active=active_result.returncode == 0,
        version=version_match.group(1),
        config_valid=validate_result.returncode == 0,
        route_coverage=tuple(route_coverage),
    )
