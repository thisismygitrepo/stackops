from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import shlex

from stackops.utils.ssh_utils.open_ssh_config import SSHConfigLookup, select_existing_identity_file
from stackops.utils.ssh_utils.open_ssh_command import parse_open_ssh_destination


@dataclass(frozen=True, slots=True)
class SSHConnectionTarget:
    host: str | None
    hostname: str
    username: str
    port: int
    ssh_key_path: str | None
    proxy_command: str | None


def resolve_ssh_connection_target(
    host: str | None,
    username: str | None,
    hostname: str | None,
    ssh_key_path: str | None,
    port: int,
    local_username: str,
    ssh_config_lookup: SSHConfigLookup,
) -> SSHConnectionTarget:
    validated_default_port = _validated_port(port=port, source="port argument")
    if host is None:
        if username is None or not username or hostname is None or not hostname:
            raise ValueError("Either host or both username and hostname must be provided.")
        return SSHConnectionTarget(
            host=None, hostname=hostname, username=username, port=validated_default_port, ssh_key_path=ssh_key_path, proxy_command=None
        )

    parsed_host = parse_open_ssh_destination(destination=host)
    requested_username = parsed_host.username or username
    config_options = ssh_config_lookup(parsed_host.hostname, requested_username, parsed_host.port)
    configured_hostname = _optional_config_text(config_options=config_options, key="hostname")
    configured_username = _optional_config_text(config_options=config_options, key="user")
    configured_port = _optional_config_port(config_options=config_options)
    configured_identity_file = select_existing_identity_file(config_options=config_options)

    resolved_port = parsed_host.port if parsed_host.port is not None else configured_port
    if resolved_port is None:
        resolved_port = validated_default_port
    resolved_hostname = configured_hostname or parsed_host.hostname
    resolved_username = parsed_host.username or username or configured_username or local_username
    proxy_command = _resolve_proxy_command(
        config_options=config_options,
        requested_hostname=parsed_host.hostname,
        resolved_hostname=resolved_hostname,
        resolved_username=resolved_username,
        resolved_port=resolved_port,
    )

    return SSHConnectionTarget(
        host=host,
        hostname=resolved_hostname,
        username=resolved_username,
        port=resolved_port,
        ssh_key_path=ssh_key_path if ssh_key_path is not None else configured_identity_file,
        proxy_command=proxy_command,
    )


def _optional_config_text(config_options: Mapping[str, object], key: str) -> str | None:
    value = config_options.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(f"SSH config option {key!r} must be text, received {type(value).__name__}.")
    return value


def _optional_config_port(config_options: Mapping[str, object]) -> int | None:
    value = config_options.get("port")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise TypeError(f"SSH config option 'port' must be text or an integer, received {type(value).__name__}.")
    return _parse_port(port_text=str(value), source="SSH config option 'port'")


def _resolve_proxy_command(
    config_options: Mapping[str, object], requested_hostname: str, resolved_hostname: str, resolved_username: str, resolved_port: int
) -> str | None:
    proxy_command = _optional_config_text(config_options=config_options, key="proxycommand")
    proxy_jump = _optional_config_text(config_options=config_options, key="proxyjump")
    if proxy_command is not None and proxy_jump is not None:
        raise ValueError("OpenSSH returned both ProxyCommand and ProxyJump for one destination.")
    if proxy_command is not None and proxy_command.casefold() != "none":
        return _expand_proxy_tokens(
            value=proxy_command,
            requested_hostname=requested_hostname,
            resolved_hostname=resolved_hostname,
            resolved_username=resolved_username,
            resolved_port=resolved_port,
        )
    if proxy_jump is None or proxy_jump.casefold() == "none":
        return None

    expanded_proxy_jump = _expand_proxy_tokens(
        value=proxy_jump,
        requested_hostname=requested_hostname,
        resolved_hostname=resolved_hostname,
        resolved_username=resolved_username,
        resolved_port=resolved_port,
    )
    jump_hosts = expanded_proxy_jump.split(",")
    if any(not jump_host for jump_host in jump_hosts):
        raise ValueError(f"Invalid ProxyJump value: {proxy_jump!r}.")
    final_jump = parse_open_ssh_destination(destination=jump_hosts[-1])
    command = ["ssh", "-T"]
    if len(jump_hosts) > 1:
        command.extend(["-J", ",".join(jump_hosts[:-1])])
    if final_jump.username is not None:
        command.extend(["-l", final_jump.username])
    if final_jump.port is not None:
        command.extend(["-p", str(final_jump.port)])
    destination = f"[{resolved_hostname}]:{resolved_port}" if ":" in resolved_hostname else f"{resolved_hostname}:{resolved_port}"
    command.extend(["-W", destination, "--", final_jump.hostname])
    return shlex.join(command)


def _expand_proxy_tokens(value: str, requested_hostname: str, resolved_hostname: str, resolved_username: str, resolved_port: int) -> str:
    replacements = {"%": "%", "h": resolved_hostname, "n": requested_hostname, "p": str(resolved_port), "r": resolved_username}
    expanded_parts: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "%":
            expanded_parts.append(character)
            index += 1
            continue
        if index + 1 == len(value):
            raise ValueError(f"Incomplete token in SSH proxy value: {value!r}.")
        token = value[index + 1]
        replacement = replacements.get(token)
        if replacement is None:
            raise ValueError(f"Unsupported %{token} token in SSH proxy value: {value!r}.")
        expanded_parts.append(replacement)
        index += 2
    return "".join(expanded_parts).replace("~", str(Path.home()))


def _parse_port(port_text: str, source: str) -> int:
    try:
        port = int(port_text)
    except ValueError as error:
        raise ValueError(f"Invalid SSH port from {source}: {port_text!r}.") from error
    return _validated_port(port=port, source=source)


def _validated_port(port: int, source: str) -> int:
    if isinstance(port, bool):
        raise TypeError(f"SSH port from {source} must be an integer, received bool.")
    if not 1 <= port <= 65_535:
        raise ValueError(f"SSH port from {source} must be between 1 and 65535, received {port}.")
    return port
