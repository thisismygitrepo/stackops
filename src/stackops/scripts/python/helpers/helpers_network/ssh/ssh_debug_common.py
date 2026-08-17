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
class SSHDConfigurationAssessment:
    settings: SSHDSettings | None
    ports: tuple[int, ...] | None
    checks: tuple[SSHDebugCheck, SSHDebugCheck]


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
    host_name: str,
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
        return SSHDConfigurationAssessment(settings=None, ports=None, checks=(unknown_config, unknown_pubkey))
    if any("," in value or "\n" in value for value in (user_name, host_name)):
        invalid_context = SSHDebugCheck(
            identifier=unknown_config.identifier,
            group=unknown_config.group,
            label=unknown_config.label,
            status="unknown",
            message="Current user or host cannot be represented safely in an sshd -C context",
            command_suggestions=(),
            manual_advice=unknown_config.manual_advice,
        )
        return SSHDConfigurationAssessment(settings=None, ports=None, checks=(invalid_context, unknown_pubkey))

    argv = [str(sshd_path), "-T"]
    if config_path is not None:
        argv.extend(("-f", str(config_path)))
    argv.extend(("-C", f"user={user_name},host={host_name},addr=127.0.0.1"))
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
        return SSHDConfigurationAssessment(settings=None, ports=None, checks=(failed_config, unknown_pubkey))

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
        return SSHDConfigurationAssessment(settings=None, ports=None, checks=(malformed_config, unknown_pubkey))

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
            return SSHDConfigurationAssessment(settings=settings, ports=None, checks=(invalid_port, unknown_pubkey))
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
        return SSHDConfigurationAssessment(settings=settings, ports=None, checks=(missing_port, unknown_pubkey))

    unique_ports = tuple(dict.fromkeys(ports))
    config_check = SSHDebugCheck(
        identifier=unknown_config.identifier,
        group=unknown_config.group,
        label=unknown_config.label,
        status="ok",
        message=(
            f"sshd -T verified user={user_name}, host={host_name}, addr=127.0.0.1 "
            f"for TCP port(s) {', '.join(map(str, unique_ports))}"
        ),
        command_suggestions=(),
        manual_advice=(),
    )
    pubkey_values = settings.values.get("pubkeyauthentication", ())
    if pubkey_values == ("yes",):
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
    return SSHDConfigurationAssessment(settings=settings, ports=unique_ports, checks=(config_check, pubkey_check))
