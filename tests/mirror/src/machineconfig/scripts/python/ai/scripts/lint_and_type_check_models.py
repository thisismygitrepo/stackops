from __future__ import annotations

from pathlib import Path

from machineconfig.scripts.python.ai.scripts import lint_and_type_check_models as models_module


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
    models_module.write_start_failure(
        report_path=failure_path,
        title="Ruff Linter",
        command=("uv", "run", "ruff"),
        error=OSError("boom"),
    )

    assert failure_path.read_text(encoding="utf-8") == (
        "# Ruff Linter\n\n"
        "- Command: `uv run ruff`\n"
        "- Start failure: `boom`\n\n"
    )


def test_result_models_derive_runtime_status_fields() -> None:
    spec = models_module.ToolSpec(
        slug="ruff",
        title="Ruff Linter",
        report_path=Path(".ai/linters/issues_ruff.md"),
        command=("uv", "run", "ruff"),
    )
    report_stats = models_module.ReportStats(line_count=3, byte_count=42)

    cleanup_result = models_module.CleanupResult(
        exit_code=0,
        started_at=2.0,
        finished_at=4.5,
        report_path=Path(".ai/linters/cleanup.md"),
        report_stats=report_stats,
    )
    failed_cleanup_result = models_module.CleanupResult(
        exit_code=1,
        started_at=2.0,
        finished_at=5.0,
        report_path=Path(".ai/linters/cleanup.md"),
        report_stats=report_stats,
    )
    completed_tool_result = models_module.ToolResult(
        spec=spec,
        exit_code=1,
        started_at=10.0,
        finished_at=13.5,
        report_stats=report_stats,
        result_kind=models_module.COMPLETED_KIND,
    )
    failed_tool_result = models_module.ToolResult(
        spec=spec,
        exit_code=1,
        started_at=10.0,
        finished_at=11.0,
        report_stats=report_stats,
        result_kind=models_module.START_FAILED_KIND,
    )

    assert cleanup_result.duration_seconds == 2.5
    assert cleanup_result.status == models_module.SUCCESS_LABEL
    assert failed_cleanup_result.status == models_module.FAILURE_LABEL
    assert completed_tool_result.duration_seconds == 3.5
    assert completed_tool_result.run_state == models_module.DONE_LABEL
    assert completed_tool_result.status == models_module.ISSUES_LABEL
    assert failed_tool_result.run_state == models_module.ERROR_LABEL
    assert failed_tool_result.status == models_module.FAILURE_LABEL
