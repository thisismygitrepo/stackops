import os
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from stackops.scripts.python.helpers.helpers_utils.environment_html import read_environment_variables, read_path_entries
from stackops.scripts.python.helpers.helpers_webui.runs import build_run_environment


# What the Environment page reads, at /api/machine/environment: the variables a task started from the web UI gets, and the folders of its
# program search path in lookup order with the programs in each. It is read here, in the server, because the command behind the page
# (`utils machine environment`) only offers a picker in a terminal or an HTML file. The environment is the one a run is given, not the server's
# own, which carries what its launcher added. A value that looks like a secret is left out by the command's own rule and never reaches the page.
def machine_environment_routes() -> list[Route]:
    def environment(_request: Request) -> JSONResponse:
        run_environment = build_run_environment(interactive=True)
        search_path = [entry for entry in run_environment.get("PATH", "").split(os.pathsep) if entry.strip()]
        return JSONResponse(
            {
                "home_directory": str(Path.home()),
                "path_separator": os.pathsep,
                "variables": read_environment_variables(environment=run_environment),
                "path_entries": read_path_entries(entries=search_path),
            }
        )

    return [Route("/api/machine/environment", environment)]
