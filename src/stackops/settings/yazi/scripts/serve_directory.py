from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
from typing import Final, Literal, assert_never, cast, get_args
import webbrowser

from stackops.scripts.python.helpers.helpers_devops.network_service import start_service, stop_services, wait_for_service
from stackops.settings.yazi.scripts.serve_browser_file import find_free_port, wait_for_return_to_yazi

type Command = list[str]
type Backend = Literal["filebrowser", "miniserve", "copyparty"]

BACKENDS: Final[tuple[str, ...]] = get_args(Backend.__value__)
HOST: Final[str] = "127.0.0.1"
READY_TIMEOUT_SECONDS: Final[float] = 30.0
FILEBROWSER_READ_ONLY_FLAGS: Final[tuple[str, ...]] = (
    "--perm.admin=false",
    "--perm.create=false",
    "--perm.delete=false",
    "--perm.execute=false",
    "--perm.modify=false",
    "--perm.rename=false",
    "--perm.share=false",
    "--perm.download=true",
)


@dataclass(frozen=True)
class ServePlan:
    setup_commands: list[Command]
    serve_command: Command


def build_serve_plan(backend: Backend, directory: Path, port: int, state_directory: Path) -> ServePlan:
    match backend:
        case "filebrowser":
            database = str(state_directory / "filebrowser.db")
            return ServePlan(
                setup_commands=[
                    ["filebrowser", "config", "init", "-d", database, "--auth.method=noauth", "--address", HOST, "--port", str(port), "--root", str(directory)],
                    ["filebrowser", "users", "add", "viewer", secrets.token_urlsafe(24), "-d", database, *FILEBROWSER_READ_ONLY_FLAGS],
                ],
                serve_command=["filebrowser", "-d", database],
            )
        case "miniserve":
            return ServePlan(setup_commands=[], serve_command=["miniserve", "--interfaces", HOST, "--port", str(port), str(directory)])
        case "copyparty":
            return ServePlan(
                setup_commands=[],
                serve_command=["uv", "tool", "run", "copyparty", "-i", HOST, "-p", str(port), "-v", f"{directory}::r", "--hist", str(state_directory / "copyparty-hist")],
            )
        case _:
            assert_never(backend)


def serve_directory(backend: Backend, directory: Path) -> None:
    port = find_free_port(host=HOST)
    with tempfile.TemporaryDirectory(prefix="stackops-serve-directory-") as state_directory:
        plan = build_serve_plan(backend=backend, directory=directory, port=port, state_directory=Path(state_directory))
        for command in plan.setup_commands:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"{' '.join(command[:3])} failed with code {result.returncode}: {result.stderr.strip()}")
        service = start_service(name=backend, arguments=plan.serve_command, background=False, environment=None)
        try:
            wait_for_service(service=service, host=HOST, port=port, timeout=READY_TIMEOUT_SECONDS)
            url = f"http://{HOST}:{port}/"
            print(f"Serving {directory} read-only with {backend}")
            print(f"URL: {url}")
            webbrowser.open(url)
            wait_for_return_to_yazi()
        except KeyboardInterrupt:
            pass
        finally:
            stop_services([service])


def main(arguments: Sequence[str]) -> int:
    if len(arguments) != 1 or arguments[0] not in BACKENDS:
        sys.stderr.write(f"Usage: serve_directory.py {{{'|'.join(BACKENDS)}}}\n")
        return 2
    try:
        serve_directory(backend=cast(Backend, arguments[0]), directory=Path.cwd())
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 127
    except RuntimeError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
