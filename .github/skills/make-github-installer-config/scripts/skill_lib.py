from dataclasses import dataclass
from typing import Literal, cast
import json
import re
import urllib.error
import urllib.request


type OperatingSystem = Literal["linux", "darwin", "windows"]
type CpuArchitecture = Literal["amd64", "arm64"]
type LicenseSource = Literal["user", "github_api_name", "github_api_spdx", "fallback"]

GITHUB_API_BASE: str = "https://api.github.com"
USER_AGENT: str = "stackops-skill/make-github-installer-config"


@dataclass(frozen=True, slots=True)
class RepoSpec:
    owner: str
    repo: str


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    tag_name: str
    assets: list[ReleaseAsset]


@dataclass(frozen=True, slots=True)
class ResolvedLicense:
    value: str
    source: LicenseSource
    warning: str | None


def _as_string_key_dict(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    if any(not isinstance(key, str) for key in value):
        return None
    return cast(dict[str, object], value)


def parse_repo_url(repo_url: str) -> RepoSpec:
    cleaned: str = repo_url.strip().removesuffix("/")
    match = re.match(r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)$", cleaned)
    if match is None:
        raise ValueError(f"Invalid GitHub repository URL: {repo_url}")
    owner: str = match.group("owner")
    repo: str = match.group("repo")
    return RepoSpec(owner=owner, repo=repo)


def _http_get_json(url: str) -> object:
    request = urllib.request.Request(url=url, headers={"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub API HTTP error {error.code} for URL: {url}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Network error while requesting GitHub API URL: {url}") from error
    return json.loads(data)


def fetch_releases(spec: RepoSpec, limit: int) -> list[ReleaseInfo]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    api_url: str = f"{GITHUB_API_BASE}/repos/{spec.owner}/{spec.repo}/releases?per_page={limit}"
    payload = _http_get_json(api_url)
    if not isinstance(payload, list):
        raise RuntimeError("Unexpected GitHub API response format for releases endpoint")

    releases: list[ReleaseInfo] = []
    for release_row in payload:
        release_map = _as_string_key_dict(release_row)
        if release_map is None:
            continue
        tag_name_raw = release_map.get("tag_name")
        assets_raw = release_map.get("assets")
        if not isinstance(tag_name_raw, str):
            continue
        assets: list[ReleaseAsset] = []
        if isinstance(assets_raw, list):
            for asset_row in assets_raw:
                asset_map = _as_string_key_dict(asset_row)
                if asset_map is None:
                    continue
                asset_name = asset_map.get("name")
                if isinstance(asset_name, str):
                    assets.append(ReleaseAsset(name=asset_name))
        releases.append(ReleaseInfo(tag_name=tag_name_raw, assets=assets))

    if len(releases) == 0:
        raise RuntimeError(f"No releases found for {spec.owner}/{spec.repo}")
    return releases


def fetch_repo_license(spec: RepoSpec) -> ResolvedLicense:
    api_url: str = f"{GITHUB_API_BASE}/repos/{spec.owner}/{spec.repo}"
    payload = _http_get_json(api_url)
    payload_map = _as_string_key_dict(payload)
    if payload_map is None:
        raise RuntimeError("Unexpected GitHub API response format for repository endpoint")

    license_value = payload_map.get("license")
    license_map = _as_string_key_dict(license_value)
    if license_map is None:
        return ResolvedLicense(
            value="No license asserted",
            source="fallback",
            warning="GitHub repository metadata does not declare a license",
        )

    license_name_raw = license_map.get("name")
    license_spdx_raw = license_map.get("spdx_id")
    license_name = license_name_raw.strip() if isinstance(license_name_raw, str) else ""
    license_spdx = license_spdx_raw.strip() if isinstance(license_spdx_raw, str) else ""

    if license_name and license_name.lower() != "other":
        return ResolvedLicense(value=license_name, source="github_api_name", warning=None)
    if license_spdx and license_spdx.upper() != "NOASSERTION":
        return ResolvedLicense(value=license_spdx, source="github_api_spdx", warning=None)
    return ResolvedLicense(
        value="No license asserted",
        source="fallback",
        warning="GitHub repository metadata does not provide a usable license value",
    )


def normalize_version_for_placeholder(tag_name: str) -> str:
    return tag_name[1:] if tag_name.startswith("v") else tag_name


def classify_os(asset_name: str) -> OperatingSystem | None:
    lowered: str = asset_name.lower()
    if "linux" in lowered:
        return "linux"
    if "darwin" in lowered or "macos" in lowered or "apple" in lowered or "osx" in lowered:
        return "darwin"
    if "windows" in lowered or "win" in lowered or "msvc" in lowered:
        return "windows"
    return None


def classify_arch(asset_name: str) -> CpuArchitecture | None:
    lowered: str = asset_name.lower()
    if "aarch64" in lowered or "arm64" in lowered:
        return "arm64"
    if "x86_64" in lowered or "amd64" in lowered or "x64" in lowered:
        return "amd64"
    return None


def looks_like_binary_asset(asset_name: str) -> bool:
    lowered: str = asset_name.lower()
    excluded_tokens: tuple[str, ...] = ("checksums", "sha256", ".sig", ".pem", "sbom", ".txt", ".json")
    if any(token in lowered for token in excluded_tokens):
        return False
    archive_like: tuple[str, ...] = (".tar.gz", ".tgz", ".tar.xz", ".zip", ".7z", ".exe", ".msi", ".pkg", ".deb", ".rpm")
    return any(lowered.endswith(suffix) for suffix in archive_like)


def to_placeholder_pattern(asset_name: str, tag_name: str) -> str:
    tag_no_v: str = normalize_version_for_placeholder(tag_name)
    variants: list[str] = [tag_name, tag_no_v, f"v{tag_no_v}"]
    variants_sorted: list[str] = sorted(set(variants), key=lambda variant: len(variant), reverse=True)
    result: str = asset_name
    for variant in variants_sorted:
        if len(variant) == 0:
            continue
        result = result.replace(variant, "{version}")
    return result


def file_exists_for_pattern(asset_names: set[str], pattern: str, latest_tag_name: str) -> bool:
    normalized_version: str = normalize_version_for_placeholder(latest_tag_name)
    candidate_a: str = pattern.replace("{version}", normalized_version)
    candidate_b: str = pattern.replace("{version}", latest_tag_name)
    return candidate_a in asset_names or candidate_b in asset_names
