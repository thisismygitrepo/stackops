from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import HerdrSnapshot, HerdrWorkspace, TabId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import (
    IterationHandoff,
    load_iter_run_manifest,
    load_iteration_handoffs,
    parse_iter_workspace_slug,
    validate_iter_run_manifest,
)


@dataclass(frozen=True, slots=True)
class IterWorkspaceRecords:
    run_path: Path
    handoffs: Mapping[int, IterationHandoff]


def load_iter_workspace_records(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> IterWorkspaceRecords:
    run_path = resolve_iter_workspace_run_path(snapshot=snapshot, workspace=workspace)
    handoffs = load_iteration_handoffs(run_path=run_path, workspace_id=workspace.workspace_id, workspace_label=workspace.label)
    return IterWorkspaceRecords(run_path=run_path, handoffs=handoffs)


def resolve_iter_workspace_run_path(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> Path:
    managed_tab_ids = _managed_iter_tab_ids(snapshot=snapshot, workspace=workspace)
    workspace_agents = tuple(agent for agent in snapshot.agents if agent.workspace_id == workspace.workspace_id and agent.tab_id in managed_tab_ids)
    run_paths: set[Path] = set()
    searched_directories: set[Path] = set()
    unusable_locations: list[str] = []
    inspected_run_paths: set[Path] = set()
    run_slug = parse_iter_workspace_slug(workspace_label=workspace.label)
    for agent in workspace_agents:
        for field_name, raw_path in (("cwd", agent.cwd), ("foreground_cwd", agent.foreground_cwd)):
            if raw_path is None:
                continue
            candidate = Path(raw_path).expanduser()
            if not candidate.is_absolute():
                unusable_locations.append(f"{agent.name or agent.tab_id}.{field_name}={raw_path!r} is not absolute")
                continue
            try:
                resolved_candidate = candidate.resolve(strict=True)
            except OSError:
                unusable_locations.append(f"{agent.name or agent.tab_id}.{field_name}={raw_path!r} does not exist")
                continue
            if not resolved_candidate.is_dir():
                unusable_locations.append(f"{agent.name or agent.tab_id}.{field_name}={raw_path!r} is not a directory")
                continue
            searched_directories.add(resolved_candidate)
            for project_root in (resolved_candidate, *resolved_candidate.parents):
                agentops_root = project_root.joinpath(".ai", "agentops")
                iterations_root = agentops_root.joinpath("iterations")
                run_path = iterations_root.joinpath(run_slug)
                if run_path in inspected_run_paths or not run_path.joinpath("run.json").exists():
                    continue
                inspected_run_paths.add(run_path)
                if any(path.is_symlink() for path in (project_root.joinpath(".ai"), agentops_root, iterations_root, run_path)):
                    raise RuntimeError(f"Refusing symlinked AgentOps record ancestry: {run_path}")
                manifest = load_iter_run_manifest(run_path=run_path)
                if manifest is None:
                    continue
                validate_iter_run_manifest(
                    manifest=manifest,
                    manifest_path=run_path.joinpath("run.json"),
                    workspace_id=workspace.workspace_id,
                    workspace_label=workspace.label,
                )
                run_paths.add(run_path.resolve(strict=True))

    workspace_identity = f"{workspace.label!r} ({workspace.workspace_id})"
    if len(run_paths) == 1:
        return next(iter(run_paths))
    if len(run_paths) > 1:
        paths = ", ".join(str(path) for path in sorted(run_paths))
        raise RuntimeError(f"Herdr iter workspace {workspace_identity} resolves to multiple AgentOps runs: {paths}")
    searched = ", ".join(str(path) for path in sorted(searched_directories)) or "none"
    unusable = f" Unusable Herdr paths: {'; '.join(unusable_locations)}." if len(unusable_locations) > 0 else ""
    raise RuntimeError(f"Cannot locate AgentOps records for Herdr iter workspace {workspace_identity}. Searched from: {searched}.{unusable}")


def _managed_iter_tab_ids(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> frozenset[TabId]:
    prefix = f"{workspace.label}-"
    managed_tab_ids: set[TabId] = set()
    for tab in snapshot.tabs:
        if tab.workspace_id != workspace.workspace_id or not tab.label.startswith(prefix):
            continue
        digits = tab.label.removeprefix(prefix)
        if len(digits) >= 3 and digits.isascii() and digits.isdecimal() and int(digits) > 0:
            managed_tab_ids.add(tab.tab_id)
    return frozenset(managed_tab_ids)
