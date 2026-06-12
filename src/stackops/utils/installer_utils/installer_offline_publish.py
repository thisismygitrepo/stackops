from pathlib import Path
import json

from stackops.utils.cloud import rclone_wrapper
from stackops.utils.installer_utils import installer_offline_constants as constants
from stackops.utils.installer_utils.installer_offline_models import ExportStepResult

KNOWN_TARGET_KEYS: tuple[str, ...] = (
    "linux-x64",
    "linux-arm",
    "macos-x64",
    "macos-arm",
    "windows-x64",
    "windows-arm",
)


def publish_archive(*, archive_path: Path, system_name: str, arch_name: str) -> list[ExportStepResult]:
    remote_path = rclone_wrapper.get_remote_path(
        local_path=archive_path,
        root=constants.OFFLINE_INSTALLER_UPLOAD_REMOTE_ROOT,
        os_specific=False,
        rel2home=True,
        strict=True,
    )
    share_url = rclone_wrapper.to_cloud(
        local_path=archive_path,
        cloud=constants.OFFLINE_INSTALLER_UPLOAD_CLOUD,
        remote_path=remote_path,
        share=True,
        share_options=None,
        verbose=True,
        transfers=10,
    )
    if share_url is None:
        raise RuntimeError("Offline installer upload requested sharing, but no share URL was returned.")
    url_map_path = _resolve_url_map_path()
    target_key = _build_target_key(system_name=system_name, arch_name=arch_name)
    url_map = _load_url_map(url_map_path=url_map_path)
    url_map[target_key] = share_url
    url_map_path.write_text(json.dumps(url_map, indent=2) + "\n", encoding="utf-8")
    return [
        ExportStepResult(
            label="cloud upload",
            status="included",
            detail=f"uploaded to {constants.OFFLINE_INSTALLER_UPLOAD_CLOUD}:{remote_path.as_posix()}",
            output_path=archive_path,
        ),
        ExportStepResult(
            label="download url map",
            status="included",
            detail=f"updated {target_key} in {url_map_path.name}",
            output_path=url_map_path,
        ),
    ]


def _resolve_url_map_path() -> Path:
    url_map_path = constants.OFFLINE_INSTALLER_URL_MAP_PATH
    if not url_map_path.is_file():
        raise RuntimeError(f"Offline installer URL map not found: {url_map_path}")
    return url_map_path


def _build_target_key(*, system_name: str, arch_name: str) -> str:
    os_token = _normalize_system_token(system_name=system_name)
    arch_token = _normalize_arch_token(arch_name=arch_name)
    return f"{os_token}-{arch_token}"


def _normalize_system_token(*, system_name: str) -> str:
    match system_name:
        case "Linux":
            return "linux"
        case "Darwin":
            return "macos"
        case "Windows":
            return "windows"
        case _:
            raise RuntimeError(f"Unsupported operating system for offline installer publishing: {system_name}")


def _normalize_arch_token(*, arch_name: str) -> str:
    normalized_arch = arch_name.lower()
    if normalized_arch in {"x86_64", "amd64"}:
        return "x64"
    if normalized_arch in {"aarch64", "arm64", "armv8", "armv8l"}:
        return "arm"
    raise RuntimeError(f"Unsupported CPU architecture for offline installer publishing: {arch_name}")


def _load_url_map(*, url_map_path: Path) -> dict[str, str | None]:
    raw_data = json.loads(url_map_path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise RuntimeError(f"Offline installer URL map must be a JSON object: {url_map_path}")
    normalized: dict[str, str | None] = {target_key: None for target_key in KNOWN_TARGET_KEYS}
    for key, value in raw_data.items():
        if key not in normalized:
            raise RuntimeError(f"Unsupported offline installer target in URL map: {key}")
        if value is not None and not isinstance(value, str):
            raise RuntimeError(f"Offline installer URL for {key} must be a string or null.")
        normalized[key] = value
    return normalized
