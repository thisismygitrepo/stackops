from pathlib import Path
import argparse
import json
import sys
from typing import cast

from stackops.utils.installer_utils.installer_catalog import installer_data_file_text, load_installer_data_file, normalize_installer_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safely upsert one installer entry into an installer_data.yaml catalog.")
    parser.add_argument("--installer-data", "-i", required=False, default="src/stackops/utils/schemas/installer/installer_data.yaml", help="Path to installer_data.yaml")
    parser.add_argument("--entry-json", "-e", required=True, help="Path to JSON produced by build_installer_config.py (contains {entry, checks})")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Show action but do not write")
    parser.add_argument("--fail-on-check-warnings", "-f", action="store_true", help="Abort if build checks contain warnings")
    return parser


def expect_string_key_dict(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError(f"{label} must only contain string keys")
    return cast(dict[str, object], value)


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

    if entry_path.exists() is False:
        raise FileNotFoundError(f"entry JSON path not found: {entry_path}")

    catalog = load_installer_data_file(path=installer_path)
    generated_payload_map = expect_string_key_dict(value=cast(object, json.loads(entry_path.read_text(encoding="utf-8"))), label="entry JSON root")
    if "entry" not in generated_payload_map:
        raise ValueError("entry JSON must include object key: entry")
    entry = normalize_installer_data(value=generated_payload_map["entry"], context=f"{entry_path}.entry")
    warning_rows = collect_warning_rows(checks=generated_payload_map.get("checks", {}))

    if fail_on_check_warnings and len(warning_rows) > 0:
        raise RuntimeError("Refusing upsert because build checks contain warnings")

    installers = catalog["installers"]
    matched_index = next(
        (index for index, installer in enumerate(installers) if installer["appName"].casefold() == entry["appName"].casefold()),
        None,
    )
    action: str
    if matched_index is None:
        installers.append(entry)
        action = "append"
    else:
        installers[matched_index] = entry
        action = f"replace index {matched_index}"

    if dry_run:
        sys.stdout.write(f"Dry run: would {action} in {installer_path}\n")
    else:
        installer_path.write_text(installer_data_file_text(path=installer_path, catalog=catalog), encoding="utf-8")
        sys.stdout.write(f"Wrote installer data via {action}: {installer_path}\n")
    if len(warning_rows) > 0:
        sys.stdout.write("Warnings:\n")
        for warning in warning_rows:
            sys.stdout.write(f"- {warning}\n")


if __name__ == "__main__":
    main()
