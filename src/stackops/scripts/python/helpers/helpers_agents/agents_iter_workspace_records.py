from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_iter_models import HerdrSnapshot, HerdrWorkspace, TabId
from stackops.scripts.python.helpers.helpers_agents.agents_iter_records import IterationHandoff, load_iteration_handoffs
from stackops.utils.accessories import get_repo_root


@dataclass(frozen=True, slots=True)
class IterWorkspaceRecords:
    repo_root: Path
    handoffs: Mapping[int, IterationHandoff]


def load_iter_workspace_records(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> IterWorkspaceRecords:
    repo_root = resolve_iter_workspace_repo_root(snapshot=snapshot, workspace=workspace)
    handoffs = load_iteration_handoffs(repo_root=repo_root, workspace_id=workspace.workspace_id, workspace_label=workspace.label)
    return IterWorkspaceRecords(repo_root=repo_root, handoffs=handoffs)


def resolve_iter_workspace_repo_root(*, snapshot: HerdrSnapshot, workspace: HerdrWorkspace) -> Path:
    managed_tab_ids = _managed_iter_tab_ids(snapshot=snapshot, workspace=workspace)
    workspace_agents = tuple(agent for agent in snapshot.agents if agent.workspace_id == workspace.workspace_id and agent.tab_id in managed_tab_ids)
    repo_roots: set[Path] = set()
    unusable_locations: list[str] = []
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
            repo_root = get_repo_root(resolved_candidate)
            if repo_root is None:
                unusable_locations.append(f"{agent.name or agent.tab_id}.{field_name}={raw_path!r} is not in a Git repository")
                continue
            repo_roots.add(repo_root.resolve(strict=True))

    workspace_identity = f"{workspace.label!r} ({workspace.workspace_id})"
    if len(repo_roots) == 1:
        return next(iter(repo_roots))
    if len(repo_roots) > 1:
        roots = ", ".join(str(path) for path in sorted(repo_roots))
        raise RuntimeError(f"Herdr iter workspace {workspace_identity} resolves to multiple Git repositories: {roots}")
    detail = "; ".join(unusable_locations) if len(unusable_locations) > 0 else "no managed iteration agent reported a cwd"
    raise RuntimeError(f"Cannot resolve the Git repository for Herdr iter workspace {workspace_identity}: {detail}.")


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
