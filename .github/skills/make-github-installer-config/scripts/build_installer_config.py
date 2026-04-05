from collections import Counter
from pathlib import Path
import argparse
import json
import sys
from typing import Literal, TypedDict

from skill_lib import classify_arch
from skill_lib import classify_os
from skill_lib import fetch_repo_license
from skill_lib import fetch_releases
from skill_lib import file_exists_for_pattern
from skill_lib import looks_like_binary_asset
from skill_lib import parse_repo_url
from skill_lib import RepoSpec
from skill_lib import ResolvedLicense
from skill_lib import to_placeholder_pattern


type PlatformName = Literal["linux", "darwin", "windows"]
type ArchName = Literal["amd64", "arm64"]
type LicenseSourceName = Literal["user", "github_api_name", "github_api_spdx", "fallback"]

PLATFORMS: tuple[PlatformName, ...] = ("linux", "darwin", "windows")
ARCHES: tuple[ArchName, ...] = ("amd64", "arm64")


class PlatformPatternRow(TypedDict):
    linux: str | None
    darwin: str | None
    windows: str | None


class PatternMatrix(TypedDict):
    amd64: PlatformPatternRow
    arm64: PlatformPatternRow


class InstallerEntry(TypedDict):
    appName: str
    license: str
    repoURL: str
    doc: str
    fileNamePattern: PatternMatrix


class OutputChecks(TypedDict):
    latestTag: str
    latestAssetCount: int
    latestPatternChecks: list[str]
    licenseSource: LicenseSourceName
    licenseWarning: str | None


class OutputPayload(TypedDict):
    entry: InstallerEntry
    checks: OutputChecks


def infer_best_pattern(candidates: list[str], os_name: PlatformName) -> str | None:
    if len(candidates) == 0:
        return None
    counts: Counter[str] = Counter(candidates)
    ranked: list[tuple[str, int]] = sorted(counts.items(), key=lambda row: row[1], reverse=True)

    if os_name == "linux":
        musl_first: list[tuple[str, int]] = [item for item in ranked if "musl" in item[0].lower()]
        if len(musl_first) > 0:
            return musl_first[0][0]
    return ranked[0][0]


def resolve_license(spec: RepoSpec, override_license: str | None) -> ResolvedLicense:
    if override_license is not None:
        cleaned_license: str = override_license.strip()
        if len(cleaned_license) == 0:
            raise ValueError("--license cannot be empty")
        return ResolvedLicense(value=cleaned_license, source="user", warning=None)
    return fetch_repo_license(spec=spec)


def build_pattern_row(platform_buckets: dict[PlatformName, list[str]]) -> PlatformPatternRow:
    return {
        "linux": infer_best_pattern(candidates=platform_buckets["linux"], os_name="linux"),
        "darwin": infer_best_pattern(candidates=platform_buckets["darwin"], os_name="darwin"),
        "windows": infer_best_pattern(candidates=platform_buckets["windows"], os_name="windows"),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build installer_data.json config entry from GitHub release assets.")
    parser.add_argument("--repo-url", required=True, help="GitHub repository URL")
    parser.add_argument("--app-name", required=True, help="Lowercase app name")
    parser.add_argument("--doc", required=True, help="Short description")
    parser.add_argument(
        "--license",
        required=False,
        default=None,
        help="Override license string instead of inferring it from GitHub metadata",
    )
    parser.add_argument("--limit", required=False, default=8, type=int, help="Number of releases to inspect")
    parser.add_argument("--output", required=False, default="-", help="Output path for JSON object, or '-' for stdout")
    parser.add_argument("--strict-latest-check", action="store_true", help="Fail if any non-null pattern does not match latest release assets")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    repo_url: str = str(args.repo_url).strip()
    app_name: str = str(args.app_name).strip().lower()
    doc: str = str(args.doc).strip()
    license_override_raw = args.license
    license_override: str | None = None if license_override_raw is None else str(license_override_raw)
    limit: int = int(args.limit)
    output: str = str(args.output)
    strict_latest_check: bool = bool(args.strict_latest_check)

    if len(app_name) == 0:
        raise ValueError("--app-name cannot be empty")
    if len(doc) == 0:
        raise ValueError("--doc cannot be empty")

    spec = parse_repo_url(repo_url=repo_url)
    resolved_license = resolve_license(spec=spec, override_license=license_override)
    releases = fetch_releases(spec=spec, limit=limit)
    latest_release = releases[0]
    latest_asset_names: set[str] = {asset.name for asset in latest_release.assets}

    buckets: dict[ArchName, dict[PlatformName, list[str]]] = {
        arch: {platform: [] for platform in PLATFORMS}
        for arch in ARCHES
    }

    for release in releases:
        for asset in release.assets:
            if looks_like_binary_asset(asset_name=asset.name) is False:
                continue
            os_name = classify_os(asset_name=asset.name)
            arch_name = classify_arch(asset_name=asset.name)
            if os_name is None or arch_name is None:
                continue
            pattern: str = to_placeholder_pattern(asset_name=asset.name, tag_name=release.tag_name)
            buckets[arch_name][os_name].append(pattern)

    pattern_matrix: PatternMatrix = {
        "amd64": build_pattern_row(platform_buckets=buckets["amd64"]),
        "arm64": build_pattern_row(platform_buckets=buckets["arm64"]),
    }

    failed_checks: list[str] = []
    for arch in ARCHES:
        for platform in PLATFORMS:
            selected_pattern: str | None = pattern_matrix[arch][platform]
            if selected_pattern is None:
                continue
            exists: bool = file_exists_for_pattern(asset_names=latest_asset_names, pattern=selected_pattern, latest_tag_name=latest_release.tag_name)
            if exists is False:
                failed_checks.append(f"Missing latest asset for {arch}/{platform}: pattern='{selected_pattern}' tag='{latest_release.tag_name}'")

    if strict_latest_check and len(failed_checks) > 0:
        raise RuntimeError("; ".join(failed_checks))

    entry: InstallerEntry = {
        "appName": app_name,
        "license": resolved_license.value,
        "repoURL": repo_url,
        "doc": doc,
        "fileNamePattern": pattern_matrix,
    }

    output_payload: OutputPayload = {
        "entry": entry,
        "checks": {
            "latestTag": latest_release.tag_name,
            "latestAssetCount": len(latest_asset_names),
            "latestPatternChecks": failed_checks,
            "licenseSource": resolved_license.source,
            "licenseWarning": resolved_license.warning,
        },
    }

    out_text: str = json.dumps(output_payload, indent=2, ensure_ascii=False)
    if output == "-":
        sys.stdout.write(out_text + "\n")
        return

    out_path = Path(output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_text + "\n", encoding="utf-8")
    sys.stdout.write(f"Wrote config output to: {out_path}\n")


if __name__ == "__main__":
    main()
