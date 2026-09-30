import sys
from pathlib import Path
from uuid import uuid4

from stackops.utils.sandbox.options import SandboxOptions, SandboxSync


def build_openshell_command(
    *,
    executable: str,
    command: list[str],
    options: SandboxOptions,
    directory: Path,
    read_only_paths: tuple[Path, ...],
    environment: dict[str, str],
    interactive: bool,
) -> list[str]:
    if options.image is None:
        raise ValueError("OpenShell requires --sandbox-image with the agent, sh, sleep, tar and git installed.")
    name = options.name if options.name is not None else f"""stackops-{uuid4().hex[:12]}"""
    sync = options.sync if options.sync is not None else SandboxSync.COPY_BACK
    arguments = [
        sys.executable, "-m", "stackops.utils.sandbox.openshell_run",
        "--executable", executable, "--image", options.image,
        "--directory", str(directory), "--name", name, "--sync", sync.value,
    ]
    if options.settings is not None:
        arguments.extend(["--settings", str(options.settings.resolve())])
    for provider in options.providers:
        arguments.extend(["--provider", provider])
    for path in dict.fromkeys(read_only_paths):
        arguments.extend(["--input", str(path.absolute())])
    for key, value in environment.items():
        if not Path(value).is_absolute():
            arguments.extend(["--env", f"""{key}={value}"""])
    if interactive:
        arguments.append("--interactive")
    return [*arguments, "--", *command]
