import platform as platform_module
import shutil
import time
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog import CATALOG, CATALOG_BY_KEY
from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import RISK_ORDER, SCAN_WORKERS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import (
    CatalogAction,
    CleanCategory,
    CleanTarget,
    CleanupAction,
    CommandCleanup,
    Estimate,
    EstimateKind,
    MeasuredPath,
    PathCleanup,
    PlanFailure,
    Platform,
    ProjectCleanup,
    Risk,
    TargetScan,
    ToolWithPathFallback,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_paths import expand_globs
from stackops.scripts.python.helpers.helpers_utils.clean_drive_projects import find_project_entries
from stackops.scripts.python.helpers.helpers_utils.clean_drive_usage import combine_usages, measure_path, reclaimable_bytes


type ScopedTarget = tuple[CleanTarget, CleanupAction]


def current_platform() -> Platform:
    match platform_module.system():
        case "Linux":
            return "linux"
        case "Darwin":
            return "darwin"
        case "Windows":
            return "windows"
        case other:
            raise RuntimeError(f"""clean-drive does not support {other}""")


def requires_root(action: CleanupAction) -> bool:
    return not isinstance(action, ProjectCleanup) and action.requires_root


def resolve_action(action: CatalogAction) -> CleanupAction:
    match action:
        case ToolWithPathFallback():
            return action.tool if shutil.which(action.tool.tool) is not None else action.fallback
        case PathCleanup() | CommandCleanup() | ProjectCleanup():
            return action


def select_scope(
    *, platform: Platform, targets: Sequence[str], categories: Sequence[CleanCategory], excludes: Sequence[str], max_risk: Risk, allow_root: bool,
) -> tuple[list[ScopedTarget], set[str]]:
    unknown = [key for key in (*targets, *excludes) if key not in CATALOG_BY_KEY]
    if unknown:
        raise ValueError(f"""Unknown target(s): {", ".join(unknown)}. Known targets: {", ".join(CATALOG_BY_KEY)}""")
    unavailable = [key for key in targets if platform not in CATALOG_BY_KEY[key].actions]
    if unavailable:
        raise ValueError(f"""Not available on {platform}: {", ".join(unavailable)}""")
    scope = [
        (target, resolve_action(target.actions[platform])) for target in CATALOG
        if platform in target.actions and (not targets or target.key in targets)
        and (not categories or target.category in categories) and target.key not in excludes
    ]
    auto_keys = {
        target.key for target, action in scope
        if targets or (RISK_ORDER[target.risk] <= RISK_ORDER[max_risk] and (allow_root or not requires_root(action)))
    }
    return scope, auto_keys


def combine_kinds(kinds: set[EstimateKind]) -> EstimateKind:
    if kinds <= {"exact"}:
        return "exact"
    if kinds <= {"exact", "at_least"}:
        return "at_least"
    if kinds <= {"exact", "at_most"}:
        return "at_most"
    return "approximate"


def _scan_paths(*, target: CleanTarget, action: PathCleanup | ProjectCleanup, paths: list[Path], min_age_days: int | None) -> TargetScan:
    cutoff = None if min_age_days is None else time.time() - min_age_days * 86_400
    measured = [(path, measure_path(path)) for path in paths]
    kept = [(path, usage) for path, usage in measured if cutoff is None or usage.newest_mtime < cutoff]
    usage = combine_usages(usage for _path, usage in kept)
    return TargetScan(
        target=target, action=action, status="ready" if kept else "empty", message=f"""{len(kept)} path(s)""",
        paths=tuple(sorted((MeasuredPath(path=path, bytes=reclaimable_bytes(entry)) for path, entry in kept), key=lambda item: -item.bytes)),
        commands=(), usage=usage, reported_bytes=None,
        estimate=Estimate(bytes=reclaimable_bytes(usage), kind="at_least" if usage.denied else "exact"),
    )


def scan_target(*, target: CleanTarget, action: CleanupAction, project_entries: dict[str, list[Path]]) -> TargetScan:
    match action:
        case PathCleanup():
            excluded = set(expand_globs(action.excluded_globs))
            paths = [path for path in expand_globs(action.globs) if path not in excluded]
            return _scan_paths(target=target, action=action, paths=paths, min_age_days=action.min_age_days)
        case ProjectCleanup():
            return _scan_paths(target=target, action=action, paths=project_entries[target.key], min_age_days=None)
        case CommandCleanup():
            unknown = Estimate(bytes=None, kind="approximate")
            if shutil.which(action.tool) is None:
                hint = "" if action.install_hint is None else f"""; {action.install_hint}"""
                return TargetScan(
                    target=target, action=action, status="missing_tool", message=f"""{action.tool} not found{hint}""",
                    paths=(), commands=(), usage=None, reported_bytes=None, estimate=unknown,
                )
            plan = action.plan()
            if isinstance(plan, PlanFailure):
                return TargetScan(
                    target=target, action=action, status="failed", message=plan.message,
                    paths=(), commands=(), usage=None, reported_bytes=None, estimate=unknown,
                )
            measured = [(path, measure_path(path)) for path in plan.measured_paths]
            usage = combine_usages(entry for _path, entry in measured) if measured else None
            estimate_bytes = reclaimable_bytes(usage) if usage is not None else plan.reported_bytes
            kind = "at_least" if usage is not None and usage.denied else plan.estimate_kind
            return TargetScan(
                target=target, action=action, status="ready" if plan.commands and estimate_bytes != 0 else "empty",
                message=" && ".join(" ".join(command) for command in plan.commands),
                paths=tuple(MeasuredPath(path=path, bytes=reclaimable_bytes(entry)) for path, entry in measured),
                commands=plan.commands, usage=usage, reported_bytes=plan.reported_bytes, estimate=Estimate(bytes=estimate_bytes, kind=kind),
            )


def scan_scope(*, scope: list[ScopedTarget], roots: tuple[Path, ...]) -> list[TargetScan]:
    project_cleanups = {target.key: action for target, action in scope if isinstance(action, ProjectCleanup)}
    project_entries = find_project_entries(roots=roots, cleanups=project_cleanups) if project_cleanups else {}
    with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as pool:
        futures = [pool.submit(scan_target, target=target, action=action, project_entries=project_entries) for target, action in scope]
        return [future.result() for future in futures]


def total_estimate(scans: Sequence[TargetScan]) -> Estimate:
    usages = [scan.usage for scan in scans if scan.usage is not None]
    reported = [scan.reported_bytes for scan in scans if scan.usage is None and scan.reported_bytes is not None]
    unknown = any(scan.estimate.bytes is None for scan in scans)
    kinds: set[EstimateKind] = {scan.estimate.kind for scan in scans}
    if unknown:
        kinds.add("at_least")
    return Estimate(bytes=reclaimable_bytes(combine_usages(usages)) + sum(reported), kind=combine_kinds(kinds))
