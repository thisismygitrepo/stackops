import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from stackops.scripts.python.helpers.helpers_agents.agents_iter_constants import HERDR_PROTOCOL, HERDR_VERSION
from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import PaneId, TabId, TerminalId, WorkspaceId
from stackops.utils.accessories import get_repo_root


type JsonObject = dict[str, object]

RECORD_SCHEMA_VERSION = 1
_RUN_KEYS = frozenset(("schema_version", "herdr_version", "herdr_protocol", "herdr_session", "workspace_id", "workspace_label"))
_HANDOFF_KEYS = frozenset(
    (
        "schema_version",
        "herdr_version",
        "herdr_protocol",
        "herdr_session",
        "workspace_id",
        "source_iteration",
        "source_tab_id",
        "successor_iteration",
        "successor_tab_id",
        "successor_pane_id",
        "successor_terminal_id",
        "successor_agent_name",
        "accepted_revision",
    )
)


@dataclass(frozen=True, slots=True)
class IterationHandoff:
    herdr_session: str
    workspace_id: WorkspaceId
    source_iteration: int
    source_tab_id: TabId
    successor_iteration: int
    successor_tab_id: TabId
    successor_pane_id: PaneId
    successor_terminal_id: TerminalId
    successor_agent_name: str
    accepted_revision: int


@dataclass(frozen=True, slots=True)
class IterRunManifest:
    herdr_session: str
    workspace_id: WorkspaceId
    workspace_label: str


def resolve_clean_repo_root(*, cwd: Path) -> Path:
    repo_root = get_repo_root(cwd)
    if repo_root is None:
        raise RuntimeError(f"AgentOps clean requires a Git repository; none contains {cwd.resolve(strict=False)}.")
    return repo_root.resolve(strict=True)


def current_herdr_session() -> str:
    session = os.environ.get("HERDR_SESSION")
    if session is None:
        return "default"
    if session == "":
        raise RuntimeError("HERDR_SESSION must not be empty.")
    return session


def load_iteration_handoffs(*, repo_root: Path, workspace_id: WorkspaceId, workspace_label: str) -> dict[int, IterationHandoff]:
    if not workspace_label.startswith("iter-") or workspace_label.removeprefix("iter-") == "":
        raise ValueError(f"Herdr workspace {workspace_label!r} is not a current AgentOps iteration workspace.")
    run_path = repo_root.joinpath(".ai", "agentops", "iterations", workspace_label.removeprefix("iter-"))
    if not run_path.exists():
        return {}
    if run_path.is_symlink() or not run_path.is_dir():
        raise RuntimeError(f"AgentOps iteration run path must be a real directory: {run_path}")
    manifest = load_iter_run_manifest(run_path=run_path)
    if manifest is None:
        return {}
    active_session = current_herdr_session()
    if manifest.herdr_session != active_session:
        raise RuntimeError(
            f"AgentOps run belongs to Herdr session {manifest.herdr_session!r}, not {active_session!r}: {run_path.joinpath('run.json')}"
        )
    if manifest.workspace_label != workspace_label:
        raise RuntimeError(f"AgentOps run manifest label does not match {workspace_label!r}: {run_path.joinpath('run.json')}")
    if manifest.workspace_id != workspace_id:
        raise RuntimeError(f"AgentOps run manifest workspace ID does not match {workspace_id!r}: {run_path.joinpath('run.json')}")

    handoffs: dict[int, IterationHandoff] = {}
    for iteration_path in sorted(run_path.iterdir(), key=lambda path: path.name):
        iteration = _iteration_directory_number(path=iteration_path)
        if iteration is None:
            continue
        receipt_path = iteration_path.joinpath("handoff.json")
        if not receipt_path.exists():
            continue
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise RuntimeError(f"AgentOps handoff receipt must be a real file: {receipt_path}")
        handoff = _parse_handoff(path=receipt_path)
        if handoff.source_iteration != iteration:
            raise RuntimeError(f"AgentOps handoff source iteration {handoff.source_iteration} does not match {iteration_path.name}.")
        if iteration in handoffs:
            raise RuntimeError(f"AgentOps iteration run contains duplicate handoff {iteration:03d}.")
        if handoff.herdr_session != manifest.herdr_session or handoff.workspace_id != manifest.workspace_id:
            raise RuntimeError(f"AgentOps handoff workspace does not match run.json: {receipt_path}")
        handoffs[iteration] = handoff
    return handoffs


def load_iter_run_manifest(*, run_path: Path) -> IterRunManifest | None:
    manifest_path = run_path.joinpath("run.json")
    if not manifest_path.exists():
        return None
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError(f"AgentOps run manifest must be a real file: {manifest_path}")
    value = _load_json_object(path=manifest_path, record_name="run manifest")
    if frozenset(value) != _RUN_KEYS:
        raise RuntimeError(f"AgentOps run manifest has the wrong fields: {manifest_path}")
    _validate_current_header(mapping=value, path=manifest_path)
    return IterRunManifest(
        herdr_session=_required_string(mapping=value, key="herdr_session"),
        workspace_id=WorkspaceId(_required_string(mapping=value, key="workspace_id")),
        workspace_label=_required_string(mapping=value, key="workspace_label"),
    )


def _iteration_directory_number(*, path: Path) -> int | None:
    if path.is_symlink() or not path.is_dir() or not path.name.startswith("iter-"):
        return None
    digits = path.name.removeprefix("iter-")
    if len(digits) < 3 or not digits.isascii() or not digits.isdecimal():
        return None
    iteration = int(digits)
    return iteration if iteration > 0 else None


def _parse_handoff(*, path: Path) -> IterationHandoff:
    value = _load_json_object(path=path, record_name="handoff receipt")
    if frozenset(value) != _HANDOFF_KEYS:
        raise RuntimeError(f"AgentOps handoff receipt has the wrong fields: {path}")
    _validate_current_header(mapping=value, path=path)
    return IterationHandoff(
        herdr_session=_required_string(mapping=value, key="herdr_session"),
        workspace_id=WorkspaceId(_required_string(mapping=value, key="workspace_id")),
        source_iteration=_required_int(mapping=value, key="source_iteration", minimum=1),
        source_tab_id=TabId(_required_string(mapping=value, key="source_tab_id")),
        successor_iteration=_required_int(mapping=value, key="successor_iteration", minimum=1),
        successor_tab_id=TabId(_required_string(mapping=value, key="successor_tab_id")),
        successor_pane_id=PaneId(_required_string(mapping=value, key="successor_pane_id")),
        successor_terminal_id=TerminalId(_required_string(mapping=value, key="successor_terminal_id")),
        successor_agent_name=_required_string(mapping=value, key="successor_agent_name"),
        accepted_revision=_required_int(mapping=value, key="accepted_revision", minimum=0),
    )


def _load_json_object(*, path: Path, record_name: str) -> JsonObject:
    try:
        payload = cast(object, json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Failed to read current AgentOps {record_name} {path}: {error}") from error
    if not isinstance(payload, dict):
        raise RuntimeError(f"AgentOps {record_name} must contain a JSON object: {path}")
    return cast(JsonObject, payload)


def _validate_current_header(*, mapping: JsonObject, path: Path) -> None:
    schema_version = _required_int(mapping=mapping, key="schema_version", minimum=1)
    version = _required_string(mapping=mapping, key="herdr_version")
    protocol = _required_int(mapping=mapping, key="herdr_protocol", minimum=0)
    if schema_version != RECORD_SCHEMA_VERSION or version != HERDR_VERSION or protocol != HERDR_PROTOCOL:
        raise RuntimeError(f"AgentOps record does not use the current Herdr contract: {path}")


def _required_string(*, mapping: JsonObject, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or value == "":
        raise RuntimeError(f"AgentOps record field {key!r} must be a non-empty string.")
    return value


def _required_int(*, mapping: JsonObject, key: str, minimum: int) -> int:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise RuntimeError(f"AgentOps record field {key!r} must be an integer >= {minimum}.")
    return value
