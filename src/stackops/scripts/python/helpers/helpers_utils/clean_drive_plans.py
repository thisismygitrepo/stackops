import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal, TypedDict, cast

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import JOURNAL_RETAIN_MEBIBYTES, QUERY_TIMEOUT_SECONDS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import CommandPlan, EstimateKind, PathGlob, PlanFailure
from stackops.scripts.python.helpers.helpers_utils.clean_drive_paths import expand_globs
from stackops.scripts.python.helpers.helpers_utils.clean_drive_usage import parse_size


type DockerKind = Literal["Containers", "Images", "Local Volumes", "Build Cache"]


class DockerDiskUsageRow(TypedDict):
    Type: str
    Reclaimable: str


def resolve_command(command: tuple[str, ...]) -> tuple[str, ...]:
    executable = shutil.which(command[0])
    if executable is None:
        raise FileNotFoundError(f"""{command[0]} is not on PATH""")
    return (executable, *command[1:])


def query_tool(command: tuple[str, ...]) -> str | PlanFailure:
    rendered = " ".join(command)
    try:
        completed = subprocess.run(
            resolve_command(command), capture_output=True, text=True, timeout=QUERY_TIMEOUT_SECONDS, check=False,
            env={**os.environ, "LC_ALL": "C", "LANG": "C"},
        )
    except subprocess.TimeoutExpired:
        return PlanFailure(message=f"""`{rendered}` timed out after {QUERY_TIMEOUT_SECONDS}s""")
    if completed.returncode != 0:
        lines = (completed.stderr or completed.stdout).strip().splitlines()
        return PlanFailure(message=f"""`{rendered}` failed: {lines[-1] if lines else f"exit code {completed.returncode}"}""")
    return completed.stdout


def plan_tool_directory(*, query: tuple[str, ...], clean: tuple[str, ...], estimate_kind: EstimateKind) -> CommandPlan | PlanFailure:
    output = query_tool(query)
    if isinstance(output, PlanFailure):
        return output
    directory = output.strip()
    if not directory or directory == "off":
        return PlanFailure(message=f"""`{" ".join(query)}` reported no cache directory""")
    return CommandPlan(commands=(clean,), measured_paths=(Path(directory),), reported_bytes=None, estimate_kind=estimate_kind)


def plan_from_globs(*, globs: tuple[PathGlob, ...], clean: tuple[str, ...]) -> CommandPlan | PlanFailure:
    return CommandPlan(commands=(clean,), measured_paths=tuple(expand_globs(globs)), reported_bytes=None, estimate_kind="exact")


def _reported_plan(*, output: str, pattern: str, clean: tuple[str, ...], estimate_kind: EstimateKind, retain_bytes: int) -> CommandPlan | PlanFailure:
    match = re.search(pattern, output, re.MULTILINE)
    if match is None:
        return CommandPlan(commands=(), measured_paths=(), reported_bytes=0, estimate_kind=estimate_kind)
    try:
        reclaimable = max(0, parse_size(match[1]) - retain_bytes)
    except ValueError as error:
        return PlanFailure(message=str(error))
    return CommandPlan(commands=(clean,) if reclaimable else (), measured_paths=(), reported_bytes=reclaimable, estimate_kind=estimate_kind)


def plan_docker(*, kind: DockerKind, clean: tuple[str, ...]) -> CommandPlan | PlanFailure:
    output = query_tool(("docker", "system", "df", "--format", "{{json .}}"))
    if isinstance(output, PlanFailure):
        return output
    rows = [cast(DockerDiskUsageRow, json.loads(line)) for line in output.splitlines() if line.strip()]
    lines = "\n".join(f"""{row["Type"]}={row["Reclaimable"]}""" for row in rows)
    return _reported_plan(output=lines, pattern=rf"""^{kind}=(\S+)""", clean=clean, estimate_kind="approximate", retain_bytes=0)


def plan_journal() -> CommandPlan | PlanFailure:
    output = query_tool(("journalctl", "--disk-usage"))
    if isinstance(output, PlanFailure):
        return output
    return _reported_plan(
        output=output, pattern=r"take up (\S+) in the file system", estimate_kind="at_most",
        clean=("journalctl", f"""--vacuum-size={JOURNAL_RETAIN_MEBIBYTES}M"""), retain_bytes=JOURNAL_RETAIN_MEBIBYTES * 1024**2,
    )


def plan_ollama_model(*, model: str) -> CommandPlan | PlanFailure:
    output = query_tool(("ollama", "list"))
    if isinstance(output, PlanFailure):
        return output
    return _reported_plan(
        output=output, pattern=rf"""^{re.escape(model)}(?::\S+)?\s+\S+\s+(\d+(?:\.\d+)?\s*[kKMGT]?B)\s""", estimate_kind="approximate",
        clean=("ollama", "rm", model), retain_bytes=0,
    )


def plan_brew() -> CommandPlan | PlanFailure:
    output = query_tool(("brew", "cleanup", "--prune=all", "-s", "--dry-run"))
    if isinstance(output, PlanFailure):
        return output
    return _reported_plan(
        output=output, pattern=r"free approximately (\S+) of disk space", estimate_kind="approximate",
        clean=("brew", "cleanup", "--prune=all", "-s"), retain_bytes=0,
    )


def plan_bleachbit(*, executable: str, options: tuple[str, ...]) -> CommandPlan | PlanFailure:
    output = query_tool((executable, "--preview", *options))
    if isinstance(output, PlanFailure):
        return output
    if re.search(r"^Disk space to be recovered: ", output, re.MULTILINE) is None:
        return PlanFailure(message=f"""`{executable} --preview` printed no recovery total""")
    return _reported_plan(
        output=output, pattern=r"^Disk space to be recovered: (\S+)$", estimate_kind="exact",
        clean=(executable, "--clean", *options), retain_bytes=0,
    )
