import os
import platform

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.profile.shell_profile_source import ShellProfileSource
from stackops.scripts.python.helpers.helpers_webui.terminal_shell_profile_state import read_shell_profiles


# What the Shell profile page reads: the shells StackOps can set up, where each one's profile is, and whether StackOps' line is in it.
# Setting a shell up goes through the CLI like any other run, so nothing here changes a file.
def terminal_shell_profile_routes() -> list[Route]:
    pwsh_sources: dict[str, ShellProfileSource] = {}

    def read(_request: Request) -> JSONResponse:
        return JSONResponse(read_shell_profiles(system_name=platform.system(), shell_variable=os.environ.get("SHELL"), pwsh_sources=pwsh_sources))

    return [Route("/api/terminal/shell-profile/state", read)]
