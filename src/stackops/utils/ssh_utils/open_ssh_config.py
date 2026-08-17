from collections.abc import Callable, Mapping
from pathlib import Path
import shlex
import subprocess


type SSHConfigLookup = Callable[[str, str | None, int | None], Mapping[str, object]]


def lookup_open_ssh_config(hostname: str, username: str | None, port: int | None) -> dict[str, object]:
    command = ["ssh", "-G", "-T"]
    if username is not None:
        command.extend(["-l", username])
    if port is not None:
        command.extend(["-p", str(port)])
    command.extend(["--", hostname])
    completed_process: subprocess.CompletedProcess[str] = subprocess.run(command, check=True, capture_output=True, encoding="utf-8")
    return parse_open_ssh_config(config_text=completed_process.stdout)


def parse_open_ssh_config(config_text: str) -> dict[str, object]:
    config_options: dict[str, object] = {}
    identity_files: list[str] = []
    user_known_hosts_files: list[str] = []
    global_known_hosts_files: list[str] = []
    for line_number, line in enumerate(config_text.splitlines(), start=1):
        key, separator, value = line.partition(" ")
        if not separator or not key or not value:
            raise ValueError(f"Invalid output from 'ssh -G' on line {line_number}: {line!r}.")
        normalized_key = key.casefold()
        match normalized_key:
            case (
                "hostname"
                | "user"
                | "port"
                | "proxycommand"
                | "proxyjump"
                | "identitiesonly"
                | "hostkeyalias"
                | "hashknownhosts"
            ):
                config_options[normalized_key] = value
            case "identityfile":
                identity_files.append(value)
            case "userknownhostsfile":
                user_known_hosts_files.extend(shlex.split(value))
            case "globalknownhostsfile":
                global_known_hosts_files.extend(shlex.split(value))
            case _:
                continue
    if identity_files:
        config_options["identityfile"] = identity_files
    if user_known_hosts_files:
        config_options["userknownhostsfile"] = user_known_hosts_files
    if global_known_hosts_files:
        config_options["globalknownhostsfile"] = global_known_hosts_files
    return config_options


def select_existing_identity_files(config_options: Mapping[str, object]) -> tuple[str, ...]:
    value = config_options.get("identityfile")
    if value is None:
        return ()
    if isinstance(value, str):
        identity_files = [value]
    elif isinstance(value, list):
        identity_files = [identity_file for identity_file in value if isinstance(identity_file, str)]
        if len(identity_files) != len(value):
            raise TypeError("Every SSH config identity file must be text.")
    else:
        raise TypeError(f"SSH config option 'identityfile' must be text or a list, received {type(value).__name__}.")
    existing_identity_files: list[str] = []
    for identity_file in identity_files:
        if identity_file.casefold() == "none":
            continue
        identity_file_path = Path(identity_file).expanduser()
        if identity_file_path.is_file():
            existing_identity_files.append(str(identity_file_path.absolute()))
    return tuple(existing_identity_files)
