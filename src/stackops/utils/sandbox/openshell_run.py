import argparse
import shlex
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import cast

from stackops.utils.sandbox.openshell_transfer import upload_workspace
from stackops.utils.sandbox.openshell_workspace import merge_workspace, snapshot_workspace
from stackops.utils.sandbox.options import SandboxSync


def run_openshell(
    *,
    executable: str,
    directory: Path,
    image: str,
    name: str,
    settings: Path | None,
    providers: tuple[str, ...],
    sync: SandboxSync,
    command: list[str],
    inputs: tuple[Path, ...],
    environment: tuple[str, ...],
    interactive: bool,
) -> int:
    created = False
    try:
        capabilities = subprocess.run(
            [executable, "sandbox", "create", "--help"],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True,
        )
        if "--detach" not in capabilities.stdout:
            raise ValueError(
                "Update OpenShell before running this backend: devops install openshell --update --source library. "
                "The installed CLI does not support detached sandbox creation."
            )
        with TemporaryDirectory(prefix="stackops-openshell-") as temporary:
            staging = Path(temporary)
            snapshot = staging / "stackops-project"
            snapshot_workspace(directory=directory, destination=snapshot)
            create = [
                executable, "sandbox", "create", "--name", name, "--from", image,
                "--detach", "--no-tty", "--no-auto-providers",
            ]
            if settings is not None:
                create.extend(["--policy", str(settings)])
            for provider in providers:
                create.extend(["--provider", provider])
            print(f"""Creating OpenShell sandbox {name}.""", file=sys.stderr)
            subprocess.run(
                [*create, "--", "sleep", "infinity"], stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
            )
            created = True
            project, remote_command = upload_workspace(
                executable=executable, name=name, snapshot=snapshot, inputs=inputs, command=command, staging=staging,
            )
            print(f"""OpenShell project: {project}""", file=sys.stderr)
            execution = [
                executable, "sandbox", "exec", "--name", name, "--workdir", str(project),
                "--no-login-shell", "--tty" if interactive else "--no-tty",
            ]
            for value in environment:
                execution.extend(["--env", value])
            completed = subprocess.run([*execution, "--", *remote_command], check=False)
            if sync == SandboxSync.MANUAL:
                download = [executable, "sandbox", "download", name, str(project), f"""./{name}-results"""]
                print(f"""Project changes remain in {name}. Download with: {shlex.join(download)}""", file=sys.stderr)
                return completed.returncode
            result = staging / "result"
            result.mkdir()
            subprocess.run(
                [executable, "sandbox", "download", name, str(project), str(result)],
                stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
            )
            conflicts = merge_workspace(directory=directory, baseline=snapshot, result=result)
            if conflicts:
                print("These paths need manual reconciliation; local copies were preserved:", file=sys.stderr)
                for conflict in conflicts:
                    print(f"""  {conflict}""", file=sys.stderr)
                return completed.returncode if completed.returncode != 0 else 1
            print("OpenShell project changes copied back.", file=sys.stderr)
            if completed.returncode == 0:
                subprocess.run(
                    [executable, "sandbox", "delete", name], stdin=subprocess.DEVNULL, stdout=sys.stderr, check=True,
                )
                created = False
            return completed.returncode
    except subprocess.CalledProcessError as error:
        if error.stderr:
            print(error.stderr, file=sys.stderr)
        print(f"""OpenShell operation failed (exit {error.returncode}).""", file=sys.stderr)
        if not created:
            print(
                f"""If provisioning allocated a sandbox, inspect it with: openshell sandbox get {shlex.quote(name)}""",
                file=sys.stderr,
            )
        return error.returncode if error.returncode > 0 else 1
    except (OSError, ValueError) as error:
        print(f"""OpenShell run failed: {error}""", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    finally:
        if created:
            print(
                f"""Sandbox retained as {name}. Use openshell sandbox stop {shlex.quote(name)} to stop compute, """
                f"""or openshell sandbox delete {shlex.quote(name)} when finished.""",
                file=sys.stderr,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an agent in an OpenShell project snapshot.")
    parser.add_argument("--executable", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--image", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--settings", type=Path)
    parser.add_argument("--provider", action="append", default=[])
    parser.add_argument("--input", type=Path, action="append", default=[])
    parser.add_argument("--env", action="append", default=[])
    parser.add_argument("--sync", type=SandboxSync, choices=list(SandboxSync), required=True)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args()
    command = cast(list[str], arguments.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        parser.error("An agent command is required after --.")
    return run_openshell(
        executable=cast(str, arguments.executable), directory=cast(Path, arguments.directory),
        image=cast(str, arguments.image), name=cast(str, arguments.name),
        settings=cast(Path | None, arguments.settings), providers=tuple(cast(list[str], arguments.provider)),
        sync=cast(SandboxSync, arguments.sync), command=command, inputs=tuple(cast(list[Path], arguments.input)),
        environment=tuple(cast(list[str], arguments.env)), interactive=cast(bool, arguments.interactive),
    )


if __name__ == "__main__":
    raise SystemExit(main())
