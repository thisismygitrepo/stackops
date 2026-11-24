import asyncio
import subprocess
from typing import Literal

from stackops.scripts.python.helpers.helpers_webui.constants import (
    MACHINE_INSTALL_COMMAND,
    MACHINE_PREPARE_SECONDS,
    MACHINE_REMOTE_PATH,
    MACHINE_SSH_OPTIONS,
    MACHINE_UPDATE_COMMAND,
)
from stackops.scripts.python.helpers.helpers_webui.other_machines_links import LinkProblem, find_ssh, read_last_words

# What the page offers to run on a machine that cannot be opened yet: StackOps installed where it is missing, updated where it is too old.
type MachineStep = Literal["install", "update"]


# The step runs over SSH without a terminal, so anything that would ask a question there fails at once instead of waiting for an answer.
async def prepare_machine(name: str, step: MachineStep) -> LinkProblem | None:
    found = find_ssh()
    if isinstance(found, LinkProblem):
        return found
    ssh, environment = found
    match step:
        case "install":
            command, doing = MACHINE_INSTALL_COMMAND, "Installing"
        case "update":
            command, doing = MACHINE_UPDATE_COMMAND, "Updating"
    options = [part for option in MACHINE_SSH_OPTIONS for part in ("-o", option)]
    argv = [ssh, "-T", *options, "--", name, f"""sh -c 'PATH="{MACHINE_REMOTE_PATH}"; {command}'"""]
    try:
        finished = await asyncio.to_thread(
            subprocess.run, argv, env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=MACHINE_PREPARE_SECONDS, check=False
        )
    except subprocess.TimeoutExpired:
        return LinkProblem(reason="failed", message=f"""{doing} StackOps on {name} did not finish within {MACHINE_PREPARE_SECONDS / 60:.0f} minutes.""")
    if finished.returncode != 0:
        return LinkProblem(reason="failed", message=f"""{doing} StackOps on {name} stopped with exit code {finished.returncode}. It said: {read_last_words(bytearray(finished.stdout))}""")
    return None
