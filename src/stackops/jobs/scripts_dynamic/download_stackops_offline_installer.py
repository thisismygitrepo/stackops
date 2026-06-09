#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# ///

from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Final
from urllib.request import urlopen

URL_MAP_FILE_NAME: Final[str] = Path(__file__).resolve().with_suffix(".json").name
URL_MAP_FALLBACK_URL: Final[str] = (
    "https://raw.githubusercontent.com/thisismygitrepo/stackops/refs/heads/main/"
    f"src/stackops/jobs/scripts_dynamic/{URL_MAP_FILE_NAME}"
)
DEFAULT_OUTPUT_DIR: Final[Path] = Path.home().joinpath(
    ".config",
    "stackops",
    "offline_installers",
    "stackops-offline-installer",
)
KNOWN_TARGETS: Final[tuple[str, ...]] = (
    "linux-x64",
    "linux-arm",
    "macos-x64",
    "macos-arm",
    "windows-x64",
    "windows-arm",
)


@dataclass(frozen=True, slots=True)
class InstallerTarget:
    pair: str
    url: str | None


def main() -> None:
    download_installer(target_key=None, output_dir=None)


def download_installer(*, target_key: str | None, output_dir: Path | None) -> Path:
    url_map = _load_url_map()
    targets = _build_targets(url_map=url_map)
    if target_key is None:
        selected_target = _prompt_for_target(targets=targets)
    else:
        selected_target = _resolve_target(targets=targets, target_key=target_key)
    if selected_target.url is None:
        raise RuntimeError(f"No Google Drive URL is configured yet for {selected_target.pair}.")
    resolved_output_dir = (output_dir or DEFAULT_OUTPUT_DIR).expanduser().resolve()
    print(f"Downloading {selected_target.pair} offline installer into {resolved_output_dir}")
    _download_and_extract(url=selected_target.url, output_dir=resolved_output_dir)
    print(f"Offline installer extracted to {resolved_output_dir}")
    return resolved_output_dir


def _load_url_map() -> dict[str, str | None]:
    local_url_map_path = Path(__file__).resolve().with_suffix(".json")
    if local_url_map_path.is_file():
        return _parse_url_map(raw_json=local_url_map_path.read_text(encoding="utf-8"))
    with urlopen(URL_MAP_FALLBACK_URL, timeout=30) as response:
        payload = response.read().decode("utf-8")
    return _parse_url_map(raw_json=payload)


def _parse_url_map(*, raw_json: str) -> dict[str, str | None]:
    parsed = json.loads(raw_json)
    if not isinstance(parsed, dict):
        raise RuntimeError("Offline installer URL map must be a JSON object.")
    url_map: dict[str, str | None] = {target_key: None for target_key in KNOWN_TARGETS}
    for key, value in parsed.items():
        if key not in url_map:
            raise RuntimeError(f"Unsupported offline installer target in URL map: {key}")
        if value is not None and not isinstance(value, str):
            raise RuntimeError(f"Offline installer URL for {key} must be a string or null.")
        url_map[key] = value
    return url_map


def _build_targets(*, url_map: dict[str, str | None]) -> list[InstallerTarget]:
    return [InstallerTarget(pair=target_key, url=url_map[target_key]) for target_key in KNOWN_TARGETS]


def _prompt_for_target(*, targets: list[InstallerTarget]) -> InstallerTarget:
    if len(targets) == 0:
        raise RuntimeError("No offline installer targets are configured.")
    print("Choose the OS/arch pair to download:")
    for index, target in enumerate(targets, start=1):
        status = "ready" if target.url is not None else "missing URL"
        print(f"{index}. {target.pair} [{status}]")
    while True:
        selection = input("Select a number: ").strip()
        if not selection.isdigit():
            print("Enter a numeric choice.")
            continue
        selected_index = int(selection)
        if 1 <= selected_index <= len(targets):
            return targets[selected_index - 1]
        print("Choice out of range.")


def _resolve_target(*, targets: list[InstallerTarget], target_key: str) -> InstallerTarget:
    for target in targets:
        if target.pair == target_key:
            return target
    supported_targets = ", ".join(target.pair for target in targets)
    raise RuntimeError(f"Unsupported offline installer target: {target_key}. Supported targets: {supported_targets}")


def _download_and_extract(*, url: str, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stackops_offline_installer_", dir=output_dir.parent) as temp_dir_string:
        download_dir = Path(temp_dir_string)
        subprocess.run(["uvx", "gdown", url, "-O", f"{download_dir.as_posix()}/"], check=True)
        archive_path = _resolve_downloaded_archive(download_dir=download_dir)
        shutil.unpack_archive(str(archive_path), str(output_dir))


def _resolve_downloaded_archive(*, download_dir: Path) -> Path:
    downloaded_files = sorted(path for path in download_dir.iterdir() if path.is_file())
    if len(downloaded_files) != 1:
        raise RuntimeError(f"Expected exactly one downloaded archive in {download_dir}, found {len(downloaded_files)}.")
    return downloaded_files[0]


if __name__ == "__main__":
    main()
