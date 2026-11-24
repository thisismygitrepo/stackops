import getpass
import platform
import re
import shutil
from pathlib import Path
from typing import TypedDict, cast

import psutil
import yaml

from stackops.scripts.python.helpers.helpers_webui.network_constants import (
    CLOUDFLARED_BACKGROUND_UNIT,
    CLOUDFLARED_COMMAND,
    CLOUDFLARED_CONFIG_NAMES,
    CLOUDFLARED_DEFAULT_BINARY,
    CLOUDFLARED_LOCAL_SECONDS,
    CLOUDFLARED_SERVICE_CONFIG,
    CLOUDFLARED_SERVICE_NAME,
    CLOUDFLARED_USER_FOLDER,
)
from stackops.scripts.python.helpers.helpers_webui.network_system import read_tool

VERSION_PATTERN = re.compile(r"cloudflared version (\S+)")
TUNNEL_ID_PATTERN = re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
PROCESS_NAMES = frozenset({"cloudflared", "cloudflared.exe"})


# One line of a tunnel's routing table: requests for `hostname` go to `service` on this machine. The last line has no hostname and takes
# whatever matched nothing else.
class TunnelRoute(TypedDict):
    hostname: str
    path: str
    service: str


class TunnelConfig(TypedDict):
    path: str
    exists: bool
    tunnel: str
    routes: list[TunnelRoute]
    problem: str


class RunningTunnel(TypedDict):
    pid: int
    started: float
    tunnel: str


# What this machine can say about Cloudflare tunnels without asking Cloudflare. `config` is the file a tunnel started by hand reads and
# `service_config` the one the installed service reads. `background_blocker` is why a tunnel cannot be started as a background service here.
class TunnelsLocal(TypedDict):
    system: str
    installed: bool
    binary: str
    version: str
    signed_in: bool
    config: TunnelConfig
    service_config: TunnelConfig
    credentials: list[str]
    service_known: bool
    service_active: bool
    background_active: bool
    background_blocker: str
    running: list[RunningTunnel]


def read_config(path: Path) -> TunnelConfig:
    config: TunnelConfig = {"path": str(path), "exists": False, "tunnel": "", "routes": [], "problem": ""}
    try:
        loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return config
    except PermissionError:
        return {**config, "exists": True, "problem": "Only an administrator can read this file."}
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as error:
        return {**config, "exists": True, "problem": f"""This file cannot be read as a cloudflared configuration: {error}"""}
    fields = cast(dict[str, object], loaded) if isinstance(loaded, dict) else {}
    listed = fields.get("ingress")
    routes: list[TunnelRoute] = []
    for item in cast(list[object], listed) if isinstance(listed, list) else []:
        rule = cast(dict[str, object], item) if isinstance(item, dict) else {}
        service = rule.get("service")
        if isinstance(service, str):
            routes.append({"hostname": str(rule.get("hostname") or ""), "path": str(rule.get("path") or ""), "service": service})
    tunnel = fields.get("tunnel")
    return {**config, "exists": True, "tunnel": tunnel if isinstance(tunnel, str) else "", "routes": routes}


def find_binary() -> str:
    default = Path(CLOUDFLARED_DEFAULT_BINARY).expanduser()
    return shutil.which(CLOUDFLARED_COMMAND) or (str(default) if default.is_file() else "")


def read_running() -> list[RunningTunnel]:
    running: list[RunningTunnel] = []
    for process in psutil.process_iter(["name"]):
        if process.info["name"] not in PROCESS_NAMES:
            continue
        try:
            arguments = process.cmdline()
            started = process.create_time()
        except psutil.Error:
            continue
        if "run" not in arguments or "tunnel" not in arguments[: arguments.index("run")]:
            continue
        # The name follows `run` when one was given; without it the tunnel is the one the configuration file names.
        after = [argument for argument in arguments[arguments.index("run") + 1 :] if not argument.startswith("-")]
        running.append({"pid": process.pid, "started": started, "tunnel": after[-1] if after else ""})
    return running


# Why `run-tunnel --background` cannot work here, in the order it would fail. The command starts a systemd unit as root, from the
# cloudflared and the configuration under /home/<user>, and nothing else (`cli_cloudflare.run_tunnel`).
def background_blocker(system: str) -> str:
    if system != "Linux" or shutil.which("systemctl") is None or not Path("/run/systemd/system").is_dir():
        return "A background tunnel runs as a systemd service, which only Linux machines with systemd have."
    home = Path("/home").joinpath(getpass.getuser())
    if not home.joinpath(".local", "bin", CLOUDFLARED_COMMAND).is_file():
        return f"""The background service starts {home}/.local/bin/cloudflared, and there is no cloudflared there."""
    if not home.joinpath(CLOUDFLARED_USER_FOLDER, CLOUDFLARED_CONFIG_NAMES[0]).is_file():
        return f"""The background service reads {home}/{CLOUDFLARED_USER_FOLDER}/{CLOUDFLARED_CONFIG_NAMES[0]}, and that file does not exist."""
    return ""


def read_tunnels_local() -> TunnelsLocal:
    system = platform.system()
    folder = Path.home().joinpath(CLOUDFLARED_USER_FOLDER)
    binary = find_binary()
    version = VERSION_PATTERN.search(read_tool(command=[binary, "--version"], seconds=CLOUDFLARED_LOCAL_SECONDS) or "") if binary != "" else None
    config_path = next((folder.joinpath(name) for name in CLOUDFLARED_CONFIG_NAMES if folder.joinpath(name).is_file()), folder.joinpath(CLOUDFLARED_CONFIG_NAMES[0]))
    has_systemd = system == "Linux" and shutil.which("systemctl") is not None
    # `systemctl is-active` answers through its exit code, which `read_tool` turns into text or None.
    active = {unit: has_systemd and read_tool(command=["systemctl", "is-active", "--quiet", unit], seconds=CLOUDFLARED_LOCAL_SECONDS) is not None for unit in (CLOUDFLARED_SERVICE_NAME, CLOUDFLARED_BACKGROUND_UNIT)}
    return {
        "system": "macOS" if system == "Darwin" else system,
        "installed": binary != "",
        "binary": binary,
        "version": version.group(1) if version is not None else "",
        "signed_in": folder.joinpath("cert.pem").is_file(),
        "config": read_config(path=config_path),
        "service_config": read_config(path=Path(CLOUDFLARED_SERVICE_CONFIG)),
        # A tunnel's credentials file is named after its ID. Only the names are read, never what is in the files.
        "credentials": sorted(path.stem for path in folder.glob("*.json") if TUNNEL_ID_PATTERN.fullmatch(path.stem) is not None),
        "service_known": has_systemd,
        "service_active": active[CLOUDFLARED_SERVICE_NAME],
        "background_active": active[CLOUDFLARED_BACKGROUND_UNIT],
        "background_blocker": background_blocker(system=system),
        "running": read_running(),
    }
