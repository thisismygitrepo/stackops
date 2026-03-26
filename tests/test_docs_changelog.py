from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

from machineconfig.scripts.python.helpers.helpers_devops import docs_changelog


def test_build_updated_changelog_inserts_newer_releases_before_existing_entries() -> None:
    changelog_text = dedent(
        """
        # Changelog

        ## [Unreleased]

        ### Added
        - Placeholder

        ---

        ## [8.28] - 2025-12-03

        ### Added
        - Existing manual notes

        ---

        ## Supported Platforms
        """
    ).lstrip()

    releases = [
        docs_changelog.ReleaseTag(
            version="8.85",
            released_on="2026-03-25",
            subject="feat: enhance CLI commands with no_args_is_help option for better usability",
            major=8,
            minor=85,
        ),
        docs_changelog.ReleaseTag(
            version="8.84",
            released_on="2026-03-24",
            subject="new release",
            major=8,
            minor=84,
        ),
        docs_changelog.ReleaseTag(
            version="8.28",
            released_on="2025-12-03",
            subject="feat: existing manual release",
            major=8,
            minor=28,
        ),
    ]

    updated_changelog = docs_changelog.build_updated_changelog(
        changelog_text=changelog_text,
        releases=releases,
    )

    assert "## [8.85] - 2026-03-25" in updated_changelog
    assert "### Added\n- Enhance CLI commands with no_args_is_help option for better usability" in updated_changelog
    assert "## [8.84] - 2026-03-24" in updated_changelog
    assert "### Changed\n- New release" in updated_changelog
    assert updated_changelog.index("## [8.85] - 2026-03-25") < updated_changelog.index("## [8.84] - 2026-03-24")
    assert updated_changelog.index("## [8.84] - 2026-03-24") < updated_changelog.index("## [8.28] - 2025-12-03")
    assert docs_changelog.build_updated_changelog(
        changelog_text=updated_changelog,
        releases=releases,
    ) == updated_changelog


def test_sync_docs_changelog_writes_generated_release_entries(tmp_path: Path) -> None:
    changelog_path = tmp_path.joinpath("docs", "changelog.md")
    changelog_path.parent.mkdir(parents=True)
    changelog_path.write_text(
        dedent(
            """
            # Changelog

            ## [Unreleased]

            ---

            ## [8.28] - 2025-12-03

            ### Added
            - Existing manual notes
            """
        ).lstrip(),
        encoding="utf-8",
    )

    releases = [
        docs_changelog.ReleaseTag(
            version="8.29",
            released_on="2025-12-04",
            subject="fix: repair changelog sync",
            major=8,
            minor=29,
        ),
    ]

    with patch.object(docs_changelog, "load_release_tags", return_value=releases):
        updated_path = docs_changelog.sync_docs_changelog(repo_root=tmp_path)

    assert updated_path == changelog_path
    updated_text = changelog_path.read_text(encoding="utf-8")
    assert "## [8.29] - 2025-12-04" in updated_text
    assert "### Fixed\n- Repair changelog sync" in updated_text
