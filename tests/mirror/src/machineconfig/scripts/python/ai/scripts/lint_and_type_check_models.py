import importlib
import json
from pathlib import Path

import pytest

from machineconfig.scripts.python.ai.scripts import models as models_module


def test_format_helpers_cover_runtime_branches() -> None:
    assert models_module.format_duration(12.345) == "12.35s"
    assert models_module.format_duration(90.5) == "1m 30.50s"
    assert models_module.format_bytes(512) == "512 B"
    assert models_module.format_bytes(1536) == "1.5 KB"
    assert models_module.format_share(1.0, 4.0) == "25.0%"
    assert models_module.format_share(1.0, 0.0) == "0.0%"
    assert models_module.relative_path(Path("nested") / "report.md") == "./nested/report.md"
    assert models_module.format_command(("uv", "run", "pyright")) == "uv run pyright"


def test_read_report_stats_and_write_start_failure_use_filesystem_state(tmp_path: Path) -> None:
    missing_stats = models_module.read_report_stats(tmp_path / "missing.md")
    assert missing_stats == models_module.ReportStats(line_count=0, byte_count=0)

    report_path = tmp_path / "report.md"
    report_path.write_text("one\ntwo\n", encoding="utf-8")

    stats = models_module.read_report_stats(report_path)

    assert stats.line_count == 2
    assert stats.byte_count == report_path.stat().st_size

    failure_path = tmp_path / "failure.md"
    models_module.write_start_failure(report_path=failure_path, title="Ruff Linter", command=("uv", "run", "ruff"), error=OSError("boom"))

    assert failure_path.read_text(encoding="utf-8") == ("# Ruff Linter\n\n- Command: `uv run ruff`\n- Start failure: `boom`\n\n")


def test_result_models_derive_runtime_status_fields() -> None:
    spec = models_module.ToolSpec(
        slug="ruff",
        title="Ruff Linter",
        report_path=Path(".ai/linters/issues_ruff.md"),
        command=("uv", "run", "ruff"),
        output_format="json",
    )
    report_stats = models_module.ReportStats(line_count=3, byte_count=42)

    cleanup_result = models_module.CleanupResult(
        exit_code=0, started_at=2.0, finished_at=4.5, report_path=Path(".ai/linters/cleanup.md"), report_stats=report_stats
    )
    failed_cleanup_result = models_module.CleanupResult(
        exit_code=1, started_at=2.0, finished_at=5.0, report_path=Path(".ai/linters/cleanup.md"), report_stats=report_stats
    )
    completed_tool_result = models_module.ToolResult(
        spec=spec, exit_code=1, started_at=10.0, finished_at=13.5, report_stats=report_stats, result_kind=models_module.COMPLETED_KIND
    )
    failed_tool_result = models_module.ToolResult(
        spec=spec, exit_code=1, started_at=10.0, finished_at=11.0, report_stats=report_stats, result_kind=models_module.START_FAILED_KIND
    )

    assert cleanup_result.duration_seconds == 2.5
    assert cleanup_result.status == models_module.SUCCESS_LABEL
    assert failed_cleanup_result.status == models_module.FAILURE_LABEL
    assert completed_tool_result.duration_seconds == 3.5
    assert completed_tool_result.run_state == models_module.DONE_LABEL
    assert completed_tool_result.status == models_module.ISSUES_LABEL
    assert failed_tool_result.run_state == models_module.ERROR_LABEL
    assert failed_tool_result.status == models_module.FAILURE_LABEL


def test_checker_specs_request_structured_output() -> None:
    checker_commands = {spec.slug: spec.command for spec in models_module.CHECKER_SPECS}

    assert "--outputjson" in checker_commands["pyright"]
    assert checker_commands["mypy"][checker_commands["mypy"].index("-O") + 1] == "json"
    assert checker_commands["mypy"][checker_commands["mypy"].index("--exclude") + 1] == r"(^|/|\\)gromit-mpx($|/|\\)"
    assert "--output-format=json2" in checker_commands["pylint"]
    assert "--no-progress-bar" not in checker_commands["pyrefly"]
    assert "--summary=none" in checker_commands["pyrefly"]
    assert checker_commands["pyrefly"][checker_commands["pyrefly"].index("--output-format") + 1] == "json"
    assert checker_commands["ty"][checker_commands["ty"].index("--output-format") + 1] == "gitlab"
    assert checker_commands["ruff"][checker_commands["ruff"].index("--output-format") + 1] == "json"


def test_checker_specs_append_environment_excludes_and_generate_pyright_override(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pyright_config_path = tmp_path / "pyrightconfig.json"
    pyright_config_path.write_text(
        (
            "{\n"
            "  \"venvPath\": \".\",\n"
            "  \"exclude\": [\n"
            "    \"tests\",\n"
            "  ],\n"
            "  // comment preserved by jsonc stripping\n"
            "}\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        models_module.TYPE_CHECK_EXCLUDES_ENV_VAR,
        json.dumps(["src/generated", "tests"]),
    )
    reloaded_module = importlib.reload(models_module)
    generated_pattern = r"(^|/|\\)src(/|\\)generated($|/|\\)"
    tests_pattern = r"(^|/|\\)tests($|/|\\)"
    try:
        checker_commands = {
            spec.slug: spec.command for spec in reloaded_module.CHECKER_SPECS
        }
        cleanup_commands = reloaded_module.CLEANUP_COMMANDS
        pyright_override_path = tmp_path / ".machineconfig.pyright.type-check.json"
        pyright_override = json.loads(
            pyright_override_path.read_text(encoding="utf-8")
        )

        assert checker_commands["pyright"][
            checker_commands["pyright"].index("--project") + 1
        ] == str(reloaded_module.PYRIGHT_CONFIG_OVERRIDE_PATH)
        assert pyright_override == {
            "extends": "./pyrightconfig.json",
            "exclude": ["tests", "src/generated"],
        }
        assert checker_commands["mypy"][
            checker_commands["mypy"].index("--exclude") + 1
        ] == r"(^|/|\\)gromit-mpx($|/|\\)"
        assert generated_pattern in checker_commands["mypy"]
        assert tests_pattern in checker_commands["mypy"]
        assert checker_commands["pylint"][
            checker_commands["pylint"].index("--ignore-paths") + 1
        ] == f"(?:{generated_pattern})|(?:{tests_pattern})"
        assert checker_commands["pyrefly"][
            checker_commands["pyrefly"].index("--project-excludes") + 1
        ] == "src/generated"
        assert checker_commands["ty"][
            checker_commands["ty"].index("--exclude") + 1
        ] == "src/generated"
        assert "--force-exclude" in checker_commands["ty"]
        assert checker_commands["ruff"][
            checker_commands["ruff"].index("--extend-exclude") + 1
        ] == "src/generated"
        assert "--force-exclude" in checker_commands["ruff"]
        assert cleanup_commands[0][
            cleanup_commands[0].index("--exclude") + 1
        ] == generated_pattern
        assert cleanup_commands[2][
            cleanup_commands[2].index("--extend-exclude") + 1
        ] == "src/generated"
    finally:
        monkeypatch.delenv(
            models_module.TYPE_CHECK_EXCLUDES_ENV_VAR, raising=False
        )
        importlib.reload(models_module)


def test_format_tool_report_splits_json_diagnostics_into_sections() -> None:
    spec = models_module.ToolSpec(
        slug="pyright",
        title="Pyright Type Checker",
        report_path=Path(".ai/linters/issues_pyright.md"),
        command=("uv", "run", "pyright"),
        output_format="json",
    )

    report = models_module.format_tool_report(
        spec=spec,
        exit_code=1,
        raw_output=(
            '{"summary": {"errorCount": 1}, "generalDiagnostics": ['
            '{"file": "demo.py", "severity": "error", "message": "boom"}]}'
        ),
    )

    assert "- Diagnostic entries: `1`" in report
    assert "## Metadata" in report
    assert "## Diagnostics" in report
    assert "### Diagnostic 1" in report
    assert '"file": "demo.py"' in report


def test_format_tool_report_falls_back_to_raw_text_on_invalid_json() -> None:
    spec = models_module.ToolSpec(
        slug="pyright",
        title="Pyright Type Checker",
        report_path=Path(".ai/linters/issues_pyright.md"),
        command=("uv", "run", "pyright"),
        output_format="json",
    )

    report = models_module.format_tool_report(
        spec=spec,
        exit_code=2,
        raw_output="not json",
    )

    assert "JSON parse failure" in report
    assert "## Raw Output" in report
    assert "not json" in report


def test_format_tool_report_recovers_json_after_prefix_lines() -> None:
    spec = models_module.ToolSpec(
        slug="ruff",
        title="Ruff Linter",
        report_path=Path(".ai/linters/issues_ruff.md"),
        command=("uv", "run", "ruff"),
        output_format="json",
    )

    report = models_module.format_tool_report(
        spec=spec,
        exit_code=0,
        raw_output="warning: prefix line\n[]\n",
    )

    assert "## Prefix" in report
    assert "warning: prefix line" in report
    assert "## Diagnostics" in report
    assert "No diagnostics reported." in report


def test_format_tool_report_splits_json_stream_diagnostics_into_sections() -> None:
    spec = models_module.ToolSpec(
        slug="mypy",
        title="MyPy Type Checker",
        report_path=Path(".ai/linters/issues_mypy.md"),
        command=("uv", "run", "mypy"),
        output_format="json",
    )

    report = models_module.format_tool_report(
        spec=spec,
        exit_code=1,
        raw_output=(
            "warning: prefix line\n"
            '{"file": "demo.py", "line": -1, "message": "context", "severity": "note"}\n'
            '{"file": "demo.py", "line": 1, "message": "boom", "severity": "error"}\n'
        ),
    )

    assert "## Prefix" in report
    assert "warning: prefix line" in report
    assert "- Diagnostic entries: `2`" in report
    assert "### Diagnostic 1" in report
    assert "### Diagnostic 2" in report
    assert '"severity": "error"' in report
