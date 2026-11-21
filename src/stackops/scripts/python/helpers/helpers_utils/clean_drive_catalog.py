from stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_dev import DEV_TARGETS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_stackops import STACKOPS_TARGETS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_catalog_system import CONTAINER_TARGETS, SYSTEM_TARGETS, TRASH_TARGETS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import ALL_PLATFORMS
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import CleanCategory, CleanTarget, ProjectCleanup, ProjectMarker


PROJECT_TARGETS: tuple[CleanTarget, ...] = (
    CleanTarget(
        key="ai-scratch", title="AI agent scratch folders (.ai)", category=CleanCategory.PROJECTS, risk="caution",
        note="Every `.ai` folder under the search roots: agents' temp scripts, harnesses and linter reports. Not regenerable.",
        actions={platform: ProjectCleanup(directory_names=(".ai",), marker=None) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="python-tool-caches", title="Python bytecode and tool caches", category=CleanCategory.PROJECTS, risk="safe",
        note="__pycache__, .mypy_cache, .ruff_cache and .pytest_cache folders; tools rebuild them.",
        actions={platform: ProjectCleanup(directory_names=("__pycache__", ".mypy_cache", ".ruff_cache", ".pytest_cache"), marker=None) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="node-modules", title="Project node_modules", category=CleanCategory.PROJECTS, risk="caution",
        note="node_modules next to a package.json; reinstall with your package manager.",
        actions={platform: ProjectCleanup(directory_names=("node_modules",), marker=ProjectMarker(relation="sibling", name="package.json")) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="python-venvs", title="Project virtual environments (.venv)", category=CleanCategory.PROJECTS, risk="caution",
        note=".venv folders containing pyvenv.cfg; recreate with `uv sync`. Anything installed by hand is lost.",
        actions={platform: ProjectCleanup(directory_names=(".venv",), marker=ProjectMarker(relation="child", name="pyvenv.cfg")) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="rust-targets", title="Rust build output (target)", category=CleanCategory.PROJECTS, risk="caution",
        note="target folders next to a Cargo.toml; the next build recompiles everything.",
        actions={platform: ProjectCleanup(directory_names=("target",), marker=ProjectMarker(relation="sibling", name="Cargo.toml")) for platform in ALL_PLATFORMS},
    ),
)

CATALOG: tuple[CleanTarget, ...] = (*CONTAINER_TARGETS, *DEV_TARGETS, *SYSTEM_TARGETS, *TRASH_TARGETS, *PROJECT_TARGETS, *STACKOPS_TARGETS)
CATALOG_BY_KEY: dict[str, CleanTarget] = {target.key: target for target in CATALOG}
assert len(CATALOG_BY_KEY) == len(CATALOG), "clean-drive target keys must be unique"
