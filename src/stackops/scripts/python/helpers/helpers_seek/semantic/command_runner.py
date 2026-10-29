import os
import shlex
import subprocess
import sys
from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.backend_names import SemanticBackend
from stackops.scripts.python.helpers.helpers_seek.semantic.semantic_models import SemanticFailure, SemanticStage


def run_backend_command(
    backend: SemanticBackend,
    stage: SemanticStage,
    command: list[str],
    cwd: Path,
    extra_env: dict[str, str],
    accepted_exit_codes: tuple[int, ...],
    capture_stdout: bool,
) -> str | SemanticFailure:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env={**os.environ, **extra_env},
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE if capture_stdout else sys.stderr,
        stderr=sys.stderr,
        encoding="utf-8",
        check=False,
    )
    if completed.returncode not in accepted_exit_codes:
        return SemanticFailure(
            backend=backend,
            stage=stage,
            message=f"""{shlex.join(command)} exited with code {completed.returncode}""",
        )
    return completed.stdout if capture_stdout else ""
