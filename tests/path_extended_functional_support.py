from __future__ import annotations

from collections.abc import Callable
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
import os
from pathlib import Path
import subprocess
from typing import Literal
import zipfile


@dataclass(frozen=True)
class CallOutcome:
    value: object | None
    exception_type: type[BaseException] | None
    exception_text: str | None
    stdout: str


@dataclass(frozen=True)
class SnapshotEntry:
    rel_path: str
    kind: Literal["dir", "file", "symlink"]
    payload: bytes | str | None


def capture_call(call: Callable[[], object]) -> CallOutcome:
    stdout_buffer = StringIO()
    with redirect_stdout(stdout_buffer):
        try:
            value = call()
        except BaseException as exc:  # noqa: BLE001
            return CallOutcome(
                value=None,
                exception_type=type(exc),
                exception_text=str(exc),
                stdout=stdout_buffer.getvalue(),
            )
    return CallOutcome(value=value, exception_type=None, exception_text=None, stdout=stdout_buffer.getvalue())


def normalize_text(text: str, root: Path | None) -> str:
    if root is None:
        return text
    normalized = text
    replacements = sorted({str(root), root.as_posix(), root.as_uri()}, key=len, reverse=True)
    for replacement in replacements:
        normalized = normalized.replace(replacement, "<ROOT>")
    return normalized


def normalize_value(value: object, root: Path | None) -> object:
    if isinstance(value, Path):
        return normalize_text(str(value), root)
    if isinstance(value, str):
        return normalize_text(value, root)
    if isinstance(value, list):
        return [normalize_value(item, root) for item in value]
    if isinstance(value, tuple):
        return tuple(normalize_value(item, root) for item in value)
    if isinstance(value, subprocess.CompletedProcess):
        return {
            "args": normalize_value(value.args, root),
            "returncode": value.returncode,
            "stdout": normalize_value(value.stdout, root),
            "stderr": normalize_value(value.stderr, root),
        }
    if isinstance(value, zipfile.Path):
        return {
            "filename": normalize_text(str(value.root.filename), root),
            "at": value.at,
        }
    return value


def assert_matching_outcomes(
    original: CallOutcome,
    functional: CallOutcome,
    *,
    original_root: Path | None = None,
    functional_root: Path | None = None,
) -> None:
    assert original.exception_type is functional.exception_type
    assert normalize_text(original.exception_text or "", original_root) == normalize_text(functional.exception_text or "", functional_root)
    assert normalize_text(original.stdout, original_root) == normalize_text(functional.stdout, functional_root)
    assert normalize_value(original.value, original_root) == normalize_value(functional.value, functional_root)


def snapshot_tree(root: Path) -> tuple[SnapshotEntry, ...]:
    if not root.exists():
        return ()
    entries: list[SnapshotEntry] = []
    for path in sorted(root.rglob("*"), key=lambda candidate: candidate.as_posix()):
        rel_path = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries.append(SnapshotEntry(rel_path=rel_path, kind="symlink", payload=os.readlink(path)))
            continue
        if path.is_dir():
            entries.append(SnapshotEntry(rel_path=rel_path, kind="dir", payload=None))
            continue
        entries.append(SnapshotEntry(rel_path=rel_path, kind="file", payload=path.read_bytes()))
    return tuple(entries)
