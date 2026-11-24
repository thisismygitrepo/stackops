import json
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from importlib.metadata import Distribution, PackageNotFoundError, distribution
from pathlib import Path
from typing import Literal, TypedDict, cast
from urllib.parse import urlsplit
from urllib.request import url2pathname

from stackops.scripts.python.helpers.helpers_webui.machine_update_checkout import without_sign_in
from stackops.scripts.python.helpers.helpers_webui.machine_update_constants import PACKAGE_NAME, UV_TIMEOUT_SECONDS

# What uv writes into the folder of every tool it installs. A folder that holds one is a uv tool.
TOOL_RECEIPT = "uv-receipt.toml"
ENVIRONMENT_MARKER = "pyvenv.cfg"
WEBUI_COMMAND = "webui"

# Where a copy came from: the package index, a folder installed so that edits to it take effect at once, a folder copied in, a git address, or a file.
type InstallSource = Literal["index", "checkout", "folder", "repository", "archive"]


# One installed copy of StackOps. `origin` is the folder or address it was installed from, empty for the package index. `installed_at` is when its
# files were last written, which every install and reinstall does.
class InstallView(TypedDict):
    version: str
    location: str
    source: InstallSource
    origin: str
    python: str
    installed_at: float
    uv_tool: bool


# Where uv keeps its tools, asked once: the answer does not change while the server runs.
@dataclass
class ToolsFolder:
    path: Path | None


def environment_of(site_packages: Path) -> Path | None:
    return next((folder for folder in [*site_packages.parents][:3] if folder.joinpath(ENVIRONMENT_MARKER).is_file()), None)


# The environment this server imports StackOps from. None when it runs from source files with no install record.
def running_environment() -> Path | None:
    try:
        record = distribution(PACKAGE_NAME)
    except PackageNotFoundError:
        return None
    return environment_of(Path(str(record.locate_file(""))))


# The folder of the uv tool the update reinstalls, whether or not this server runs from it. uv itself says where its tools are.
def tool_environment(running: Path | None, known: ToolsFolder) -> Path | None:
    if running is not None and running.joinpath(TOOL_RECEIPT).is_file():
        return running
    if known.path is None:
        uv_path = shutil.which("uv")
        if uv_path is None:
            return None
        try:
            answer = subprocess.run([uv_path, "tool", "dir"], capture_output=True, text=True, check=False, stdin=subprocess.DEVNULL, timeout=UV_TIMEOUT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            return None
        if answer.returncode != 0 or answer.stdout.strip() == "":
            return None
        known.path = Path(answer.stdout.strip())
    folder = known.path.joinpath(PACKAGE_NAME)
    return folder if folder.joinpath(TOOL_RECEIPT).is_file() else None


# The install record names where a copy came from, in the standard form every installer writes. A copy from the package index has no such note.
def read_origin(note: str | None) -> tuple[InstallSource, str]:
    if note is None:
        return ("index", "")
    document = cast(dict[str, object], json.loads(note))
    address = str(document.get("url", ""))
    if "dir_info" in document:
        editable = cast(dict[str, object], document["dir_info"]).get("editable") is True
        return ("checkout" if editable else "folder", url2pathname(urlsplit(address).path))
    return ("repository" if "vcs_info" in document else "archive", without_sign_in(address))


def read_install(environment: Path) -> InstallView | None:
    records = [record for folder in [*environment.glob("lib/python*/site-packages"), *environment.glob("Lib/site-packages")] for record in folder.glob(f"""{PACKAGE_NAME}-*.dist-info""")]
    if len(records) == 0:
        return None
    record = Distribution.at(records[0])
    source, origin = read_origin(record.read_text("direct_url.json"))
    settings = [line.partition("=") for line in environment.joinpath(ENVIRONMENT_MARKER).read_text(encoding="utf-8").splitlines()]
    python = next((value.strip() for key, _, value in settings if key.strip() in ("version_info", "version")), "")
    return {
        "version": record.version,
        "location": str(environment),
        "source": source,
        "origin": origin,
        "python": python,
        "installed_at": records[0].joinpath("METADATA").stat().st_mtime,
        "uv_tool": environment.joinpath(TOOL_RECEIPT).is_file(),
    }


# The command that starts this web UI again the way it was started: the nearest process above this one that was given `webui` as a word. It is
# written with the `stackops` on the PATH, which is the copy the update replaces. Not exhaustive by choice: a server started some other way gets
# the plain command.
def restart_command() -> str:
    import psutil

    for ancestor in psutil.Process().parents():
        try:
            words = ancestor.cmdline()
        except psutil.Error:
            continue
        if WEBUI_COMMAND in words[1:]:
            return shlex.join([PACKAGE_NAME, *words[words.index(WEBUI_COMMAND, 1) :]])
    return f"""{PACKAGE_NAME} {WEBUI_COMMAND}"""
