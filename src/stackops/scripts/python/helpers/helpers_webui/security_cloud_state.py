import json
import platform
import shutil
import subprocess
from hashlib import file_digest
from pathlib import Path
from typing import Literal, TypedDict

from stackops.jobs.installer.checks.constants import SECURITY_UPLOAD_ROOT
from stackops.scripts.python.helpers.helpers_webui.security_constants import (
    CLOUD_REACH_TIMEOUT_SECONDS,
    FOLDER_MEASURE_LIMIT,
    RCLONE_REACH_FLAGS,
    UPLOAD_FINGERPRINT_LIMIT_BYTES,
)
from stackops.scripts.python.helpers.helpers_webui.security_paths import PathMeasure, measure_path
from stackops.utils.cloud.default_remote import DefaultRcloneRemoteConfigError, read_default_rclone_remote
from stackops.utils.cloud.rclone import RcloneConfigError, list_remote_names, remote_backend_type
from stackops.utils.cloud.rclone_wrapper import get_remote_path

# What stands between this machine and an upload: no rclone, no cloud account in rclone, none chosen for StackOps, or the chosen one is gone.
type CloudProblem = Literal["no_rclone", "no_remotes", "no_default", "default_gone", "unreadable"]
type UploadProblem = Literal["missing", "not_file", "outside_home"]


# The cloud an upload goes to, read from this machine alone. `kind` is the service behind the name, as rclone calls it ("drive", "onedrive").
class CloudState(TypedDict):
    problem: CloudProblem | None
    detail: str
    remotes: int
    name: str
    kind: str
    root: str
    system: str


# Whether the cloud answered just now, and how full it is where the service says so (None where it does not).
class CloudReach(TypedDict):
    reachable: bool
    detail: str
    total: int | None
    used: int | None
    free: int | None


# Where a file would land. The folder is named after the file's fingerprint, which is worked out here for a file small enough to read quickly.
class UploadPlan(TypedDict):
    file: PathMeasure
    problem: UploadProblem | None
    folder: str
    fingerprint: str


def read_cloud_state() -> CloudState:
    state: CloudState = {"problem": None, "detail": "", "remotes": 0, "name": "", "kind": "", "root": SECURITY_UPLOAD_ROOT, "system": platform.system().lower()}
    if shutil.which("rclone") is None:
        return {**state, "problem": "no_rclone"}
    try:
        names = list_remote_names()
    except RuntimeError as error:
        return {**state, "problem": "unreadable", "detail": str(error).splitlines()[0]}
    state["remotes"] = len(names)
    if len(names) == 0:
        return {**state, "problem": "no_remotes"}
    try:
        state["name"] = read_default_rclone_remote()
    except DefaultRcloneRemoteConfigError:
        return {**state, "problem": "no_default"}
    if state["name"] not in names:
        return {**state, "problem": "default_gone"}
    try:
        state["kind"] = remote_backend_type(remote_name=state["name"])
    except RcloneConfigError:
        state["kind"] = ""
    return state


def _rclone(arguments: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(["rclone", *arguments, *RCLONE_REACH_FLAGS], capture_output=True, text=True, check=False, timeout=CLOUD_REACH_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return None


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


# Asks the cloud how full it is, which also shows that it answers. A service that does not report its space is asked for its top folder instead.
def read_cloud_reach(name: str) -> CloudReach:
    unreached: CloudReach = {"reachable": False, "detail": "", "total": None, "used": None, "free": None}
    about = _rclone(["about", f"""{name}:""", "--json"])
    if about is None:
        return {**unreached, "detail": "It did not answer in time."}
    if about.returncode == 0:
        try:
            space = json.loads(about.stdout)
        except json.JSONDecodeError:
            space = {}
        numbers = {key: space.get(key) if isinstance(space, dict) and isinstance(space.get(key), int) else None for key in ("total", "used", "free")}
        return {"reachable": True, "detail": "", "total": numbers["total"], "used": numbers["used"], "free": numbers["free"]}
    if "support" not in about.stderr.lower():
        return {**unreached, "detail": _last_line(about.stderr)}
    listing = _rclone(["lsd", f"""{name}:""", "--max-depth", "1"])
    if listing is None:
        return {**unreached, "detail": "It did not answer in time."}
    return {**unreached, "reachable": listing.returncode == 0, "detail": "" if listing.returncode == 0 else _last_line(listing.stderr)}


def read_upload_plan(path: Path) -> UploadPlan:
    file = measure_path(path, limit=FOLDER_MEASURE_LIMIT)
    plan: UploadPlan = {"file": file, "problem": None, "folder": "", "fingerprint": ""}
    if file["kind"] == "missing":
        return {**plan, "problem": "missing"}
    if file["kind"] != "file":
        return {**plan, "problem": "not_file"}
    try:
        mapped = get_remote_path(local_path=path, root=SECURITY_UPLOAD_ROOT, os_specific=True, rel2home=True, strict=True)
    except ValueError:
        return {**plan, "problem": "outside_home"}
    plan["folder"] = (mapped.parent / path.stem).as_posix()
    if file["size"] <= UPLOAD_FINGERPRINT_LIMIT_BYTES:
        try:
            with path.open("rb") as opened:
                plan["fingerprint"] = file_digest(opened, "sha256").hexdigest()
        except OSError:
            plan["fingerprint"] = ""
    return plan
