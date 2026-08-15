import os
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from stat import S_IMODE

from stackops.utils.installer_utils.github_commit_dates_constants import NEW_OUTPUT_FILE_MODE


@dataclass(frozen=True, slots=True)
class TextOutput:
    path: Path
    content: str


@dataclass(frozen=True, slots=True)
class _StagedTextOutput:
    path: Path
    temporary_path: Path


def _stage_text_output(output: TextOutput) -> _StagedTextOutput:
    output.path.parent.mkdir(parents=True, exist_ok=True)
    if output.path.exists() and not output.path.is_file():
        raise OSError(f"Output path is not a file: {output.path}")
    output_mode = S_IMODE(output.path.stat().st_mode) if output.path.exists() else NEW_OUTPUT_FILE_MODE
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.path.name}.", dir=output.path.parent)
    temporary_path = Path(temporary_name)
    try:
        os.chmod(temporary_path, output_mode)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            descriptor = -1
            stream.write(output.content)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        temporary_path.unlink(missing_ok=True)
        raise
    return _StagedTextOutput(path=output.path, temporary_path=temporary_path)


def commit_text_outputs(outputs: Sequence[TextOutput]) -> None:
    staged_outputs: list[_StagedTextOutput] = []
    try:
        for output in outputs:
            staged_outputs.append(_stage_text_output(output=output))
        for staged_output in staged_outputs:
            os.replace(staged_output.temporary_path, staged_output.path)
    finally:
        for staged_output in staged_outputs:
            staged_output.temporary_path.unlink(missing_ok=True)
