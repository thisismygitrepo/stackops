from functools import partial

from stackops.scripts.python.helpers.helpers_utils.clean_drive_constants import ALL_PLATFORMS, SEMTOOLS_HUB_MODEL
from stackops.scripts.python.helpers.helpers_utils.clean_drive_models import CleanCategory, CleanTarget, CommandCleanup, PathCleanup, PathGlob
from stackops.scripts.python.helpers.helpers_utils.clean_drive_plans import plan_tool_directory


DEV_TARGETS: tuple[CleanTarget, ...] = (
    CleanTarget(
        key="uv-cache", title="uv package cache", category=CleanCategory.DEV, risk="safe",
        note="Wheels, sources and built packages that uv re-downloads on demand. Runs `uv cache clean`.",
        actions={platform: CommandCleanup(
            tool="uv", install_hint=None, requires_root=False,
            plan=partial(plan_tool_directory, query=("uv", "cache", "dir"), clean=("uv", "cache", "clean"), estimate_kind="exact"),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="bun-cache", title="Bun install cache", category=CleanCategory.DEV, risk="safe",
        note="Packages Bun re-downloads on the next install. Runs `bun pm cache rm`.",
        actions={platform: CommandCleanup(
            tool="bun", install_hint=None, requires_root=False,
            plan=partial(plan_tool_directory, query=("bun", "pm", "cache"), clean=("bun", "pm", "cache", "rm"), estimate_kind="exact"),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="bun-transpiler-cache", title="Bun runtime transpiler cache", category=CleanCategory.DEV, risk="safe",
        note="Transpiled sources that Bun-run tools (qmd among them) cache for faster startup; rebuilt on demand. Outside macOS it sits inside the install cache (bun-cache) unless XDG_CACHE_HOME is set.",
        actions={
            "linux": PathCleanup(globs=(PathGlob("xdg_cache", "bun/@t@"),), excluded_globs=(), min_age_days=None, requires_root=False),
            "darwin": PathCleanup(globs=(PathGlob("xdg_cache", "bun/@t@"), PathGlob("mac_caches", "bun/@t@")), excluded_globs=(), min_age_days=None, requires_root=False),
            "windows": PathCleanup(globs=(PathGlob("xdg_cache", "bun/@t@"),), excluded_globs=(), min_age_days=None, requires_root=False),
        },
    ),
    CleanTarget(
        key="pnpm-store", title="pnpm store (unreferenced packages)", category=CleanCategory.DEV, risk="safe",
        note="Packages no project references any more. Runs `pnpm store prune`; the estimate is the whole store.",
        actions={platform: CommandCleanup(
            tool="pnpm", install_hint=None, requires_root=False,
            plan=partial(plan_tool_directory, query=("pnpm", "store", "path"), clean=("pnpm", "store", "prune"), estimate_kind="at_most"),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="npm-cache", title="npm cache, npx installs and logs", category=CleanCategory.DEV, risk="safe",
        note="npm re-downloads tarballs and npx packages on demand.",
        actions={
            "linux": PathCleanup(globs=(PathGlob("home", ".npm/_cacache"), PathGlob("home", ".npm/_npx"), PathGlob("home", ".npm/_logs")), excluded_globs=(), min_age_days=None, requires_root=False),
            "darwin": PathCleanup(globs=(PathGlob("home", ".npm/_cacache"), PathGlob("home", ".npm/_npx"), PathGlob("home", ".npm/_logs")), excluded_globs=(), min_age_days=None, requires_root=False),
            "windows": PathCleanup(globs=(PathGlob("local_app_data", "npm-cache/_cacache"), PathGlob("local_app_data", "npm-cache/_npx"), PathGlob("local_app_data", "npm-cache/_logs")), excluded_globs=(), min_age_days=None, requires_root=False),
        },
    ),
    CleanTarget(
        key="yarn-cache", title="Yarn caches (classic and berry)", category=CleanCategory.DEV, risk="safe",
        note="Yarn re-downloads packages on demand.",
        actions={
            "linux": PathCleanup(globs=(PathGlob("xdg_cache", "yarn"), PathGlob("home", ".yarn/berry/cache")), excluded_globs=(), min_age_days=None, requires_root=False),
            "darwin": PathCleanup(globs=(PathGlob("mac_caches", "Yarn"), PathGlob("home", ".yarn/berry/cache")), excluded_globs=(), min_age_days=None, requires_root=False),
            "windows": PathCleanup(globs=(PathGlob("local_app_data", "Yarn/Cache"), PathGlob("local_app_data", "Yarn/Berry/cache")), excluded_globs=(), min_age_days=None, requires_root=False),
        },
    ),
    CleanTarget(
        key="pip-cache", title="pip cache", category=CleanCategory.DEV, risk="safe",
        note="pip re-downloads wheels on demand.",
        actions={
            "linux": PathCleanup(globs=(PathGlob("xdg_cache", "pip"),), excluded_globs=(), min_age_days=None, requires_root=False),
            "darwin": PathCleanup(globs=(PathGlob("mac_caches", "pip"),), excluded_globs=(), min_age_days=None, requires_root=False),
            "windows": PathCleanup(globs=(PathGlob("local_app_data", "pip/Cache"),), excluded_globs=(), min_age_days=None, requires_root=False),
        },
    ),
    CleanTarget(
        key="cargo-cache", title="Cargo registry and git caches", category=CleanCategory.DEV, risk="safe",
        note="Crate archives, extracted sources and git checkouts that Cargo fetches again when needed.",
        actions={platform: PathCleanup(
            globs=(PathGlob("cargo_home", "registry/cache"), PathGlob("cargo_home", "registry/src"), PathGlob("cargo_home", "git/checkouts"), PathGlob("cargo_home", "git/db")),
            excluded_globs=(), min_age_days=None, requires_root=False,
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="go-build-cache", title="Go build, test and fuzz cache", category=CleanCategory.DEV, risk="safe",
        note="Compiled packages and cached test results. Runs `go clean -cache -fuzzcache`.",
        actions={platform: CommandCleanup(
            tool="go", install_hint=None, requires_root=False,
            plan=partial(plan_tool_directory, query=("go", "env", "GOCACHE"), clean=("go", "clean", "-cache", "-fuzzcache"), estimate_kind="exact"),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="go-module-cache", title="Go module cache", category=CleanCategory.DEV, risk="caution",
        note="Every downloaded module; builds re-download them. Runs `go clean -modcache`.",
        actions={platform: CommandCleanup(
            tool="go", install_hint=None, requires_root=False,
            plan=partial(plan_tool_directory, query=("go", "env", "GOMODCACHE"), clean=("go", "clean", "-modcache"), estimate_kind="exact"),
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="gradle-cache", title="Gradle caches and wrapper distributions", category=CleanCategory.DEV, risk="caution",
        note="Dependencies and Gradle distributions; the next build re-downloads them.",
        actions={platform: PathCleanup(
            globs=(PathGlob("gradle_home", "caches"), PathGlob("gradle_home", "wrapper/dists")), excluded_globs=(), min_age_days=None, requires_root=False,
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="maven-repository", title="Maven local repository", category=CleanCategory.DEV, risk="caution",
        note="Every downloaded artifact; builds re-download them, and locally installed snapshots are lost.",
        actions={platform: PathCleanup(globs=(PathGlob("home", ".m2/repository"),), excluded_globs=(), min_age_days=None, requires_root=False) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="huggingface-cache", title="Hugging Face hub cache", category=CleanCategory.DEV, risk="caution",
        note="Downloaded models and datasets; they download again on next use, which can be large. The semtools model belongs to seek-models.",
        actions={platform: PathCleanup(
            globs=(PathGlob("hf_home", "hub/*"), PathGlob("hf_home", "xet")), excluded_globs=(PathGlob("hf_home", SEMTOOLS_HUB_MODEL),),
            min_age_days=None, requires_root=False,
        ) for platform in ALL_PLATFORMS},
    ),
    CleanTarget(
        key="playwright-browsers", title="Playwright browsers", category=CleanCategory.DEV, risk="caution",
        note="Browsers that `playwright install` downloads again.",
        actions={
            "linux": PathCleanup(globs=(PathGlob("xdg_cache", "ms-playwright"), PathGlob("xdg_cache", "ms-playwright-go")), excluded_globs=(), min_age_days=None, requires_root=False),
            "darwin": PathCleanup(globs=(PathGlob("mac_caches", "ms-playwright"), PathGlob("mac_caches", "ms-playwright-go")), excluded_globs=(), min_age_days=None, requires_root=False),
            "windows": PathCleanup(globs=(PathGlob("local_app_data", "ms-playwright"), PathGlob("local_app_data", "ms-playwright-go")), excluded_globs=(), min_age_days=None, requires_root=False),
        },
    ),
    CleanTarget(
        key="puppeteer-browsers", title="Puppeteer browsers", category=CleanCategory.DEV, risk="caution",
        note="Browsers Puppeteer downloads again on its next install.",
        actions={platform: PathCleanup(globs=(PathGlob("home", ".cache/puppeteer"),), excluded_globs=(), min_age_days=None, requires_root=False) for platform in ALL_PLATFORMS},
    ),
)
