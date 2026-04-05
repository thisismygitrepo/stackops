from datetime import UTC, datetime
from pathlib import Path
import argparse
import json
import sys
from typing import Literal, cast


type PlatformName = Literal["linux", "darwin", "windows"]
type ArchName = Literal["amd64", "arm64"]

PLATFORMS: tuple[PlatformName, ...] = ("linux", "darwin", "windows")
ARCHES: tuple[ArchName, ...] = ("amd64", "arm64")
PLATFORM_KEYS: frozenset[str] = frozenset(PLATFORMS)
ARCH_KEYS: frozenset[str] = frozenset(ARCHES)
ENTRY_KEYS: frozenset[str] = frozenset({"appName", "license", "repoURL", "doc", "fileNamePattern"})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely upsert one installer entry into installer_data.json.")
    parser.add_argument("--installer-data", required=False, default="src/machineconfig/jobs/installer/installer_data.json", help="Path to installer_data.json")
    parser.add_argument("--entry-json", required=True, help="Path to JSON produced by build_installer_config.py (contains {entry, checks})")
    parser.add_argument("--dry-run", action="store_true", help="Show action but do not write")
    parser.add_argument("--fail-on-check-warnings", action="store_true", help="Abort if build checks contain warnings")
    return parser


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def expect_string_key_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} must only contain string keys")
    return cast(dict[str, object], value)


def expect_non_empty_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    cleaned: str = value.strip()
    if len(cleaned) == 0:
        raise ValueError(f"{label} must be non-empty")
    return cleaned


def validate_pattern_row(value: object, label: str) -> None:
    row = expect_string_key_dict(value=value, label=label)
    missing_keys = sorted(PLATFORM_KEYS - set(row))
    unexpected_keys = sorted(set(row) - PLATFORM_KEYS)
    if len(missing_keys) > 0 or len(unexpected_keys) > 0:
        raise ValueError(f"{label} keys mismatch, missing={missing_keys}, unexpected={unexpected_keys}")
    for platform in PLATFORMS:
        platform_value = row[platform]
        if platform_value is not None and not isinstance(platform_value, str):
            raise ValueError(f"{label}.{platform} must be a string or null")


def validate_entry_shape(entry: object) -> tuple[str, str]:
    entry_map = expect_string_key_dict(value=entry, label="entry")
    missing_keys = sorted(ENTRY_KEYS - set(entry_map))
    unexpected_keys = sorted(set(entry_map) - ENTRY_KEYS)
    if len(missing_keys) > 0 or len(unexpected_keys) > 0:
        raise ValueError(f"entry keys mismatch, missing={missing_keys}, unexpected={unexpected_keys}")

    app_name = expect_non_empty_string(value=entry_map["appName"], label="entry.appName")
    expect_non_empty_string(value=entry_map["license"], label="entry.license")
    repo_url = expect_non_empty_string(value=entry_map["repoURL"], label="entry.repoURL")
    expect_non_empty_string(value=entry_map["doc"], label="entry.doc")

    pattern_map = expect_string_key_dict(value=entry_map["fileNamePattern"], label="entry.fileNamePattern")
    missing_arches = sorted(ARCH_KEYS - set(pattern_map))
    unexpected_arches = sorted(set(pattern_map) - ARCH_KEYS)
    if len(missing_arches) > 0 or len(unexpected_arches) > 0:
        raise ValueError(f"entry.fileNamePattern keys mismatch, missing={missing_arches}, unexpected={unexpected_arches}")
    for arch in ARCHES:
        validate_pattern_row(value=pattern_map[arch], label=f"entry.fileNamePattern.{arch}")

    return app_name, repo_url


def collect_warning_rows(checks: object) -> list[str]:
    checks_map: dict[str, object]
    if isinstance(checks, dict):
        checks_map = expect_string_key_dict(value=checks, label="checks")
    else:
        checks_map = {}
    warning_rows: list[str] = []

    latest_checks_value = checks_map.get("latestPatternChecks")
    if isinstance(latest_checks_value, list):
        for item in latest_checks_value:
            if isinstance(item, str):
                warning_rows.append(item)

    license_warning_value = checks_map.get("licenseWarning")
    if isinstance(license_warning_value, str) and len(license_warning_value.strip()) > 0:
        warning_rows.append(license_warning_value.strip())
    return warning_rows


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    installer_path = Path(str(args.installer_data)).expanduser().resolve()
    entry_path = Path(str(args.entry_json)).expanduser().resolve()
    dry_run: bool = bool(args.dry_run)
    fail_on_check_warnings: bool = bool(args.fail_on_check_warnings)

    if installer_path.exists() is False:
        raise FileNotFoundError(f"installer_data path not found: {installer_path}")
    if entry_path.exists() is False:
        raise FileNotFoundError(f"entry JSON path not found: {entry_path}")

    installer_payload = load_json(installer_path)
    generated_payload = load_json(entry_path)

    installer_payload_map = expect_string_key_dict(value=installer_payload, label="installer_data")
    installers_any = installer_payload_map.get("installers")
    if not isinstance(installers_any, list):
        raise ValueError("installer_data.installers must be an array")

    generated_payload_map = expect_string_key_dict(value=generated_payload, label="entry JSON root")
    if "entry" not in generated_payload_map:
        raise ValueError("entry JSON must include object key: entry")
    entry_any = generated_payload_map["entry"]
    checks_any = generated_payload_map.get("checks", {})

    app_name, repo_url = validate_entry_shape(entry=entry_any)
    warning_rows = collect_warning_rows(checks=checks_any)

    if fail_on_check_warnings and len(warning_rows) > 0:
        raise RuntimeError("Refusing upsert because build checks contain warnings")

    matched_indices: list[int] = []
    for idx, row in enumerate(installers_any):
        if not isinstance(row, dict):
            continue
        row_map = expect_string_key_dict(value=row, label=f"installer_data.installers[{idx}]")
        row_app = row_map.get("appName")
        row_repo = row_map.get("repoURL")
        if row_app == app_name or row_repo == repo_url:
            matched_indices.append(idx)

    action: str
    if len(matched_indices) == 0:
        installers_any.append(expect_string_key_dict(value=entry_any, label="entry"))
        action = "append"
    else:
        first_idx: int = matched_indices[0]
        installers_any[first_idx] = expect_string_key_dict(value=entry_any, label="entry")
        action = f"update index {first_idx}"
        if len(matched_indices) > 1:
            dedupe_indices: list[int] = matched_indices[1:]
            for idx in sorted(dedupe_indices, reverse=True):
                installers_any.pop(idx)
            action = action + f" and removed {len(dedupe_indices)} duplicate(s)"

    if dry_run:
        sys.stdout.write(f"Dry run: would {action} in {installer_path}\n")
        if len(warning_rows) > 0:
            sys.stdout.write("Warnings:\n")
            for warning in warning_rows:
                sys.stdout.write(f"- {warning}\n")
        return

    backup_suffix: str = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    backup_path = installer_path.with_suffix(installer_path.suffix + f".{backup_suffix}.bak")
    backup_path.write_text(installer_path.read_text(encoding="utf-8"), encoding="utf-8")

    installer_path.write_text(json.dumps(installer_payload_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sys.stdout.write(f"Wrote installer data via {action}: {installer_path}\n")
    sys.stdout.write(f"Backup written: {backup_path}\n")
    if len(warning_rows) > 0:
        sys.stdout.write("Warnings:\n")
        for warning in warning_rows:
            sys.stdout.write(f"- {warning}\n")


if __name__ == "__main__":
    main()
