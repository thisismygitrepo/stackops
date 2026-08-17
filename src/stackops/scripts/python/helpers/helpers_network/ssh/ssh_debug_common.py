import ipaddress
import re
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_network.ssh.ssh_debug_models import SSHDebugCheck


COMMAND_TIMEOUT_SECONDS = 15
SETTING_NAME_PATTERN = re.compile(r"[a-z][a-z0-9]*")
type ListenerAddressFamily = Literal["ipv4", "ipv6"]


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
    listener_families: frozenset[ListenerAddressFamily] | None
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
            listener_families=None,
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
            listener_families=None,
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
            listener_families=None,
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
                listener_families=None,
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
            listener_families=None,
            checks=(missing_port, unknown_pubkey),
            connection_context_applied=connection_context is not None and invalid_context_detail is None,
        )

    unique_ports = tuple(dict.fromkeys(ports))
    listener_ports: list[int] = []
    listener_families: set[ListenerAddressFamily] = set()
    listener_family_unknown = False
    for listen_address in settings.values.get("listenaddress", ()):
        endpoint = listen_address.split(maxsplit=1)[0]
        address, separator, port_text = endpoint.rpartition(":")
        if separator == "":
            listener_ports.extend(unique_ports)
            listener_family_unknown = True
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
                listener_families=None,
                checks=(invalid_listener, unknown_pubkey),
                connection_context_applied=connection_context is not None and invalid_context_detail is None,
            )
        listener_ports.append(int(port_text))
        normalized_address = address.removeprefix("[").removesuffix("]").split("%", maxsplit=1)[0]
        try:
            parsed_address = ipaddress.ip_address(normalized_address)
        except ValueError:
            listener_family_unknown = True
        else:
            listener_families.add("ipv4" if parsed_address.version == 4 else "ipv6")
    effective_listener_ports = tuple(dict.fromkeys(listener_ports)) or unique_ports
    effective_listener_families = (
        frozenset(listener_families) if listener_families and not listener_family_unknown else None
    )
    if (
        connection_context is not None
        and invalid_context_detail is None
        and connection_context.local_port not in effective_listener_ports
    ):
        mismatched_config = SSHDebugCheck(
            identifier=unknown_config.identifier,
            group=unknown_config.group,
            label=unknown_config.label,
            status="unknown",
            message=(
                f"Connection local port {connection_context.local_port} is not among effective listener port(s) "
                f"{', '.join(map(str, effective_listener_ports))}"
            ),
            command_suggestions=(),
            manual_advice=("Supply the local address and port of an effective SSH listener.",),
        )
        mismatched_pubkey = SSHDebugCheck(
            identifier=unknown_pubkey.identifier,
            group=unknown_pubkey.group,
            label=unknown_pubkey.label,
            status="unknown",
            message="Match-dependent authentication was not accepted for a non-listening local port",
            command_suggestions=(),
            manual_advice=mismatched_config.manual_advice,
        )
        return SSHDConfigurationAssessment(
            settings=settings,
            ports=effective_listener_ports,
            listener_families=effective_listener_families,
            checks=(mismatched_config, mismatched_pubkey),
            connection_context_applied=False,
        )
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
    else:
        pubkey_check = _assess_connection_authentication(settings=settings, user_name=user_name)
    return SSHDConfigurationAssessment(
        settings=settings,
        ports=effective_listener_ports,
        listener_families=effective_listener_families,
        checks=(config_check, pubkey_check),
        connection_context_applied=connection_context is not None and invalid_context_detail is None,
    )


def _assess_connection_authentication(settings: SSHDSettings, user_name: str) -> SSHDebugCheck:
    base_check = SSHDebugCheck(
        identifier="public_key_authentication",
        group="configuration",
        label="Public-key authentication",
        status="unknown",
        message="Connection-specific public-key authentication is unproved",
        command_suggestions=(),
        manual_advice=(),
    )
    pubkey_values = settings.values.get("pubkeyauthentication", ())
    if pubkey_values == ("no",):
        return replace(
            base_check,
            status="error",
            message="Effective PubkeyAuthentication is exactly no",
            manual_advice=("Change the controlling sshd configuration and verify it with the same connection context.",),
        )
    if pubkey_values != ("yes",):
        return replace(
            base_check,
            status="unknown",
            message=f"Unexpected effective PubkeyAuthentication value(s): {pubkey_values or ('missing',)}",
            manual_advice=("Inspect the connection-specific authentication configuration.",),
        )

    permit_root = settings.values.get("permitrootlogin", ())
    if user_name == "root" and permit_root == ("no",):
        return replace(
            base_check,
            status="error",
            message="The target is root and effective PermitRootLogin is no",
            manual_advice=("Use a permitted target account or deliberately revise PermitRootLogin.",),
        )
    if user_name == "root" and permit_root == ("forced-commands-only",):
        return replace(
            base_check,
            status="unknown",
            message="Root public-key login is restricted to forced commands",
            manual_advice=("Verify that the intended key and connection supply an allowed forced command.",),
        )

    deny_users = tuple(token for value in settings.values.get("denyusers", ()) for token in value.split())
    allow_users = tuple(token for value in settings.values.get("allowusers", ()) for token in value.split())
    complex_user_patterns = tuple(
        pattern
        for pattern in (*deny_users, *allow_users)
        if "@" in pattern or any(character in pattern for character in "*?![]")
    )
    if complex_user_patterns:
        return replace(
            base_check,
            status="unknown",
            message=f"User admission uses patterns requiring OpenSSH pattern evaluation: {complex_user_patterns}",
            manual_advice=("Verify AllowUsers and DenyUsers for the exact target and client host/address.",),
        )
    if user_name in deny_users:
        return replace(
            base_check,
            status="error",
            message=f"Effective DenyUsers explicitly rejects {user_name}",
            manual_advice=("Use an admitted account or revise the controlling DenyUsers directive.",),
        )
    if any(candidate.casefold() == user_name.casefold() for candidate in deny_users):
        return replace(
            base_check,
            status="unknown",
            message=f"DenyUsers differs from target {user_name} only by case, whose account semantics are platform-specific",
            manual_advice=("Verify the exact account spelling used by sshd.",),
        )
    if allow_users and user_name not in allow_users:
        if any(candidate.casefold() == user_name.casefold() for candidate in allow_users):
            status = "unknown"
            message = f"AllowUsers differs from target {user_name} only by case"
        else:
            status = "error"
            message = f"Effective AllowUsers does not admit {user_name}"
        return replace(
            base_check,
            status=status,
            message=message,
            manual_advice=("Verify the exact target account admitted by AllowUsers.",),
        )
    if settings.values.get("allowgroups", ()) or settings.values.get("denygroups", ()):
        return replace(
            base_check,
            status="unknown",
            message="AllowGroups or DenyGroups is configured, but effective target group membership was not proved",
            manual_advice=("Verify target group membership using the platform account directory.",),
        )

    authentication_methods = tuple(
        method_list
        for value in settings.values.get("authenticationmethods", ())
        for method_list in value.split()
    )
    if "any" not in authentication_methods:
        public_key_sequences = [
            tuple(method.partition(":")[0] for method in method_list.split(","))
            for method_list in authentication_methods
            if "publickey" in tuple(method.partition(":")[0] for method in method_list.split(","))
        ]
        if not public_key_sequences:
            return replace(
                base_check,
                status="error",
                message=f"AuthenticationMethods does not permit publickey: {authentication_methods or ('missing',)}",
                manual_advice=("Select an authentication method admitted by the effective connection configuration.",),
            )
        if ("publickey",) not in public_key_sequences:
            return replace(
                base_check,
                status="unknown",
                message=f"Public key is only one step in AuthenticationMethods sequences: {authentication_methods}",
                manual_advice=("Verify every additional authentication step required by the selected sequence.",),
            )
    return replace(
        base_check,
        status="ok",
        message="Target admission and effective authentication settings permit public-key authentication",
        manual_advice=(),
    )
