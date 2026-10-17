from pathlib import Path
from typing import Final

from stackops.utils.installer_utils.install_request_logic import build_install_target
from stackops.utils.schemas.installer.installer_types import InstallerData
from stackops.utils.source_of_truth import LIBRARY_ROOT


LIBRARY_INSTALLER_SCRIPTS_ROOT: Final[Path] = LIBRARY_ROOT.joinpath("jobs", "installer")


def get_user_installer_scripts_root(user_catalog_path: Path) -> Path:
    return user_catalog_path.parent.joinpath("installer_scripts")


def resolve_installer_script(script_name: str, user_scripts_root: Path | None) -> Path:
    search_roots = (LIBRARY_INSTALLER_SCRIPTS_ROOT,) if user_scripts_root is None else (LIBRARY_INSTALLER_SCRIPTS_ROOT, user_scripts_root)
    search_results = [match for search_root in search_roots for match in search_root.rglob(script_name)]
    if len(search_results) == 0:
        raise FileNotFoundError(f"""Could not find installation script {script_name} under any of: {", ".join(str(search_root) for search_root in search_roots)}""")
    if len(search_results) > 1:
        raise ValueError(f"""Multiple installation scripts found for {script_name}: {", ".join(str(search_result) for search_result in search_results)}""")
    return search_results[0]


def validate_installer_script_references(installers: list[InstallerData], user_scripts_root: Path) -> None:
    for installer in installers:
        for architecture_pattern in (installer["fileNamePattern"]["amd64"], installer["fileNamePattern"]["arm64"]):
            linux_pattern = architecture_pattern["linux"]
            linux_values = (
                [linux_pattern]
                if linux_pattern is None or isinstance(linux_pattern, str)
                else [linux_pattern["apk"], linux_pattern["apt"], linux_pattern["dnf"], linux_pattern["pacman"], linux_pattern.get("omarchy")]
            )
            for pattern_value in (architecture_pattern["windows"], *linux_values, architecture_pattern["darwin"]):
                if pattern_value is None:
                    continue
                if build_install_target(repo_url=installer["repoURL"], installer_value=pattern_value).installer_kind == "script":
                    resolve_installer_script(script_name=pattern_value, user_scripts_root=user_scripts_root)
