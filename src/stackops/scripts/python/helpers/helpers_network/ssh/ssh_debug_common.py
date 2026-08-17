import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


COMMAND_TIMEOUT_SECONDS = 15
SETTING_NAME_PATTERN = re.compile(r"[a-z][a-z0-9]*")


@dataclass(frozen=True, slots=True)
class CommandResult:
    returncode: int | None
    stdout: str
    stderr: str
    failure: str | None


@dataclass(frozen=True, slots=True)
class SSHDSettings:
    values: dict[str, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class SSHDConnectionContext:
    client_host_name: str
    client_address: str
    local_address: str
    local_port: int
    routing_domain: str | None


@dataclass(frozen=True, slots=True)
class SSHDConfigurationAssessment:
    settings: SSHDSettings | None
    ports: tuple[int, ...] | None
    checks: tuple[SSHDebugCheck, SSHDebugCheck]
    connection_context_applied: bool


def run_argv(argv: tuple[str, ...]) -> CommandResult:
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        return CommandResult(returncode=None, stdout="", stderr="", failure="executable not found")
    except PermissionError:
        return CommandResult(returncode=None, stdout="", stderr="", failure="permission denied")
    except subprocess.TimeoutExpired:
        return CommandResult(returncode=None, stdout="", stderr="", failure="command timed out")
    except OSError as error:
        return CommandResult(returncode=None, stdout="", stderr="", failure=f"could not start command: {error}")
    return CommandResult(
        returncode=completed.returncode,
        stdout=completed.stdout.strip(),
        stderr=completed.stderr.strip(),
        failure=None,
    )


def parse_sshd_settings(output: str) -> SSHDSettings | None:
    parsed: dict[str, list[str]] = {}
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or SETTING_NAME_PATTERN.fullmatch(parts[0]) is None:
            return None
        parsed.setdefault(parts[0], []).append(parts[1].strip())
    if not parsed:
        return None
    return SSHDSettings(values={key: tuple(values) for key, values in parsed.items()})


def assess_sshd_configuration(
    sshd_path: Path | None,
    config_path: Path | None,
    user_name: str,
    connection_context: SSHDConnectionContext | None,
) -> SSHDConfigurationAssessment:
    unknown_config = SSHDebugCheck(
        identifier="effective_configuration",
        group="configuration",
        label="Effective sshd configuration",
        status="unknown",
        message="sshd -T was not run",
        command_suggestions=(),
        manual_advice=("Inspect the effective configuration with sshd -T without using elevated privileges.",),
    )
    unknown_pubkey = SSHDebugCheck(
        identifier="public_key_authentication",
        group="configuration",
        label="Public-key authentication",
        status="unknown",
        message="Effective PubkeyAuthentication value is unavailable",
        command_suggestions=(),
        manual_advice=("Resolve the effective-configuration probe before relying on key authentication.",),
    )
    if sshd_path is None:
        return SSHDConfigurationAssessment(
            settings=None,
            ports=None,
            checks=(unknown_config, unknown_pubkey),
            connection_context_applied=False,
        )
    argv = [str(sshd_path), "-T"]
    if config_path is not None:
        argv.extend(("-f", str(config_path)))
    invalid_context_detail: str | None = None
    if connection_context is not None:
        context_values = (
            user_name,
            connection_context.client_host_name,
            connection_context.client_address,
            connection_context.local_address,
            connection_context.routing_domain or "",
        )
        if any("," in value or "\n" in value for value in context_values):
            invalid_context_detail = "A connection-context value contains a comma or newline"
        elif not 1 <= connection_context.local_port <= 65535:
            invalid_context_detail = f"Invalid local TCP port {connection_context.local_port}"
        else:
            context_parts = [
                f"user={user_name}",
                f"host={connection_context.client_host_name}",
                f"addr={connection_context.client_address}",
                f"laddr={connection_context.local_address}",
                f"lport={connection_context.local_port}",
            ]
            if connection_context.routing_domain is not None:
                context_parts.append(f"rdomain={connection_context.routing_domain}")
            argv.extend(("-C", ",".join(context_parts)))
    completed = run_argv(tuple(argv))
    if completed.returncode != 0:
        detail = completed.stderr or completed.stdout or completed.failure or "unknown command failure"
        failed_config = SSHDebugCheck(
            identifier=unknown_config.identifier,
            group=unknown_config.group,
            label=unknown_config.label,
            status="unknown",
            message=f"sshd -T failed: {detail}",
            command_suggestions=(),
            manual_advice=unknown_config.manual_advice,
        )
        return SSHDConfigurationAssessment(
            settings=None,
            ports=None,
            checks=(failed_config, unknown_pubkey),
            connection_context_applied=False,
        )

    settings = parse_sshd_settings(completed.stdout)
    if settings is None:
        malformed_config = SSHDebugCheck(
            identifier=unknown_config.identifier,
            group=unknown_config.group,
            label=unknown_config.label,
            status="unknown",
            message="sshd -T returned empty or malformed settings",
            command_suggestions=(),
            manual_advice=unknown_config.manual_advice,
        )
        return SSHDConfigurationAssessment(
            settings=None,
            ports=None,
            checks=(malformed_config, unknown_pubkey),
            connection_context_applied=False,
        )

    port_values = settings.values.get("port", ())
    ports: list[int] = []
    for value in port_values:
        if not value.isdecimal() or not 1 <= int(value) <= 65535:
            invalid_port = SSHDebugCheck(
                identifier=unknown_config.identifier,
                group=unknown_config.group,
                label=unknown_config.label,
                status="unknown",
                message=f"sshd -T returned an invalid Port value: {value}",
                command_suggestions=(),
                manual_advice=unknown_config.manual_advice,
            )
            return SSHDConfigurationAssessment(
                settings=settings,
                ports=None,
                checks=(invalid_port, unknown_pubkey),
                connection_context_applied=connection_context is not None and invalid_context_detail is None,
            )
        ports.append(int(value))
    if not ports:
        missing_port = SSHDebugCheck(
            identifier=unknown_config.identifier,
            group=unknown_config.group,
            label=unknown_config.label,
            status="unknown",
            message="sshd -T did not report an effective Port",
            command_suggestions=(),
            manual_advice=unknown_config.manual_advice,
        )
        return SSHDConfigurationAssessment(
            settings=settings,
            ports=None,
            checks=(missing_port, unknown_pubkey),
            connection_context_applied=connection_context is not None and invalid_context_detail is None,
        )

    unique_ports = tuple(dict.fromkeys(ports))
    listener_ports: list[int] = []
    for listen_address in settings.values.get("listenaddress", ()):
        endpoint = listen_address.split(maxsplit=1)[0]
        _address, separator, port_text = endpoint.rpartition(":")
        if separator == "":
            listener_ports.extend(unique_ports)
            continue
        if not port_text.isdecimal() or not 1 <= int(port_text) <= 65535:
            invalid_listener = SSHDebugCheck(
                identifier=unknown_config.identifier,
                group=unknown_config.group,
                label=unknown_config.label,
                status="unknown",
                message=f"sshd -T returned an unparseable ListenAddress endpoint: {listen_address}",
                command_suggestions=(),
                manual_advice=unknown_config.manual_advice,
            )
            return SSHDConfigurationAssessment(
                settings=settings,
                ports=None,
                checks=(invalid_listener, unknown_pubkey),
                connection_context_applied=connection_context is not None and invalid_context_detail is None,
            )
        listener_ports.append(int(port_text))
    effective_listener_ports = tuple(dict.fromkeys(listener_ports)) or unique_ports
    if connection_context is None or invalid_context_detail is not None:
        context_message = "global configuration"
    else:
        context_message = (
            f"user={user_name}, host={connection_context.client_host_name}, "
            f"addr={connection_context.client_address}, laddr={connection_context.local_address}, "
            f"lport={connection_context.local_port}"
        )
    config_check = SSHDebugCheck(
        identifier=unknown_config.identifier,
        group=unknown_config.group,
        label=unknown_config.label,
        status="ok",
        message=f"sshd -T verified {context_message} for listener TCP port(s) {', '.join(map(str, effective_listener_ports))}",
        command_suggestions=(),
        manual_advice=(),
    )
    pubkey_values = settings.values.get("pubkeyauthentication", ())
    if invalid_context_detail is not None:
        pubkey_check = SSHDebugCheck(
            identifier=unknown_pubkey.identifier,
            group=unknown_pubkey.group,
            label=unknown_pubkey.label,
            status="unknown",
            message=f"Connection-specific configuration was not evaluated: {invalid_context_detail}",
            command_suggestions=(),
            manual_advice=("Supply connection-context values that sshd -C can represent safely.",),
        )
    elif connection_context is None:
        pubkey_check = SSHDebugCheck(
            identifier=unknown_pubkey.identifier,
            group=unknown_pubkey.group,
            label=unknown_pubkey.label,
            status="unknown",
            message="No explicit connection context was supplied, so Match-dependent authentication cannot be verified",
            command_suggestions=(),
            manual_advice=("Supply the client host/address and server local address/port to evaluate sshd Match rules.",),
        )
    elif pubkey_values == ("yes",):
        pubkey_check = SSHDebugCheck(
            identifier=unknown_pubkey.identifier,
            group=unknown_pubkey.group,
            label=unknown_pubkey.label,
            status="ok",
            message="Effective PubkeyAuthentication is exactly yes",
            command_suggestions=(),
            manual_advice=(),
        )
    elif pubkey_values == ("no",):
        pubkey_check = SSHDebugCheck(
            identifier=unknown_pubkey.identifier,
            group=unknown_pubkey.group,
            label=unknown_pubkey.label,
            status="error",
            message="Effective PubkeyAuthentication is exactly no",
            command_suggestions=(),
            manual_advice=("Change the controlling sshd configuration and verify the result again with sshd -T.",),
        )
    else:
        pubkey_check = SSHDebugCheck(
            identifier=unknown_pubkey.identifier,
            group=unknown_pubkey.group,
            label=unknown_pubkey.label,
            status="unknown",
            message=f"Unexpected effective PubkeyAuthentication value(s): {pubkey_values or ('missing',)}",
            command_suggestions=(),
            manual_advice=unknown_pubkey.manual_advice,
        )
    return SSHDConfigurationAssessment(
        settings=settings,
        ports=effective_listener_ports,
        checks=(config_check, pubkey_check),
        connection_context_applied=connection_context is not None and invalid_context_detail is None,
    )
