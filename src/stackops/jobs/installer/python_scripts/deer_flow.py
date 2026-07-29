import platform
import shutil
import subprocess
from pathlib import Path
from typing import Final

from stackops.utils.schemas.installer.installer_types import InstallerData


DEER_FLOW_REPOSITORY_URL: Final[str] = "https://github.com/bytedance/deer-flow"
DEER_FLOW_INSTALL_ROOT: Final[Path] = Path.home().joinpath("code", "foreign", "deer-flow")


def main(installer_data: InstallerData, version: str | None, update: bool) -> None:
    repository_url = installer_data["repoURL"]
    if repository_url != DEER_FLOW_REPOSITORY_URL:
        raise ValueError(f"Unexpected DeerFlow repository URL: {repository_url}")

    if DEER_FLOW_INSTALL_ROOT.exists():
        if not DEER_FLOW_INSTALL_ROOT.joinpath(".git").is_dir():
            raise FileExistsError(f"DeerFlow install path exists but is not a Git repository: {DEER_FLOW_INSTALL_ROOT}")
    else:
        DEER_FLOW_INSTALL_ROOT.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", DEER_FLOW_REPOSITORY_URL, str(DEER_FLOW_INSTALL_ROOT)],
            check=True,
        )

    if version is not None:
        subprocess.run(
            ["git", "-C", str(DEER_FLOW_INSTALL_ROOT), "fetch", "--tags", "origin"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(DEER_FLOW_INSTALL_ROOT), "checkout", "--detach", version],
            check=True,
        )
    elif update:
        subprocess.run(
            ["git", "-C", str(DEER_FLOW_INSTALL_ROOT), "pull", "--ff-only"],
            check=True,
        )

    if not DEER_FLOW_INSTALL_ROOT.joinpath("config.yaml").is_file():
        if platform.system() == "Windows":
            bash_path = shutil.which("bash")
            if bash_path is None:
                raise FileNotFoundError("DeerFlow setup on Windows requires Git Bash")
            subprocess.run(
                [
                    bash_path,
                    "-lc",
                    'cd "$(cygpath -u "$1")" && make setup',
                    "stackops-deer-flow",
                    str(DEER_FLOW_INSTALL_ROOT),
                ],
                check=True,
            )
        else:
            subprocess.run(["make", "setup"], cwd=DEER_FLOW_INSTALL_ROOT, check=True)

    print(f"DeerFlow workspace: {DEER_FLOW_INSTALL_ROOT}")
    print("Run `make docker-init && make docker-start` from that directory for the recommended Docker development environment.")
