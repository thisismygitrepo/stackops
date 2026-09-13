import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import cast


def _native_command(command: list[str]) -> list[str]:
    if not command:
        raise ValueError("A sandbox command must contain an executable.")
    resolved = shutil.which(command[0])
    if resolved is None:
        raise ValueError(f"""Agent executable not found: {command[0]}.""")
    executable = Path(resolved).resolve()
    if executable.suffix.lower() != ".exe":
        raise ValueError(
            f"""Native Windows SRT requires an agent .exe; {executable.name} is a script launcher. Use a native executable installation or run agents inside WSL2."""
        )
    return [str(executable), *command[1:]]


def build_windows_srt_command(
    *,
    executable: str,
    command: list[str],
    settings: Path,
    directory: Path,
    environment_names: tuple[str, ...],
    environment_overrides: dict[str, str],
) -> list[str]:
    native_command = _native_command(command)
    return [
        sys.executable,
        "-m",
        "stackops.utils.sandbox.windows_srt",
        "--executable",
        executable,
        "--settings",
        str(settings.resolve()),
        "--directory",
        str(directory.resolve()),
        "--environment-names",
        json.dumps(environment_names),
        "--environment-overrides",
        json.dumps(environment_overrides),
        "--command-json",
        json.dumps(native_command),
    ]


def _srt_command(executable: str) -> list[str]:
    runtime = Path(executable).resolve()
    if runtime.suffix.lower() == ".exe":
        return [str(runtime)]
    script = runtime.parent / "node_modules/@anthropic-ai/sandbox-runtime/dist/cli.js"
    node = shutil.which("node.exe")
    if runtime.suffix.lower() != ".cmd" or not script.is_file() or node is None:
        raise ValueError(
            "Native Windows SRT requires node.exe and a global npm installation of @anthropic-ai/sandbox-runtime, or a native srt.exe."
        )
    return [node, str(script)]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a native Windows agent through SRT. Run srt windows-install once; "
            "the settings must allow the agent's network, workspace, executable and state paths."
        )
    )
    parser.add_argument("--executable", required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--environment-names", required=True)
    parser.add_argument("--environment-overrides", required=True)
    parser.add_argument("--command-json", required=True)
    arguments = parser.parse_args()
    if sys.platform != "win32":
        parser.error("This SRT adapter requires native Windows.")
    try:
        command_value: object = json.loads(cast(str, arguments.command_json))
        names_value: object = json.loads(cast(str, arguments.environment_names))
        overrides_value: object = json.loads(cast(str, arguments.environment_overrides))
        if not isinstance(command_value, list) or not all(isinstance(value, str) for value in command_value):
            raise ValueError("--command-json must contain a JSON array of strings.")
        if not isinstance(names_value, list) or not all(isinstance(value, str) for value in names_value):
            raise ValueError("--environment-names must contain a JSON array of strings.")
        if not isinstance(overrides_value, dict) or not all(isinstance(key, str) and isinstance(value, str) for key, value in overrides_value.items()):
            raise ValueError("--environment-overrides must contain a JSON object of strings.")
        command = _native_command(cast(list[str], command_value))
        environment_names = cast(list[str], names_value)
        directory = cast(Path, arguments.directory).resolve()
        settings = cast(Path, arguments.settings).resolve()
        if not directory.is_dir() or not settings.is_file():
            raise ValueError("The SRT working directory and settings file must exist.")
        environment = {"HOME": str(Path.home()), "USERPROFILE": str(Path.home())}
        for name in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", *environment_names):
            value = os.environ.get(name)
            if value is not None:
                environment[name] = value
        environment.update(cast(dict[str, str], overrides_value))
        payload = {
            "executable": command[0],
            "arguments": subprocess.list2cmdline(command[1:]),
            "directory": str(directory),
            "environment": environment,
        }
        encoded_payload = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
        script = f"""
$ErrorActionPreference = 'Stop'
try {{
    $payload = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('{encoded_payload}')) | ConvertFrom-Json
    $start = New-Object System.Diagnostics.ProcessStartInfo
    $start.UseShellExecute = $false
    $start.FileName = $payload.executable
    $start.Arguments = $payload.arguments
    $start.WorkingDirectory = $payload.directory
    foreach ($entry in $payload.environment.PSObject.Properties) {{
        $start.EnvironmentVariables[$entry.Name] = [string] $entry.Value
    }}
    $process = [System.Diagnostics.Process]::Start($start)
    $process.WaitForExit()
    exit $process.ExitCode
}} catch {{
    [Console]::Error.WriteLine('Unable to start the agent in SRT. Check the executable and state-path grants in --sandbox-settings. ' + $_.Exception.Message)
    exit 1
}}
"""
        encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        shell_command = rf""""%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -NonInteractive -EncodedCommand {encoded_script}"""
        if len(shell_command) > 8000:
            raise ValueError(
                "The encoded SRT launch is too long for Windows cmd.exe's 8191-character limit. Shorten the arguments or forwarded environment, or run agents inside WSL2."
            )
        runtime_command = _srt_command(cast(str, arguments.executable))
        runtime_environment = {name: value for name, value in os.environ.items() if name != "SRT_DEBUG"}
        completed = subprocess.run(
            [*runtime_command, "--settings", str(settings), "-c", shell_command],
            cwd=directory,
            env=runtime_environment,
            check=False,
            shell=False,
        )
        return completed.returncode
    except (OSError, ValueError) as error:
        print(f"""Windows SRT launch failed: {error}""", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
