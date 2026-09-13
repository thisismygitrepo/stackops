import os
from pathlib import Path, PurePosixPath

from stackops.utils.sandbox.options import SandboxAccess, SandboxBackend


def container_path(path: Path, *, is_windows: bool) -> str:
    if is_windows:
        drive = path.drive.rstrip(":").lower()
        if not drive or drive.startswith("\\\\"):
            raise ValueError("Container sandboxes require a local drive path on Windows.")
        return str(PurePosixPath("/host", drive, *path.parts[1:]))
    return str(path)


def build_container_command(
    *,
    executable: str,
    backend: SandboxBackend,
    image: str,
    command: list[str],
    directory: Path,
    access: SandboxAccess,
    read_only_paths: tuple[Path, ...],
    host_system: str,
    interactive: bool,
) -> list[str]:
    is_windows = host_system == "Windows"
    home = Path.home()
    sandbox_home = container_path(home, is_windows=is_windows)
    arguments = [executable, "run", "--rm", "--interactive", "--platform", "linux"]
    if interactive:
        arguments.append("--tty")
    arguments.extend([
        "--cap-drop=ALL", "--security-opt=no-new-privileges",
        "--env", f"""HOME={sandbox_home}""",
        "--tmpfs", f"""{sandbox_home}:rw,exec,mode=1777""",
        "--workdir", container_path(directory, is_windows=is_windows),
    ])
    if host_system == "Linux":
        if backend == SandboxBackend.PODMAN:
            arguments.append("--userns=keep-id")
        arguments.extend(["--user", f"""{os.getuid()}:{os.getgid()}"""])
    else:
        arguments.extend(["--user", "0:0"])
    for path in dict.fromkeys((directory, *access.writable_paths)):
        if "," in str(path):
            raise ValueError(f"""Container bind mount paths cannot contain commas: {path}""")
        target = container_path(path, is_windows=is_windows)
        arguments.extend(["--mount", f"""type=bind,source={path},target={target}"""])
    for path in dict.fromkeys(read_only_paths):
        if "," in str(path):
            raise ValueError(f"""Container bind mount paths cannot contain commas: {path}""")
        target = container_path(path, is_windows=is_windows)
        arguments.extend(["--mount", f"""type=bind,source={path},target={target},readonly"""])
    for name in dict.fromkeys((*access.environment_names, *access.environment_overrides)):
        value = access.environment_overrides.get(name, os.environ.get(name))
        if value is None:
            continue
        environment_argument = f"""{name}={value}""" if name in access.environment_overrides else name
        if is_windows:
            value_path = Path(value)
            if value_path.is_absolute() and any(path.is_relative_to(value_path) for path in access.writable_paths):
                environment_argument = f"""{name}={container_path(value_path, is_windows=True)}"""
        arguments.extend(["--env", environment_argument])
    arguments.extend(["--entrypoint", command[0], image, *command[1:]])
    return arguments
