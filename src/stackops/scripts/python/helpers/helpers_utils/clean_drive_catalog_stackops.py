from functools import partial

from stackops.scripts.python.helpers.helpers_seek.semantic.constants import (
    CK_INDEX_DIR,
    GREPAI_CONFIG_RELATIVE_PATH,
    QMD_INDEX_DIR,
    QMD_LOCAL_CONFIG_RELATIVE_PATHS,
    SEMTOOLS_WORKSPACE_PREFIX,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import (
    ALL_PLATFORMS,
    CK_INDEX_MARKER,
    GREPAI_OLLAMA_MODEL,
    SEMTOOLS_HUB_MODEL,
    STACKOPS_SCRATCH_ENTRIES,
    STACKOPS_TEMP_PATTERNS,
    STALE_TEMP_DAYS,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import (
    Anchor,
    CleanCategory,
    CleanTarget,
    CommandCleanup,
    PathCleanup,
    PathGlob,
    Platform,
    ProjectCleanup,
    ProjectMarker,
)
from stackops.scripts.python.helpers.helpers_utils.clean_drive_plans import plan_ollama_model


SEEK_STORE_GLOBS: tuple[PathGlob, ...] = (
    PathGlob("xdg_cache", "ck/models"), PathGlob("xdg_cache", "ck/rerankers"), PathGlob("xdg_cache", "qmd/models"),
    PathGlob("hf_home", SEMTOOLS_HUB_MODEL), PathGlob("home", f""".semtools/workspaces/{SEMTOOLS_WORKSPACE_PREFIX}*"""),
    PathGlob("xdg_config", "qmd/trusted.json*"),
)
SEEK_STORE_GLOBS_BY_PLATFORM: dict[Platform, tuple[PathGlob, ...]] = {
    "linux": SEEK_STORE_GLOBS,
    "darwin": SEEK_STORE_GLOBS,
    "windows": (*SEEK_STORE_GLOBS, PathGlob("local_app_data", "ck/cache/models"), PathGlob("local_app_data", "ck/cache/rerankers")),
}
RCLONE_CACHE_ANCHORS: dict[Platform, Anchor] = {"linux": "xdg_cache", "darwin": "mac_caches", "windows": "local_app_data"}

STACKOPS_TARGETS: tuple[CleanTarget, ...] = (
    CleanTarget(
        key="stackops-scratch", title="StackOps scratch files and logs", category=CleanCategory.STACKOPS, risk="safe",
        note=f"""Generated scripts, picker files, installer downloads and logs, unzip folders and the vault cache under ~/tmp_results; background-service logs in ~/.cache/stackops; StackOps leftovers in the temp folder; temporary browser profiles and `--tmp` profile copies. Only entries untouched for {STALE_TEMP_DAYS} days, so running jobs and browsers keep theirs.""",
        actions={platform: PathCleanup(
            globs=(
                *(PathGlob("home", f"""tmp_results/{directory}/{entries}""") for directory, entries in STACKOPS_SCRATCH_ENTRIES.items()),
                PathGlob("home", ".cache/stackops/*/*"), PathGlob("home", "data/browsers-profiles/*/*/.tmp/*"),
                *(PathGlob("temp", pattern) for pattern in STACKOPS_TEMP_PATTERNS),
                PathGlob("filesystem_root", "tmp/stackops_agent_impl_interactive"),
            ),
            excluded_globs=(), min_age_days=STALE_TEMP_DAYS, requires_root=False,
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="stackops-tmp-results", title="Everything else in ~/tmp_results", category=CleanCategory.STACKOPS, risk="caution",
        note="Remote-job state, temp projects, repo-linked tmp data and any task output you or your agents parked there. Not regenerable.",
        actions={platform: PathCleanup(
            globs=(PathGlob("home", "tmp_results/*"),),
            excluded_globs=tuple(PathGlob("home", f"""tmp_results/{directory}""") for directory in STACKOPS_SCRATCH_ENTRIES),
            min_age_days=None, requires_root=False,
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="stackops-config-leftovers", title="StackOps staging and bundles in ~/.config/stackops", category=CleanCategory.STACKOPS, risk="caution",
        note="Repo-sync staging copies (remote, integration), offline-installer bundles and the Slidev scaffold. The command that made them rebuilds them; an unresolved sync merge is lost.",
        actions={platform: PathCleanup(
            globs=(
                PathGlob("home", ".config/stackops/remote/*"), PathGlob("home", ".config/stackops/integration/*"),
                PathGlob("home", ".config/stackops/offline_installers/*"), PathGlob("home", ".config/stackops/.cache/*"),
            ),
            excluded_globs=(), min_age_days=None, requires_root=False,
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="stackops-cloud-mount-cache", title="Cloud mount cache (rclone VFS)", category=CleanCategory.STACKOPS, risk="caution",
        note="Files rclone caches for `cloud mount`. Unmount first: anything written through a mount but not uploaded yet is lost.",
        actions={platform: PathCleanup(
            globs=(PathGlob(anchor, "rclone/vfs/*"), PathGlob(anchor, "rclone/vfsMeta/*")), excluded_globs=(), min_age_days=None, requires_root=False,
        ) for platform, anchor in RCLONE_CACHE_ANCHORS.items()},
    ),
    CleanTarget(
        key="seek-ck-index", title="Semantic seek indexes: ck (.ck)", category=CleanCategory.STACKOPS, risk="caution",
        note="Index folders `seek --semantic -b ck` leaves in searched directories; the next search re-embeds the tree.",
        actions={platform: ProjectCleanup(
            directory_names=(CK_INDEX_DIR.name,), marker=ProjectMarker(relation="child", name=CK_INDEX_MARKER),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="seek-grepai-index", title="Semantic seek indexes: grepai (.grepai)", category=CleanCategory.STACKOPS, risk="caution",
        note="Index folders `seek --semantic -b grepai` leaves in searched directories; the next search re-initialises and re-embeds. Hand-edited config.yaml settings are lost.",
        actions={platform: ProjectCleanup(
            directory_names=(GREPAI_CONFIG_RELATIVE_PATH.parent.name,), marker=ProjectMarker(relation="child", name=GREPAI_CONFIG_RELATIVE_PATH.name),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="seek-qmd-index", title="Semantic seek indexes: qmd (.qmd)", category=CleanCategory.STACKOPS, risk="caution",
        note="Index folders `seek --semantic -b qmd` leaves in searched directories; the next search re-initialises and re-embeds. Hand-edited index.yml collections are lost.",
        actions={platform: ProjectCleanup(
            directory_names=(QMD_INDEX_DIR.name,), marker=ProjectMarker(relation="child", name=QMD_LOCAL_CONFIG_RELATIVE_PATHS[0].name),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="seek-models", title="Semantic seek models, workspaces and trust records", category=CleanCategory.STACKOPS, risk="caution",
        note="ck, qmd and semtools embedding models (qmd about 1.6 GB), semtools `seek-*` workspaces and qmd's trust records for local indexes; downloaded or rebuilt on the next `seek --semantic`. Re-approve your own hooked .qmd configs with `qmd trust`.",
        actions={platform: PathCleanup(globs=globs, excluded_globs=(), min_age_days=None, requires_root=False) for platform, globs in SEEK_STORE_GLOBS_BY_PLATFORM.items()},
    ),
    CleanTarget(
        key="seek-grepai-ollama-model", title=f"""Semantic seek model for grepai (Ollama {GREPAI_OLLAMA_MODEL})""", category=CleanCategory.STACKOPS, risk="caution",
        note=f"""The embedding model the grepai backend needs. Runs `ollama rm {GREPAI_OLLAMA_MODEL}`; pull it again before the next grepai search. Ollama must be running.""",
        actions={platform: CommandCleanup(
            tool="ollama", install_hint=None, requires_root=False, plan=partial(plan_ollama_model, model=GREPAI_OLLAMA_MODEL),
        ) for platform in ALL_PLATFORMS},
    ),
)
