from dataclasses import dataclass
from typing import Literal, TypedDict

from stackops.scripts.python.helpers.helpers_webui.machine_update_checkout import CheckoutView, read_checkout, read_local_history
from stackops.scripts.python.helpers.helpers_webui.machine_update_install import InstallView, ToolsFolder, read_install, restart_command, running_environment, tool_environment
from stackops.scripts.python.helpers.helpers_webui.machine_update_latest import BranchAnswer, IndexAnswer, LatestView, latest_commits, latest_release, no_answer


# What the page's routes keep between requests: when this server started and with which version, where uv keeps its tools, and the last answers
# from the network.
@dataclass
class UpdateMemory:
    started_at: float
    started_version: str
    tools: ToolsFolder
    answers: dict[str, IndexAnswer | BranchAnswer]


# What is installed and what an update would do, from this machine alone. `route` is the update command's own choice: with a source checkout in
# its usual place it pulls that and reinstalls from it, otherwise it installs the newest release from the package index. `installed` is the uv
# tool the update reinstalls, or the copy this server runs from where there is no such tool. `served_from` is the environment this server runs
# from. `restart_needed` says the installed files are newer than this server, which goes on running what it loaded when it started.
class UpdateState(TypedDict):
    route: Literal["checkout", "index"]
    python: str
    commit_message: str
    installed: InstallView | None
    served_from: str
    served_by_installed: bool
    started_at: float
    started_version: str
    restart_needed: bool
    restart_command: str
    checkout: CheckoutView | None


def read_update_state(memory: UpdateMemory) -> UpdateState:
    from stackops.scripts.python.helpers.helpers_devops.cli_self_repo import AUTO_COMMIT_MESSAGE, developer_repo_root
    from stackops.utils.constants import STACKOPS_PYTHON_VERSION

    running = running_environment()
    tool = tool_environment(running=running, known=memory.tools)
    environment = running if tool is None else tool
    installed = None if environment is None else read_install(environment=environment)
    served_by_installed = environment is not None and environment == running
    root = developer_repo_root()
    return {
        "route": "index" if root is None else "checkout",
        "python": STACKOPS_PYTHON_VERSION,
        "commit_message": AUTO_COMMIT_MESSAGE,
        "installed": installed,
        "served_from": "" if running is None else str(running),
        "served_by_installed": served_by_installed,
        "started_at": memory.started_at,
        "started_version": memory.started_version,
        "restart_needed": installed is not None and (installed["installed_at"] > memory.started_at or (served_by_installed and installed["version"] != memory.started_version)),
        "restart_command": restart_command(),
        "checkout": None if root is None else read_checkout(root=root),
    }


# The newest version there is, asked of the place the update would get it from. For a checkout that is the branch it follows on GitHub; one that
# follows nothing there has no online record to compare with, and the page falls back on what its last fetch left.
def read_latest(memory: UpdateMemory, fresh: bool) -> LatestView:
    from stackops.scripts.python.helpers.helpers_devops.cli_self_repo import developer_repo_root

    root = developer_repo_root()
    if root is None:
        running = running_environment()
        tool = tool_environment(running=running, known=memory.tools)
        environment = running if tool is None else tool
        installed = None if environment is None else read_install(environment=environment)
        return latest_release(installed_version=memory.started_version if installed is None else installed["version"], fresh=fresh, answers=memory.answers)
    checkout = read_checkout(root=root)
    if checkout["online"] == "":
        return no_answer(source="none", trouble="", page="")
    return latest_commits(repository=checkout["online"], branch=checkout["online_branch"], history=read_local_history(root=root), fresh=fresh, answers=memory.answers)
