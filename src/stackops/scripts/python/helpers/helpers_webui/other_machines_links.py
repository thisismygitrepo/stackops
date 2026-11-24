import asyncio
import base64
import json
import re
import shutil
import socket
import threading
import urllib.error
import urllib.request
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.scripts.python.helpers.helpers_webui.constants import (
    MACHINE_CHECK_SECONDS,
    MACHINE_CONNECT_SECONDS,
    MACHINE_OPENED_FROM_VARIABLE,
    MACHINE_OUTPUT_KEPT_BYTES,
    MACHINE_PORT_ATTEMPTS,
    MACHINE_PORT_SLOTS,
    MACHINE_PROBLEM_LINES,
    MACHINE_REMOTE_PATH,
    MACHINE_REMOTE_PORT_BASE,
    MACHINE_SSH_OPTIONS,
    MACHINE_TERMINAL_COLUMNS,
    MACHINE_TERMINAL_ROWS,
    MACHINE_TUNNEL_PORT_BASE,
    PORT_PROBE_SECONDS,
    SHUTDOWN_JOIN_SECONDS,
    STOP_GRACE_SECONDS,
    TOKEN_COOKIE_PREFIX,
)
from stackops.scripts.python.helpers.helpers_webui.other_machines_marker import MachineSummary, OpenedFrom
from stackops.scripts.python.helpers.helpers_webui.pty_process import PtyHandle, spawn_pty
from stackops.scripts.python.helpers.helpers_webui.runs import build_run_environment

# The access link the other machine's web UI prints when it is up. What follows the token has to be there too, so half a token is never taken.
LINK_PATTERN = re.compile(rb"http://127\.0\.0\.1:\d+/\?token=([A-Za-z0-9_-]+)(?=[^A-Za-z0-9_-])")
TERMINAL_CODES = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-_]")
SSH_GOODBYE = re.compile(r"(Shared c|C)onnection to \S+ closed\.")


@dataclass
class SshSession:
    handle: PtyHandle
    pump_thread: threading.Thread
    output: bytearray
    exit_code: int | None


@dataclass(frozen=True)
class MachineLink:
    name: str
    address: str
    token: str
    there: MachineSummary
    session: SshSession


@dataclass(frozen=True)
class LinkProblem:
    reason: Literal["port_taken", "failed"]
    message: str


# What SSH or the other machine said last, as plain text. The line with the access link is left out.
def read_last_words(output: bytearray) -> str:
    text = TERMINAL_CODES.sub("", output.decode(encoding="utf-8", errors="replace")).replace("\r", "\n")
    lines = [line.strip(" \t│") for line in text.split("\n") if not line.lstrip().startswith(("╭", "╰"))]
    return " ".join([line for line in lines if line != "" and "token=" not in line and SSH_GOODBYE.fullmatch(line) is None][-MACHINE_PROBLEM_LINES:])


def start_session(argv: list[str], environment: dict[str, str]) -> tuple[SshSession, asyncio.Future[str | None]]:
    loop = asyncio.get_running_loop()
    token_found: asyncio.Future[str | None] = loop.create_future()
    # SSH runs in a terminal of its own, so it asks for one on the other machine too. The web UI there then ends with the connection, and the
    # connection ends with this server however this server stops: both lose their terminal.
    handle = spawn_pty(argv=argv, working_directory=str(Path.home()), environment=environment, rows=MACHINE_TERMINAL_ROWS, columns=MACHINE_TERMINAL_COLUMNS)

    def on_output(chunk: bytes) -> None:
        session.output.extend(chunk)
        found = LINK_PATTERN.search(session.output)
        if found is not None and not token_found.done():
            token_found.set_result(found.group(1).decode())
        del session.output[: max(0, len(session.output) - MACHINE_OUTPUT_KEPT_BYTES)]

    def on_exit(exit_code: int) -> None:
        session.exit_code = exit_code
        handle.close()
        if not token_found.done():
            token_found.set_result(None)

    def relay(chunk: bytes) -> None:
        loop.call_soon_threadsafe(on_output, chunk)

    def pump() -> None:
        exit_code = handle.pump(relay)
        loop.call_soon_threadsafe(on_exit, exit_code)

    session = SshSession(handle=handle, pump_thread=threading.Thread(target=pump, name="stackops-webui-machine", daemon=True), output=bytearray(), exit_code=None)
    session.pump_thread.start()
    return session, token_found


# Asks the other machine's web UI, through the tunnel, who it is. This is also the proof that the tunnel carries a page.
def ask_machine(name: str, tunnel_port: int, remote_port: int, token: str) -> MachineSummary | LinkProblem:
    request = urllib.request.Request(f"""http://127.0.0.1:{tunnel_port}/api/other-machines""", headers={"Cookie": f"""{TOKEN_COOKIE_PREFIX}_{remote_port}={token}"""})
    try:
        # No proxy: one set for this machine's web traffic would be asked for a loopback address.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request, timeout=MACHINE_CHECK_SECONDS) as response:
            answer: dict[str, MachineSummary] = json.loads(response.read())
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return LinkProblem(reason="failed", message=f"""StackOps on {name} is older than this one and cannot be opened from another machine yet. Update it there, then connect again.""")
        return LinkProblem(reason="failed", message=f"""The web UI on {name} started, but answered this machine with status {error.code}.""")
    except OSError as error:
        return LinkProblem(reason="failed", message=f"""The web UI on {name} started, but did not answer through the SSH tunnel: {error}""")
    except ValueError:
        return LinkProblem(reason="failed", message=f"""The SSH tunnel to {name} did not lead to its web UI. Something else on this machine answers on port {tunnel_port}.""")
    return answer["here"]


async def open_on_ports(name: str, ssh: str, environment: dict[str, str], marker: str, tunnel_port: int, remote_port: int) -> MachineLink | LinkProblem:
    # Single quotes around the whole command and none inside it: whichever shell the account has hands it to `sh` unchanged.
    remote_command = f"""sh -c 'PATH="{MACHINE_REMOTE_PATH}" {MACHINE_OPENED_FROM_VARIABLE}={marker} exec stackops webui --port {remote_port} --no-browser'"""
    options = [part for option in MACHINE_SSH_OPTIONS for part in ("-o", option)]
    session, token_found = start_session(
        argv=[ssh, "-tt", *options, "-L", f"""127.0.0.1:{tunnel_port}:127.0.0.1:{remote_port}""", "--", name, remote_command], environment=environment
    )
    link: MachineLink | None = None
    try:
        try:
            token = await asyncio.wait_for(asyncio.shield(token_found), timeout=MACHINE_CONNECT_SECONDS)
        except TimeoutError:
            return LinkProblem(
                reason="failed", message=f"""{name} did not start its web UI within {MACHINE_CONNECT_SECONDS:.0f} seconds. {read_last_words(session.output)}""".rstrip()
            )
        if token is None:
            said = read_last_words(session.output)
            if "Cannot listen on" in said:
                return LinkProblem(reason="port_taken", message=f"""{name} has no free port for its web UI among the {MACHINE_PORT_ATTEMPTS} kept for it. It said: {said}""")
            if session.exit_code != 255:
                return LinkProblem(reason="failed", message=f"""{name} did not start its web UI and stopped with exit code {session.exit_code}. It said: {said}""")
            asks = "Permission denied" in said or "Host key verification failed" in said
            hint = f""" The page cannot type a password or a key passphrase, or accept a new host key. Make `ssh {name}` work in a terminal without questions first.""" if asks else ""
            return LinkProblem(reason="failed", message=f"""SSH could not connect to {name}. It said: {said}{hint}""")
        there = await asyncio.to_thread(ask_machine, name=name, tunnel_port=tunnel_port, remote_port=remote_port, token=token)
        match there:
            case LinkProblem():
                return there
            case _:
                # What is kept from here on is what was said after the web UI came up: the words a connection that ends later ends with.
                session.output.clear()
                link = MachineLink(name=name, address=f"""http://127.0.0.1:{tunnel_port}/""", token=token, there=there, session=session)
                return link
    finally:
        # However this ends without a machine to show, a cancelled request included, SSH and the web UI it started do not stay behind.
        if link is None and session.exit_code is None:
            session.handle.stop(False)


async def open_link(links: dict[str, MachineLink], name: str, here_name: str, home_address: str) -> MachineLink | LinkProblem:
    existing = links.get(name)
    if existing is not None and existing.session.exit_code is None:
        return existing
    environment = build_run_environment(interactive=False)
    ssh = shutil.which("ssh", path=environment["PATH"])
    if ssh is None:
        return LinkProblem(reason="failed", message="This machine has no `ssh` command to reach other machines with.")
    opened_from: OpenedFrom = {"name": here_name, "address": home_address, "machine": name}
    # Letters, digits, - and _ only, so the text needs no quoting on its way through two shells.
    marker = base64.urlsafe_b64encode(json.dumps(opened_from).encode()).decode().rstrip("=")
    problem = LinkProblem(reason="port_taken", message=f"""None of the {MACHINE_PORT_ATTEMPTS} ports kept for {name} on this machine is free.""")
    for attempt in range(MACHINE_PORT_ATTEMPTS):
        slot = (zlib.crc32(name.encode()) + attempt) % MACHINE_PORT_SLOTS
        with socket.socket() as probe:
            probe.settimeout(PORT_PROBE_SECONDS)
            if probe.connect_ex(("127.0.0.1", MACHINE_TUNNEL_PORT_BASE + slot)) == 0:
                continue
        result = await open_on_ports(
            name=name, ssh=ssh, environment=environment, marker=marker, tunnel_port=MACHINE_TUNNEL_PORT_BASE + slot, remote_port=MACHINE_REMOTE_PORT_BASE + slot
        )
        match result:
            case MachineLink():
                links[name] = result
                return result
            case LinkProblem(reason="port_taken"):
                problem = result
            case LinkProblem():
                return result
    return problem


# Ending SSH ends the web UI on the other machine, and with it the tasks that web UI was running.
async def close_link(link: MachineLink) -> None:
    if link.session.exit_code is not None:
        return
    link.session.handle.stop(False)
    await asyncio.to_thread(link.session.pump_thread.join, STOP_GRACE_SECONDS)
    if link.session.pump_thread.is_alive():
        link.session.handle.stop(True)
    # The pump's last word, that SSH has ended, is on its way to this loop.
    await asyncio.sleep(0)


async def close_links(links: dict[str, MachineLink]) -> None:
    live = [link for link in links.values() if link.session.exit_code is None]
    for link in live:
        link.session.handle.stop(False)
    for link in live:
        await asyncio.to_thread(link.session.pump_thread.join, SHUTDOWN_JOIN_SECONDS)
    await asyncio.sleep(0)
