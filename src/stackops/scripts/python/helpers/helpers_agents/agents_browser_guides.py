from dataclasses import dataclass
from pathlib import Path
from typing import Final

from stackops.scripts.python.helpers.helpers_agents.agents_browser_constants import BrowserTechName
import stackops.scripts.python.helpers.helpers_agents.browser_guides as browser_guide_assets
from stackops.utils.path_reference import get_path_reference_path


@dataclass(frozen=True)
class BrowserTechAssetSet:
    path_references: tuple[str, ...]
    mcp_servers: tuple[str, ...]


_BROWSER_TECH_ASSETS: Final[dict[BrowserTechName, BrowserTechAssetSet]] = {
    "agent-browser": BrowserTechAssetSet(
        path_references=(browser_guide_assets.AGENT_BROWSER_GUIDE_PATH_REFERENCE,),
        mcp_servers=(),
    ),
    "chrome-devtools-mcp": BrowserTechAssetSet(
        path_references=(
            browser_guide_assets.CHROME_DEVTOOLS_MCP_GUIDE_PATH_REFERENCE,
            browser_guide_assets.CHROME_DEVTOOLS_MCP_CONFIG_PATH_REFERENCE,
            browser_guide_assets.CHROME_DEVTOOLS_MCP_BROWSER_URL_CONFIG_PATH_REFERENCE,
        ),
        mcp_servers=("chrome-devtools", "chrome-devtools-browser-url"),
    ),
    "playwright-mcp": BrowserTechAssetSet(
        path_references=(
            browser_guide_assets.PLAYWRIGHT_MCP_GUIDE_PATH_REFERENCE,
            browser_guide_assets.PLAYWRIGHT_MCP_CONFIG_PATH_REFERENCE,
            browser_guide_assets.PLAYWRIGHT_MCP_EXTENSION_CONFIG_PATH_REFERENCE,
            browser_guide_assets.PLAYWRIGHT_MCP_CDP_CONFIG_PATH_REFERENCE,
            browser_guide_assets.PLAYWRIGHT_MCP_USER_DATA_DIR_CONFIG_PATH_REFERENCE,
            browser_guide_assets.PLAYWRIGHT_MCP_STORAGE_STATE_CONFIG_PATH_REFERENCE,
        ),
        mcp_servers=("playwright", "playwright-extension", "playwright-cdp"),
    ),
}


def _render_browser_tech_asset(raw_text: str) -> str:
    return raw_text.replace("{home}", Path.home().as_posix())


def get_browser_tech_mcp_servers(*, which: BrowserTechName) -> tuple[str, ...]:
    return _BROWSER_TECH_ASSETS[which].mcp_servers


def write_browser_tech_files(*, which: BrowserTechName, install_root: Path) -> tuple[Path, ...]:
    asset_set = _BROWSER_TECH_ASSETS[which]
    install_root.mkdir(parents=True, exist_ok=True)

    written_paths: list[Path] = []
    for path_reference in asset_set.path_references:
        source_path = get_path_reference_path(module=browser_guide_assets, path_reference=path_reference)
        destination_path = install_root.joinpath(source_path.name)
        destination_path.write_text(_render_browser_tech_asset(source_path.read_text(encoding="utf-8")), encoding="utf-8")
        written_paths.append(destination_path)
    return tuple(written_paths)
