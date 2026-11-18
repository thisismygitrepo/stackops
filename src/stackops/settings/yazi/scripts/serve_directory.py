from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
from typing import Final, Literal, assert_never, cast, get_args
import webbrowser

from typer import Exit

from stackops.scripts.python.helpers.helpers_devops.network_service import install_service_dependency, start_service, stop_services, wait_for_service
from stackops.settings.yazi.scripts.serve_browser_file import find_free_port, get_lan_addresses, wait_for_return_to_yazi

type Command = list[str]
type Backend = Literal["filebrowser", "miniserve", "copyparty"]
type Exposure = Literal["local", "network"]

BACKENDS: Final[tuple[str, ...]] = cast(tuple[str, ...], get_args(Backend.__value__))  # pylint: disable=no-member  # PEP 695 aliases expose __value__.
EXPOSURES: Final[tuple[str, ...]] = cast(tuple[str, ...], get_args(Exposure.__value__))  # pylint: disable=no-member  # PEP 695 aliases expose __value__.
LOCAL_HOST: Final[str] = "127.0.0.1"
NETWORK_HOST: Final[str] = "0.0.0.0"
READY_TIMEOUT_SECONDS: Final[float] = 30.0


@dataclass(frozen=True)
class ServePlan:
    setup_commands: list[Command]
    serve_command: Command


def build_serve_plan(backend: Backend, directory: Path, host: str, port: int, state_directory: Path) -> ServePlan:
    match backend:
        case "filebrowser":
            database = str(state_directory / "filebrowser.db")
            return ServePlan(
                setup_commands=[
                    ["filebrowser", "config", "init", "-d", database, "--auth.method=noauth", "--address", host, "--port", str(port), "--root", str(directory)],
                    ["filebrowser", "users", "add", "browser", secrets.token_urlsafe(24), "-d", database, "--perm.execute=false"],
                ],
                serve_command=["filebrowser", "-d", database],
            )
        case "miniserve":
            return ServePlan(
                setup_commands=[],
                serve_command=["miniserve", str(directory), "--interfaces", host, "--port", str(port), "--upload-files", "--mkdir", "--rm-files"],
            )
        case "copyparty":
            return ServePlan(
                setup_commands=[],
                serve_command=["copyparty", "-i", host, "-p", str(port), "-v", f"{directory}::A", "--hist", str(state_directory / "copyparty-hist")],
            )
        case _:
            assert_never(backend)


def serve_directory(backend: Backend, exposure: Exposure, directory: Path) -> None:
    if shutil.which(backend) is None:
        print(f"{backend} is not installed, installing it with: devops software install {backend}")
        install_service_dependency(backend)
    match exposure:
        case "local":
            host = LOCAL_HOST
        case "network":
            host = NETWORK_HOST
        case _:
            assert_never(exposure)
    port = find_free_port(host=host)
    with tempfile.TemporaryDirectory(prefix="stackops-serve-directory-") as state_directory:
        plan = build_serve_plan(backend=backend, directory=directory, host=host, port=port, state_directory=Path(state_directory))
        for command in plan.setup_commands:
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise RuntimeError(f"{' '.join(command[:3])} failed with code {result.returncode}: {result.stderr.strip()}")
        service = start_service(name=backend, arguments=plan.serve_command, background=False, environment=None)
        try:
            wait_for_service(service=service, host=host, port=port, timeout=READY_TIMEOUT_SECONDS)
            local_url = f"http://{LOCAL_HOST}:{port}/"
            print(f"Serving {directory} with {backend}")
            print(f"URL: {local_url}")
            if exposure == "network":
                for address in get_lan_addresses():
                    print(f"Network URL: http://{address}:{port}/")
            webbrowser.open(local_url)
            wait_for_return_to_yazi()
        except KeyboardInterrupt:
            pass
        finally:
            stop_services([service])


def main(arguments: Sequence[str]) -> int:
    if len(arguments) != 2 or arguments[0] not in BACKENDS or arguments[1] not in EXPOSURES:
        sys.stderr.write(f"Usage: serve_directory.py {{{'|'.join(BACKENDS)}}} {{{'|'.join(EXPOSURES)}}}\n")
        return 2
    try:
        serve_directory(backend=cast(Backend, arguments[0]), exposure=cast(Exposure, arguments[1]), directory=Path.cwd())
    except Exit as error:
        return error.exit_code
    except FileNotFoundError as error:
        sys.stderr.write(f"{error}\n")
        return 127
    except RuntimeError as error:
        sys.stderr.write(f"{error}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
