import os
import platform
from pathlib import Path

from stackops.utils.sandbox.options import SandboxAccess, SandboxBackend, SandboxOptions


def build_host_sandbox_command(
    *,
    executable: str,
    command: list[str],
    options: SandboxOptions,
    directory: Path,
    access: SandboxAccess,
    read_only_paths: tuple[Path, ...],
) -> list[str]:
    prefix = ["env", *(f"""{name}={value}""" for name, value in access.environment_overrides.items())] if access.environment_overrides else []
    match options.backend:
        case SandboxBackend.SRT:
            if options.settings is None:
                raise ValueError("srt requires --sandbox-settings.")
            if platform.system() == "Windows":
                from stackops.utils.sandbox.windows_srt import build_windows_srt_command

                return build_windows_srt_command(
                    executable=executable, command=command, settings=options.settings.resolve(),
                    directory=directory, environment_names=access.environment_names, environment_overrides=access.environment_overrides,
                )
            return [*prefix, executable, "--settings", str(options.settings.resolve()), "--", *command]
        case SandboxBackend.AI_JAIL:
            arguments = [executable, "--exec", "--no-save-config", "--network"]
            for path in dict.fromkeys((directory, *access.writable_paths)):
                if ":" in str(path):
                    raise ValueError(f"""ai-jail mapping paths cannot contain colons: {path}""")
                arguments.extend(["--rw-map", str(path)])
            for path in dict.fromkeys(read_only_paths):
                if ":" in str(path):
                    raise ValueError(f"""ai-jail mapping paths cannot contain colons: {path}""")
                arguments.extend(["--map", str(path)])
            for name in dict.fromkeys((*access.environment_names, *access.environment_overrides)):
                if name in os.environ or name in access.environment_overrides:
                    arguments.extend(["--env", name])
            return [*prefix, *arguments, "--", *command]
        case SandboxBackend.BWRAP:
            arguments = [
                executable, "--unshare-all", "--share-net", "--die-with-parent", "--new-session",
                "--ro-bind", "/", "/", "--tmpfs", "/tmp", "--tmpfs", "/run",
                "--dev", "/dev", "--proc", "/proc",
            ]
            resolver = Path("/etc/resolv.conf")
            if resolver.is_symlink():
                arguments.extend(["--ro-bind", str(resolver.resolve()), str(resolver.resolve())])
            for path in dict.fromkeys((directory, *access.writable_paths)):
                arguments.extend(["--bind", str(path), str(path)])
            for path in dict.fromkeys(read_only_paths):
                arguments.extend(["--ro-bind", str(path), str(path)])
            for name, value in access.environment_overrides.items():
                arguments.extend(["--setenv", name, value])
            arguments.extend(["--setenv", "TMPDIR", "/tmp", "--chdir", str(directory), "--", *command])
            return arguments
        case _:
            raise ValueError(f"""Unsupported host sandbox: {options.backend.value}.""")
