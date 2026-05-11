from pathlib import Path
import shlex

from stackops.utils import rclone_wrapper
from stackops.utils.installer_utils import installer_offline_constants as constants
from stackops.utils.installer_utils.installer_offline_models import ExportStepResult


def publish_archive(*, archive_path: Path, system_name: str, arch_name: str) -> list[ExportStepResult]:
    remote_path = constants.OFFLINE_INSTALLER_UPLOAD_REMOTE_DIR.joinpath(archive_path.name)
    share_url = rclone_wrapper.to_cloud(
        local_path=archive_path,
        cloud=constants.OFFLINE_INSTALLER_UPLOAD_CLOUD,
        remote_path=remote_path,
        share=True,
        verbose=True,
        transfers=10,
    )
    if share_url is None:
        raise RuntimeError("Offline installer upload requested sharing, but no share URL was returned.")
    share_url_path = archive_path.with_suffix(f".share_url_{constants.OFFLINE_INSTALLER_UPLOAD_CLOUD}")
    share_url_path.write_text(share_url, encoding="utf-8")
    download_script_path = _resolve_download_script_path(system_name=system_name, arch_name=arch_name)
    download_script_path.write_text(_build_download_script_content(share_url=share_url, system_name=system_name), encoding="utf-8")
    return [
        ExportStepResult(
            label="cloud upload",
            status="included",
            detail=f"uploaded to {constants.OFFLINE_INSTALLER_UPLOAD_CLOUD}:{remote_path.as_posix()}",
            output_path=share_url_path,
        ),
        ExportStepResult(
            label="download script",
            status="included",
            detail=f"updated {download_script_path.name} with shared download URL",
            output_path=download_script_path,
        ),
    ]


def _resolve_download_script_path(*, system_name: str, arch_name: str) -> Path:
    repo_root = _resolve_repo_root()
    relative_script_path = _resolve_download_script_relative_path(system_name=system_name, arch_name=arch_name)
    script_path = repo_root.joinpath(relative_script_path)
    if not script_path.is_file():
        raise RuntimeError(f"Offline installer download script not found: {script_path}")
    return script_path


def _resolve_repo_root() -> Path:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if parent.joinpath("pyproject.toml").is_file() and parent.joinpath("src", "stackops").is_dir():
            return parent
    raise RuntimeError("Could not resolve the StackOps repository root from the installed source tree.")


def _resolve_download_script_relative_path(*, system_name: str, arch_name: str) -> Path:
    os_token, script_directory, extension = _normalize_system_token(system_name=system_name)
    arch_token = _normalize_arch_token(arch_name=arch_name)
    return Path("src", "stackops", "jobs", "scripts", script_directory, f"download-stackops-offline-installer-{os_token}-{arch_token}.{extension}")


def _normalize_system_token(*, system_name: str) -> tuple[str, str, str]:
    match system_name:
        case "Linux":
            return ("linux", "bash_scripts", "sh")
        case "Darwin":
            return ("macos", "bash_scripts", "sh")
        case "Windows":
            return ("windows", "powershell_scripts", "ps1")
        case _:
            raise RuntimeError(f"Unsupported operating system for offline installer publishing: {system_name}")


def _normalize_arch_token(*, arch_name: str) -> str:
    normalized_arch = arch_name.lower()
    if normalized_arch in {"x86_64", "amd64"}:
        return "x64"
    if normalized_arch in {"aarch64", "arm64", "armv8", "armv8l"}:
        return "arm"
    raise RuntimeError(f"Unsupported CPU architecture for offline installer publishing: {arch_name}")


def _build_download_script_content(*, share_url: str, system_name: str) -> str:
    quoted_share_url = _quote_share_url(share_url=share_url, system_name=system_name)
    return f"""utils file download --decompress --output-dir {constants.OFFLINE_INSTALLER_DOWNLOAD_OUTPUT_DIR} {quoted_share_url}\n"""


def _quote_share_url(*, share_url: str, system_name: str) -> str:
    if system_name == "Windows":
        escaped_share_url = share_url.replace("'", "''")
        return f"'{escaped_share_url}'"
    return shlex.quote(share_url)
