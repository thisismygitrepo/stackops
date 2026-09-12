import fcntl
import hashlib
import json
import os
import signal
import socket
import subprocess
import time
from pathlib import Path
from types import FrameType

import psutil

from stackops.utils.dashboards.constants import POLL_INTERVAL_SECONDS, STARTUP_TIMEOUT_SECONDS, STOP_TIMEOUT_SECONDS
from stackops.utils.dashboards.ownership import DashboardOwner, listener_pids, owner_is_alive, owner_is_healthy, read_owner


def _interrupt_dashboard(signum: int, _frame: FrameType | None) -> None:
    raise KeyboardInterrupt(f"""Dashboard supervisor received signal {signum}""")


def run_dashboard(
    *, command: tuple[str, ...], port: int, identity: str, cwd: Path,
    environment: dict[str, str], health_path: str, state_dir: Path,
) -> int:
    if not 1 <= port <= 65535:
        raise ValueError(f"""Invalid dashboard port: {port}""")
    fingerprint = hashlib.sha256(json.dumps(
        [identity, command, str(cwd.resolve()), environment], sort_keys=True,
    ).encode()).hexdigest()
    state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    owner_path = state_dir / f"""{port}.json"""
    lock_path = state_dir / f"""{port}.lock"""
    child: subprocess.Popen[bytes] | None = None
    owner: DashboardOwner | None = None
    previous_sigterm = signal.signal(signal.SIGTERM, _interrupt_dashboard)
    try:
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            existing = read_owner(owner_path)
            if existing is not None and owner_is_alive(existing):
                if existing.fingerprint != fingerprint:
                    raise RuntimeError(f"""Port {port} belongs to a different managed dashboard (PID {existing.pid}); left running.""")
                if not owner_is_healthy(existing, port, health_path):
                    raise RuntimeError(f"""Dashboard PID {existing.pid} on port {port} is unhealthy; review its owner before stopping it.""")
                print(f"""Reusing {identity} (PID {existing.pid}) at http://localhost:{port}""", flush=True)
                return 0
            listeners = listener_pids(port)
            if listeners:
                pids = ", ".join(sorted("unknown" if pid is None else str(pid) for pid in listeners))
                raise RuntimeError(f"""Port {port} has an unmanaged listener (PID {pids}); left running. Review its owner before stopping it.""")
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                probe.bind(("0.0.0.0", port))
            child = subprocess.Popen(command, cwd=cwd, env=os.environ | environment, start_new_session=True)
            try:
                created_at = psutil.Process(child.pid).create_time()
            except psutil.NoSuchProcess:
                raise RuntimeError(f"""{identity} exited with status {child.wait()} before becoming healthy on port {port}.""") from None
            owner = DashboardOwner(fingerprint=fingerprint, pid=child.pid, created_at=created_at)
            pending_path = owner_path.with_suffix(".pending")
            pending_path.write_text(owner.model_dump_json(), encoding="utf-8")
            pending_path.replace(owner_path)
            deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS
            while not owner_is_healthy(owner, port, health_path):
                exit_code = child.poll()
                if exit_code is not None:
                    raise RuntimeError(f"""{identity} exited with status {exit_code} before becoming healthy on port {port}.""")
                if time.monotonic() >= deadline:
                    raise RuntimeError(f"""{identity} did not become healthy on port {port} within {STARTUP_TIMEOUT_SECONDS:g} seconds.""")
                time.sleep(POLL_INTERVAL_SECONDS)
            print(f"""Started {identity} (PID {child.pid}) at http://localhost:{port}""", flush=True)
        return child.wait()
    except KeyboardInterrupt:
        return 130
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        if child is not None:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=STOP_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            with lock_path.open("a+", encoding="utf-8") as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                if owner is not None and read_owner(owner_path) == owner:
                    owner_path.unlink()
