from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
from runpy import run_path
import sys
from typing import cast

import pytest


REPO_ROOT = Path(__file__).resolve().parents[6]
SCRIPT_PATH = REPO_ROOT / ".github" / "skills" / "make-github-installer-config" / "scripts" / "upsert_installer_data.py"


def _load_script_namespace() -> dict[str, object]:
    return run_path(str(SCRIPT_PATH))


def _pattern_matrix() -> dict[str, dict[str, str | None]]:
    return {
        "amd64": {"linux": "tool-{version}-linux-amd64.tar.gz", "darwin": None, "windows": None},
        "arm64": {"linux": None, "darwin": None, "windows": None},
    }


def test_collect_warning_rows_merges_pattern_and_license_warnings() -> None:
    namespace = _load_script_namespace()
    collect_warning_rows = cast(Callable[[object], list[str]], namespace["collect_warning_rows"])

    warnings = collect_warning_rows({"latestPatternChecks": ["missing linux asset", 5], "licenseWarning": "license missing"})

    assert warnings == ["missing linux asset", "license missing"]


def test_main_updates_first_match_removes_duplicates_and_writes_backup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    namespace = _load_script_namespace()
    main = cast(Callable[[], None], namespace["main"])
    installer_path = tmp_path / "installer_data.json"
    entry_path = tmp_path / "entry.json"

    installer_path.write_text(
        json.dumps(
            {
                "installers": [
                    {
                        "appName": "tool",
                        "license": "Old",
                        "repoURL": "https://github.com/acme/tool",
                        "doc": "old doc",
                        "fileNamePattern": _pattern_matrix(),
                    },
                    {
                        "appName": "duplicate",
                        "license": "Old",
                        "repoURL": "https://github.com/acme/tool",
                        "doc": "duplicate",
                        "fileNamePattern": _pattern_matrix(),
                    },
                    {
                        "appName": "keep",
                        "license": "MIT",
                        "repoURL": "https://github.com/acme/keep",
                        "doc": "keep doc",
                        "fileNamePattern": _pattern_matrix(),
                    },
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    entry_path.write_text(
        json.dumps(
            {
                "entry": {
                    "appName": "tool",
                    "license": "MIT",
                    "repoURL": "https://github.com/acme/tool",
                    "doc": "new doc",
                    "fileNamePattern": _pattern_matrix(),
                },
                "checks": {"latestPatternChecks": [], "licenseWarning": None},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(sys, "argv", ["upsert_installer_data.py", "--installer-data", str(installer_path), "--entry-json", str(entry_path)])

    main()

    payload = json.loads(installer_path.read_text(encoding="utf-8"))
    installers = cast(list[dict[str, object]], payload["installers"])

    assert [row["appName"] for row in installers] == ["tool", "keep"]
    assert installers[0]["doc"] == "new doc"
    assert len(list(tmp_path.glob("installer_data.json.*.bak"))) == 1


def test_main_refuses_to_write_when_warning_checks_fail(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    namespace = _load_script_namespace()
    main = cast(Callable[[], None], namespace["main"])
    installer_path = tmp_path / "installer_data.json"
    entry_path = tmp_path / "entry.json"

    installer_path.write_text(json.dumps({"installers": []}) + "\n", encoding="utf-8")
    before_text = installer_path.read_text(encoding="utf-8")
    entry_path.write_text(
        json.dumps(
            {
                "entry": {
                    "appName": "tool",
                    "license": "MIT",
                    "repoURL": "https://github.com/acme/tool",
                    "doc": "new doc",
                    "fileNamePattern": _pattern_matrix(),
                },
                "checks": {"latestPatternChecks": ["missing windows"], "licenseWarning": None},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["upsert_installer_data.py", "--installer-data", str(installer_path), "--entry-json", str(entry_path), "--fail-on-check-warnings"],
    )

    with pytest.raises(RuntimeError, match="Refusing upsert"):
        main()

    assert installer_path.read_text(encoding="utf-8") == before_text
