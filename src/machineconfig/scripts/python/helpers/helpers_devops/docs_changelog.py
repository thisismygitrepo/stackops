from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess

from machineconfig.utils.source_of_truth import REPO_ROOT


CHANGELOG_PATH = Path("docs/changelog.md")
RELEASE_HEADING_PATTERN = re.compile(r"^## \[(?P<version>[^\]]+)\] - (?P<released_on>\d{4}-\d{2}-\d{2})$", re.MULTILINE)
TAG_VERSION_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)$")
CONVENTIONAL_SUBJECT_PATTERN = re.compile(r"^(?P<kind>[a-z]+)(?:\([^)]+\))?!?:\s*(?P<body>.+)$")


@dataclass(frozen=True, slots=True)
class ReleaseTag:
    version: str
    released_on: str
    subject: str
    major: int
    minor: int


def _parse_version(version_text: str) -> tuple[int, int] | None:
    match = TAG_VERSION_PATTERN.fullmatch(version_text.strip())
    if match is None:
        return None
    return (int(match.group("major")), int(match.group("minor")))


def load_release_tags(repo_root: Path) -> list[ReleaseTag]:
    completed_process = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)\t%(creatordate:short)\t%(subject)",
            "refs/tags",
        ],
        capture_output=True,
        check=True,
        cwd=repo_root,
        encoding="utf-8",
    )

    releases: list[ReleaseTag] = []
    for raw_line in completed_process.stdout.splitlines():
        if raw_line.strip() == "":
            continue
        tag_name, released_on, subject = raw_line.split("\t", maxsplit=2)
        version = tag_name.removeprefix("v")
        parsed_version = _parse_version(version)
        if parsed_version is None:
            continue
        major, minor = parsed_version
        releases.append(
            ReleaseTag(
                version=version,
                released_on=released_on,
                subject=subject.strip(),
                major=major,
                minor=minor,
            )
        )

    releases.sort(key=lambda release: (release.major, release.minor), reverse=True)
    return releases


def extract_existing_release_versions(changelog_text: str) -> list[str]:
    return [match.group("version") for match in RELEASE_HEADING_PATTERN.finditer(changelog_text)]


def _latest_documented_version(changelog_text: str) -> tuple[int, int] | None:
    parsed_versions = [
        parsed_version
        for version in extract_existing_release_versions(changelog_text)
        if (parsed_version := _parse_version(version)) is not None
    ]
    if parsed_versions == []:
        return None
    return max(parsed_versions)


def _find_insert_index(changelog_text: str) -> int:
    first_release_match = RELEASE_HEADING_PATTERN.search(changelog_text)
    if first_release_match is not None:
        return first_release_match.start()
    return len(changelog_text)


def _uppercase_first_character(text: str) -> str:
    if text == "":
        return text
    return f"{text[0].upper()}{text[1:]}"


def _categorize_subject(subject: str) -> tuple[str, str]:
    stripped_subject = subject.strip()
    if stripped_subject == "":
        return ("Changed", "Release published")

    conventional_match = CONVENTIONAL_SUBJECT_PATTERN.fullmatch(stripped_subject)
    if conventional_match is not None:
        kind = conventional_match.group("kind")
        body = _uppercase_first_character(conventional_match.group("body").strip())
        match kind:
            case "feat":
                return ("Added", body)
            case "fix":
                return ("Fixed", body)
            case _:
                return ("Changed", body)

    lowered_subject = stripped_subject.lower()
    if lowered_subject.startswith("fixed"):
        return ("Fixed", _uppercase_first_character(stripped_subject))
    if lowered_subject.startswith("add "):
        return ("Added", _uppercase_first_character(stripped_subject))
    return ("Changed", _uppercase_first_character(stripped_subject))


def format_release_section(release: ReleaseTag) -> str:
    section_heading, bullet_text = _categorize_subject(release.subject)
    return f"""## [{release.version}] - {release.released_on}

### {section_heading}
- {bullet_text}

---

"""


def build_updated_changelog(changelog_text: str, releases: list[ReleaseTag]) -> str:
    latest_documented_version = _latest_documented_version(changelog_text)
    existing_versions = set(extract_existing_release_versions(changelog_text))

    missing_releases = [
        release
        for release in releases
        if release.version not in existing_versions
        and (
            latest_documented_version is None
            or (release.major, release.minor) > latest_documented_version
        )
    ]

    if missing_releases == []:
        return changelog_text

    insert_index = _find_insert_index(changelog_text)
    generated_sections = "".join(format_release_section(release) for release in missing_releases)
    return f"""{changelog_text[:insert_index]}{generated_sections}{changelog_text[insert_index:]}"""


def sync_docs_changelog(repo_root: Path) -> Path | None:
    changelog_path = repo_root.joinpath(CHANGELOG_PATH)
    changelog_text = changelog_path.read_text(encoding="utf-8")
    updated_changelog_text = build_updated_changelog(
        changelog_text=changelog_text,
        releases=load_release_tags(repo_root=repo_root),
    )
    if updated_changelog_text == changelog_text:
        return None
    changelog_path.write_text(updated_changelog_text, encoding="utf-8")
    return changelog_path


def main() -> None:
    updated_path = sync_docs_changelog(repo_root=REPO_ROOT)
    if updated_path is None:
        print("docs/changelog.md is already up to date.")
        return
    print(updated_path.as_posix())


if __name__ == "__main__":
    main()
