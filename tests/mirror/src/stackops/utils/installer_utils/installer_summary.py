from __future__ import annotations

from rich.console import Console

from stackops.utils.installer_utils import installer_summary as summary
from stackops.utils.schemas.installer.installer_types import (
    InstallationResult,
    InstallationResultFailed,
    InstallationResultSameVersion,
    InstallationResultSkipped,
    InstallationResultUpdated,
)


def test_format_installation_result_formats_all_result_kinds() -> None:
    skipped: InstallationResultSkipped = {
        "kind": "skipped",
        "appName": "Demo App",
        "exeName": "demo",
        "emoji": "⏭️",
        "detail": "skipped by user",
    }
    same_version: InstallationResultSameVersion = {
        "kind": "same_version",
        "appName": "Demo App",
        "exeName": "demo",
        "emoji": "😑",
        "version": "1.2.3",
    }
    updated: InstallationResultUpdated = {
        "kind": "updated",
        "appName": "Demo App",
        "exeName": "demo",
        "emoji": "🤩",
        "oldVersion": "1.0.0",
        "newVersion": "2.0.0",
    }
    failed: InstallationResultFailed = {
        "kind": "failed",
        "appName": "Demo App",
        "exeName": "demo",
        "emoji": "❌",
        "error": "boom",
    }

    assert summary.format_installation_result(skipped) == "📦️ ⏭️ demo skipped by user"
    assert summary.format_installation_result(same_version) == "📦️ 😑 demo, same version: 1.2.3"
    assert (
        summary.format_installation_result(updated)
        == "📦️ 🤩 demo updated from 1.0.0 ➡️ TO ➡️  2.0.0"
    )
    assert (
        summary.format_installation_result(failed)
        == "📦️ ❌ Failed to install `Demo App` with error: boom"
    )


def test_render_installation_summary_uses_compact_fallback_values() -> None:
    console = Console(record=True, width=120)
    results: list[InstallationResult] = [
        {
            "kind": "same_version",
            "appName": "Stable",
            "exeName": "stable",
            "emoji": "😑",
            "version": "   ",
        },
        {
            "kind": "updated",
            "appName": "Fresh",
            "exeName": "fresh",
            "emoji": "🤩",
            "oldVersion": "  old \n",
            "newVersion": " new \n",
        },
        {
            "kind": "skipped",
            "appName": "Later",
            "exeName": "later",
            "emoji": "⏭️",
            "detail": "   ",
        },
        {
            "kind": "failed",
            "appName": "Broken",
            "exeName": "broken",
            "emoji": "❌",
            "error": "   ",
        },
    ]

    summary.render_installation_summary(results=results, console=console, title="Install")

    output = console.export_text()

    assert "Same Version Apps" in output
    assert "Updated Apps" in output
    assert "Skipped Apps" in output
    assert "Failed Apps" in output
    assert "not detected" in output
    assert "n/a" in output
    assert "unknown error" in output
