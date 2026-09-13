import platform
import shutil
from pathlib import Path

from stackops.utils.sandbox.containers import build_container_command
from stackops.utils.sandbox.options import SandboxAccess, SandboxBackend, SandboxOptions


def validate_sandbox_options(options: SandboxOptions) -> None:
    host_system = platform.system()
    if options.backend == SandboxBackend.NONE:
        if options.image is not None or options.settings is not None:
            raise ValueError("--sandbox-image and --sandbox-settings require --sandbox.")
        return
    if host_system not in ("Linux", "Darwin", "Windows"):
        raise ValueError(f"""Sandboxing is not supported on {host_system}.""")
    if options.backend == SandboxBackend.BWRAP and host_system != "Linux":
        raise ValueError("bwrap requires Linux. On Windows, run agents inside WSL2.")
    if options.backend == SandboxBackend.AI_JAIL and host_system == "Windows":
        raise ValueError("ai-jail requires Linux or macOS. On Windows, run agents inside WSL2.")
    if options.backend in (SandboxBackend.DOCKER, SandboxBackend.PODMAN):
        if options.image is None or not options.image.strip() or options.image.startswith("-"):
            raise ValueError("--sandbox-image must name a Linux image with the agent installed globally on PATH, outside HOME.")
    elif options.image is not None:
        raise ValueError("--sandbox-image is only supported with docker or podman.")
    if options.backend == SandboxBackend.SRT:
        if options.settings is None or not options.settings.is_file():
            raise ValueError("srt requires --sandbox-settings pointing to a policy allowing the agent's network, workspace and state paths.")
    elif options.settings is not None:
        raise ValueError("--sandbox-settings is only supported with srt.")
    if shutil.which(options.backend.value) is None:
        raise ValueError(f"""Required sandbox command not found: {options.backend.value}. Install it before selecting this sandbox.""")


def build_sandbox_command(
    *,
    command: list[str],
    options: SandboxOptions,
    directory: Path,
    access: SandboxAccess,
    read_only_paths: tuple[Path, ...],
    interactive: bool,
) -> list[str]:
    validate_sandbox_options(options)
    if options.backend == SandboxBackend.NONE:
        return command
    if not command:
        raise ValueError("A sandbox command must contain an executable.")
    executable = shutil.which(options.backend.value)
    if executable is None:
        raise ValueError(f"""Required sandbox command not found: {options.backend.value}.""")
    directory = directory.resolve()
    if not directory.is_dir():
        raise ValueError(f"""Sandbox working directory does not exist: {directory}""")
    if options.backend not in (SandboxBackend.DOCKER, SandboxBackend.PODMAN) and shutil.which(command[0]) is None:
        raise ValueError(f"""Required command not found: {command[0]}. Install it on the host before sandboxing it.""")
    if options.backend != SandboxBackend.SRT:
        for path in access.writable_paths:
            path.mkdir(parents=True, exist_ok=True)
    if options.backend in (SandboxBackend.DOCKER, SandboxBackend.PODMAN):
        if options.image is None:
            raise ValueError("Container sandboxes require --sandbox-image.")
        return build_container_command(
            executable=executable, backend=options.backend, image=options.image,
            command=command, directory=directory, access=access, read_only_paths=read_only_paths,
            host_system=platform.system(), interactive=interactive,
        )
    from stackops.utils.sandbox.host import build_host_sandbox_command

    return build_host_sandbox_command(
        executable=executable, command=command, options=options, directory=directory,
        access=access, read_only_paths=read_only_paths,
    )
