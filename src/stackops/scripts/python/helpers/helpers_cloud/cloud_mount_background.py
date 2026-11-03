import os
from pathlib import Path
import subprocess
import tempfile
import time
from typing import TypedDict


class MountReceipt(TypedDict):
    remote: str
    mount_path: str
    status: str
    pid: int | None
    log_path: str | None


def launch_background_mount(remote: str, arguments: list[str], mount_path: Path, timeout: float) -> MountReceipt:
    if mount_path.is_mount():
        return {"remote": remote, "mount_path": str(mount_path), "status": "already_mounted", "pid": None, "log_path": None}
    if os.name == "nt" and mount_path.exists():
        raise RuntimeError(f"Windows mount destination already exists and is not mounted: {mount_path}")
    log_dir = Path.home() / ".cache" / "stackops" / "cloud-mounts"
    log_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="mount-", suffix=".log", dir=log_dir, delete=False) as log:
        process = subprocess.Popen(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=os.name != "nt",
            creationflags=(subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0,
        )
        log_path = log.name
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        returncode = process.poll()
        if returncode is not None:
            raise RuntimeError(f"Mount {remote} exited with code {returncode}; see {log_path}.")
        ready = mount_path.exists() if os.name == "nt" else mount_path.is_mount()
        if ready:
            return {"remote": remote, "mount_path": str(mount_path), "status": "mounted", "pid": process.pid, "log_path": log_path}
        time.sleep(0.1)
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    raise RuntimeError(f"Mount {remote} did not become ready within {timeout:g}s; see {log_path}.")
