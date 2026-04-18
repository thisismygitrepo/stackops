import importlib.abc
import importlib.util
import io
import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import pytest
from rich.console import Console

SUCCESS_LABEL = "success"
ISSUES_LABEL = "issues"
FAILURE_LABEL = "failure"
DONE_LABEL = "done"
ERROR_LABEL = "error"
START_FAILED_KIND = "start_failed"
COMPLETED_KIND = "completed"


def _repo_root() -> Path:
    current_path = Path(__file__).resolve()
    for parent in current_path.parents:
        if parent.joinpath("pyproject.toml").exists() and parent.joinpath("src", "machineconfig").exists():
            return parent
    raise AssertionError("repo root not found")


LINT_SCRIPT_PATH = _repo_root() / "src" / "machineconfig" / "scripts" / "python" / "ai" / "scripts" / "lint_and_type_check.py"


class ProcessLike(Protocol):
    def poll(self) -> int | None: ...
    def terminate(self) -> None: ...
    def wait(self, timeout: float) -> int: ...


@dataclass(slots=True)
class ReportStats:
    line_count: int
    byte_count: int


@dataclass(slots=True)
class DiagnosticBucket:
    label: str
    count: int


@dataclass(slots=True)
class DiagnosticSummary:
    total_count: int
    classifier: str
    buckets: tuple[DiagnosticBucket, ...]


@dataclass(slots=True)
class CheckerSpec:
    slug: str
    title: str
    command: list[str]
    report_path: Path


@dataclass(slots=True)
class CleanupResult:
    exit_code: int
    started_at: float
    finished_at: float
    report_path: Path
    report_stats: ReportStats

    @property
    def status(self) -> str:
        return SUCCESS_LABEL if self.exit_code == 0 else FAILURE_LABEL

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at


@dataclass(slots=True)
class RunningTool:
    spec: CheckerSpec
    process: ProcessLike
    report_handle: io.TextIOBase
    started_at: float


@dataclass(slots=True)
class ToolResult:
    spec: CheckerSpec
    exit_code: int
    started_at: float
    finished_at: float
    report_stats: ReportStats
    diagnostic_summary: DiagnosticSummary
    result_kind: str

    @property
    def duration_seconds(self) -> float:
        return self.finished_at - self.started_at

    @property
    def status(self) -> str:
        if self.result_kind == START_FAILED_KIND:
            return FAILURE_LABEL
        if self.diagnostic_summary.total_count > 0:
            return ISSUES_LABEL
        if self.exit_code == 0:
            return SUCCESS_LABEL
        return ISSUES_LABEL

    @property
    def run_state(self) -> str:
        return ERROR_LABEL if self.result_kind == START_FAILED_KIND else DONE_LABEL


@dataclass(slots=True)
class ModelsFixture:
    module: types.ModuleType
    checker_specs: tuple[CheckerSpec, CheckerSpec]
    reports_dir: Path
    repo_marker: Path
    summary_path: Path


@dataclass(slots=True)
class CompletedRun:
    returncode: int
    stdout: str


class FakeProcess:
    def poll(self) -> int | None:
        return None

    def terminate(self) -> None:
        return None

    def wait(self, timeout: float) -> int:
        return 0


def _read_report_stats(path: Path) -> ReportStats:
    if path.exists() is False:
        return ReportStats(line_count=0, byte_count=0)
    text = path.read_text(encoding="utf-8")
    return ReportStats(line_count=text.count("\n"), byte_count=len(text.encode("utf-8")))


def _build_models_fixture(base_dir: Path) -> ModelsFixture:
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    repo_marker = base_dir / "pyproject.toml"
    summary_path = reports_dir / "summary.md"
    checker_specs = (
        CheckerSpec(slug="checker_a", title="Checker A", command=["checker-a"], report_path=reports_dir / "checker_a.md"),
        CheckerSpec(slug="checker_b", title="Checker B", command=["checker-b"], report_path=reports_dir / "checker_b.md"),
    )
    module = types.ModuleType("lint_and_type_check_models")
    setattr(module, "CHECKER_REFRESH_SECONDS", 0.0)
    setattr(module, "CHECKER_SPECS", checker_specs)
    setattr(module, "CLEANUP_COMMANDS", (["cleanup-one"], ["cleanup-two"]))
    setattr(module, "COMPLETED_KIND", COMPLETED_KIND)
    setattr(module, "FAILURE_LABEL", FAILURE_LABEL)
    setattr(module, "ISSUES_LABEL", ISSUES_LABEL)
    setattr(module, "REPORTS_DIR", reports_dir)
    setattr(module, "REPO_MARKER", repo_marker)
    setattr(module, "START_FAILED_KIND", START_FAILED_KIND)
    setattr(module, "SUCCESS_LABEL", SUCCESS_LABEL)
    setattr(module, "SUMMARY_PATH", summary_path)
    setattr(module, "CleanupResult", CleanupResult)
    setattr(module, "DiagnosticSummary", DiagnosticSummary)
    setattr(module, "RunningTool", RunningTool)
    setattr(module, "ToolResult", ToolResult)
    setattr(module, "build_diagnostic_summary", lambda tool_slug, raw_output: DiagnosticSummary(total_count=1 if raw_output.strip() != "" else 0, classifier="rule", buckets=(DiagnosticBucket(label=tool_slug, count=1),) if raw_output.strip() != "" else ()))
    setattr(module, "format_bytes", lambda size: f"{size} B")
    setattr(module, "format_diagnostic_distribution", lambda summary: "none" if summary.total_count == 0 else ", ".join(f"{bucket.label} {bucket.count}" for bucket in summary.buckets))
    setattr(module, "format_duration", lambda seconds: f"{seconds:.2f}s")
    setattr(module, "format_share", lambda duration, total: "0.00%" if total == 0 else f"{(duration / total) * 100:.2f}%")
    setattr(module, "format_tool_report", lambda spec, exit_code, raw_output: f"# {spec.title}\n\n- Exit code: {exit_code}\n\n{raw_output}")
    setattr(module, "read_report_stats", _read_report_stats)
    setattr(module, "relative_path", lambda path: str(path.relative_to(base_dir)))

    def write_start_failure(report_path: Path, title: str, command: list[str], error: OSError) -> None:
        report_path.write_text(
            f"# {title}\n{" ".join(command)}\n{error.strerror}",
            encoding="utf-8",
        )

    setattr(module, "write_start_failure", write_start_failure)
    return ModelsFixture(
        module=module,
        checker_specs=checker_specs,
        reports_dir=reports_dir,
        repo_marker=repo_marker,
        summary_path=summary_path,
    )


def _load_module(monkeypatch: pytest.MonkeyPatch, models_fixture: ModelsFixture, module_name: str) -> types.ModuleType:
    dashboard_module = types.ModuleType("lint_and_type_check_dashboard")
    setattr(dashboard_module, "build_command_preview", lambda: "preview")
    setattr(dashboard_module, "build_final_summary", lambda cleanup_result, checker_results, wall_started_at: "summary")
    setattr(dashboard_module, "build_live_renderable", lambda repo_root, cleanup_result, running_tools, completed_tools, wall_started_at: "live")

    monkeypatch.setitem(sys.modules, "models", models_fixture.module)
    monkeypatch.setitem(sys.modules, "lint_and_type_check_models", models_fixture.module)
    monkeypatch.setitem(sys.modules, "dashboard", dashboard_module)
    monkeypatch.setitem(sys.modules, "lint_and_type_check_dashboard", dashboard_module)

    spec = importlib.util.spec_from_file_location(module_name, LINT_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load lint script")
    module = importlib.util.module_from_spec(spec)
    loader = spec.loader
    assert isinstance(loader, importlib.abc.Loader)
    loader.exec_module(module)
    return module


def test_run_cleanup_writes_log_and_uses_first_failure_exit_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    lint_module = _load_module(monkeypatch=monkeypatch, models_fixture=models_fixture, module_name="test_lint_script_cleanup")
    results = iter([CompletedRun(returncode=3, stdout="first output\n"), CompletedRun(returncode=0, stdout="second output\n")])
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/outer-env")
    monkeypatch.setenv("UNCHANGED_ENV", "keep-me")

    def fake_run(
        command: list[str],
        env: dict[str, str],
        stdout: object,
        stderr: object,
        text: bool,
        check: bool,
    ) -> CompletedRun:
        assert stdout == lint_module.subprocess.PIPE
        assert stderr == lint_module.subprocess.STDOUT
        assert text is True
        assert check is False
        assert env["UNCHANGED_ENV"] == "keep-me"
        assert "VIRTUAL_ENV" not in env
        return next(results)

    monkeypatch.setattr(lint_module.subprocess, "run", fake_run)
    console = Console(file=io.StringIO(), force_terminal=False, color_system=None)
    cleanup_result = lint_module.run_cleanup(console=console)
    cleanup_log = (models_fixture.reports_dir / "log_cleanup.md").read_text(encoding="utf-8")

    assert cleanup_result.exit_code == 3
    assert "$ cleanup-one" in cleanup_log
    assert "first output" in cleanup_log
    assert "$ cleanup-two" in cleanup_log
    assert "second output" in cleanup_log


def test_validate_environment_checks_marker_and_uv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    lint_module = _load_module(monkeypatch=monkeypatch, models_fixture=models_fixture, module_name="test_lint_script_validate")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(lint_module.shutil, "which", lambda name: "/usr/bin/uv")

    with pytest.raises(SystemExit) as exit_info:
        lint_module.validate_environment()

    assert exit_info.value.code == 1
    models_fixture.repo_marker.write_text("[project]\nname='demo'\n", encoding="utf-8")
    repo_root = lint_module.validate_environment()

    assert repo_root == tmp_path
    assert models_fixture.reports_dir.is_dir()


def test_start_checker_processes_records_launch_failures(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    lint_module = _load_module(monkeypatch=monkeypatch, models_fixture=models_fixture, module_name="test_lint_script_start")
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/outer-env")
    monkeypatch.setenv("UNCHANGED_ENV", "keep-me")

    def fake_popen(
        command: list[str], env: dict[str, str], stdout: io.TextIOBase, stderr: object
    ) -> FakeProcess:
        assert stderr == lint_module.subprocess.STDOUT
        assert env["UNCHANGED_ENV"] == "keep-me"
        assert "VIRTUAL_ENV" not in env
        if command[0] == "checker-a":
            raise OSError(2, "boom", "checker-a")
        return FakeProcess()

    monkeypatch.setattr(lint_module.subprocess, "Popen", fake_popen)
    running_tools, completed_tools = lint_module.start_checker_processes()

    assert set(running_tools) == {"checker_b"}
    assert completed_tools["checker_a"].result_kind == START_FAILED_KIND
    assert "boom" in models_fixture.checker_specs[0].report_path.read_text(encoding="utf-8")


def test_build_subprocess_environment_strips_virtual_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    lint_module = _load_module(
        monkeypatch=monkeypatch,
        models_fixture=models_fixture,
        module_name="test_lint_script_subprocess_environment",
    )
    monkeypatch.setenv("VIRTUAL_ENV", "/tmp/outer-env")
    monkeypatch.setenv("UNCHANGED_ENV", "keep-me")

    subprocess_environment = lint_module.build_subprocess_environment()

    assert subprocess_environment["UNCHANGED_ENV"] == "keep-me"
    assert "VIRTUAL_ENV" not in subprocess_environment
    assert os.environ["VIRTUAL_ENV"] == "/tmp/outer-env"


def test_finish_ready_processes_formats_captured_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    lint_module = _load_module(monkeypatch=monkeypatch, models_fixture=models_fixture, module_name="test_lint_script_finish")

    class FinishedProcess:
        def poll(self) -> int | None:
            return 1

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float) -> int:
            return 1

    running_tools = {
        "checker_a": RunningTool(
            spec=models_fixture.checker_specs[0],
            process=FinishedProcess(),
            report_handle=io.StringIO('[{"message":"boom"}]'),
            started_at=10.0,
        )
    }
    completed_tools: dict[str, ToolResult] = {}

    lint_module.finish_ready_processes(running_tools=running_tools, completed_tools=completed_tools)

    report_text = models_fixture.checker_specs[0].report_path.read_text(encoding="utf-8")
    assert report_text.startswith("# Checker A")
    assert "- Exit code: 1" in report_text
    assert '[{"message":"boom"}]' in report_text
    assert completed_tools["checker_a"].diagnostic_summary.total_count == 1


def test_write_summary_appends_diagnostic_distribution_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    lint_module = _load_module(
        monkeypatch=monkeypatch,
        models_fixture=models_fixture,
        module_name="test_lint_script_write_summary",
    )
    cleanup_result = CleanupResult(
        exit_code=0,
        started_at=1.0,
        finished_at=2.0,
        report_path=models_fixture.reports_dir / "cleanup.md",
        report_stats=ReportStats(line_count=1, byte_count=4),
    )
    checker_results = (
        ToolResult(
            spec=models_fixture.checker_specs[0],
            exit_code=0,
            started_at=2.0,
            finished_at=4.0,
            report_stats=ReportStats(line_count=1, byte_count=8),
            diagnostic_summary=DiagnosticSummary(
                total_count=0, classifier="unknown", buckets=()
            ),
            result_kind=COMPLETED_KIND,
        ),
        ToolResult(
            spec=models_fixture.checker_specs[1],
            exit_code=0,
            started_at=2.0,
            finished_at=5.0,
            report_stats=ReportStats(line_count=2, byte_count=16),
            diagnostic_summary=DiagnosticSummary(
                total_count=3,
                classifier="rule",
                buckets=(
                    DiagnosticBucket(label="F401", count=2),
                    DiagnosticBucket(label="UP006", count=1),
                ),
            ),
            result_kind=COMPLETED_KIND,
        ),
    )

    lint_module.write_summary(
        cleanup_result=cleanup_result,
        checker_results=checker_results,
        wall_started_at=1.0,
    )
    summary_text = models_fixture.summary_path.read_text(encoding="utf-8")

    assert "## Diagnostic Distribution" in summary_text
    assert "| Tool | Outcome | Diagnostics | By | Distribution |" in summary_text
    assert "| Checker B | issues | 3 | rule | F401 2, UP006 1 |" in summary_text
