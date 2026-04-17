import importlib.abc
import importlib.util
import io
import sys
import types
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

SUCCESS_LABEL = "success"
ISSUES_LABEL = "issues"
FAILURE_LABEL = "failure"
RUNNING_LABEL = "running"
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


DASHBOARD_SCRIPT_PATH = _repo_root() / "src" / "machineconfig" / "scripts" / "python" / "ai" / "scripts" / "dashboard.py"


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
    process: object
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
    summary_path: Path


def _read_report_stats(path: Path) -> ReportStats:
    if path.exists() is False:
        return ReportStats(line_count=0, byte_count=0)
    text = path.read_text(encoding="utf-8")
    return ReportStats(line_count=text.count("\n"), byte_count=len(text.encode("utf-8")))


def _build_models_fixture(base_dir: Path) -> ModelsFixture:
    reports_dir = base_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    summary_path = reports_dir / "summary.md"
    checker_specs = (
        CheckerSpec(slug="checker_a", title="Checker A", command=["checker-a", "--all"], report_path=reports_dir / "checker_a.md"),
        CheckerSpec(slug="checker_b", title="Checker B", command=["checker-b"], report_path=reports_dir / "checker_b.md"),
    )
    module = types.ModuleType("lint_and_type_check_models")
    setattr(module, "CHECKER_SPECS", checker_specs)
    setattr(module, "CLEANUP_COMMANDS", (["cleanup-one"], ["cleanup-two"]))
    setattr(module, "DONE_LABEL", DONE_LABEL)
    setattr(module, "ERROR_LABEL", ERROR_LABEL)
    setattr(module, "FAILURE_LABEL", FAILURE_LABEL)
    setattr(module, "ISSUES_LABEL", ISSUES_LABEL)
    setattr(module, "RUNNING_LABEL", RUNNING_LABEL)
    setattr(module, "START_FAILED_KIND", START_FAILED_KIND)
    setattr(module, "SUCCESS_LABEL", SUCCESS_LABEL)
    setattr(module, "SUMMARY_PATH", summary_path)
    setattr(module, "CleanupResult", CleanupResult)
    setattr(module, "RunningTool", RunningTool)
    setattr(module, "ToolResult", ToolResult)
    setattr(module, "format_bytes", lambda size: f"{size} B")
    setattr(module, "format_command", lambda command: " ".join(command))
    setattr(module, "format_diagnostic_distribution", lambda summary: "none" if summary.total_count == 0 else ", ".join(f"{bucket.label} {bucket.count}" for bucket in summary.buckets))
    setattr(module, "format_duration", lambda seconds: f"{seconds:.2f}s")
    setattr(module, "format_share", lambda duration, total: "0.00%" if total == 0 else f"{(duration / total) * 100:.2f}%")
    setattr(module, "read_report_stats", _read_report_stats)
    setattr(module, "relative_path", lambda path: str(path.relative_to(base_dir)))
    return ModelsFixture(module=module, checker_specs=checker_specs, summary_path=summary_path)


def _load_module(models_fixture: ModelsFixture, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, DASHBOARD_SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("failed to load dashboard script")
    module = importlib.util.module_from_spec(spec)
    sys.modules["models"] = models_fixture.module
    sys.modules["lint_and_type_check_models"] = models_fixture.module
    loader = spec.loader
    assert isinstance(loader, importlib.abc.Loader)
    loader.exec_module(module)
    return module


def test_checker_state_and_status_text_cover_runtime_states(tmp_path: Path) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    dashboard_module = _load_module(models_fixture=models_fixture, module_name="test_dashboard_states")
    success_result = ToolResult(
        spec=models_fixture.checker_specs[0],
        exit_code=0,
        started_at=1.0,
        finished_at=3.0,
        report_stats=ReportStats(line_count=1, byte_count=4),
        diagnostic_summary=DiagnosticSummary(
            total_count=0, classifier="unknown", buckets=()
        ),
        result_kind=COMPLETED_KIND,
    )
    failed_start_result = ToolResult(
        spec=models_fixture.checker_specs[1],
        exit_code=1,
        started_at=1.0,
        finished_at=2.0,
        report_stats=ReportStats(line_count=1, byte_count=4),
        diagnostic_summary=DiagnosticSummary(
            total_count=0, classifier="unknown", buckets=()
        ),
        result_kind=START_FAILED_KIND,
    )

    assert dashboard_module.checker_state_text(None).plain == RUNNING_LABEL
    assert dashboard_module.checker_state_text(success_result).plain == DONE_LABEL
    assert dashboard_module.checker_state_text(failed_start_result).plain == ERROR_LABEL
    assert dashboard_module.checker_status_text(success_result).plain == SUCCESS_LABEL
    assert dashboard_module.checker_status_text(failed_start_result).plain == FAILURE_LABEL


def test_build_command_preview_lists_cleanup_and_checker_commands(tmp_path: Path) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    dashboard_module = _load_module(models_fixture=models_fixture, module_name="test_dashboard_preview")
    stream = io.StringIO()
    console = Console(file=stream, width=120, force_terminal=False, color_system=None)

    console.print(dashboard_module.build_command_preview())
    output = stream.getvalue()

    assert "Commands To Execute" in output
    assert "cleanup-one" in output
    assert "checker-a --all" in output
    assert "Checker B" in output


def test_build_final_summary_renders_totals_and_summary_path(tmp_path: Path) -> None:
    models_fixture = _build_models_fixture(base_dir=tmp_path)
    dashboard_module = _load_module(models_fixture=models_fixture, module_name="test_dashboard_summary")
    cleanup_result = CleanupResult(
        exit_code=0,
        started_at=0.0,
        finished_at=2.0,
        report_path=tmp_path / "reports" / "cleanup.md",
        report_stats=ReportStats(line_count=1, byte_count=4),
    )
    checker_results = (
        ToolResult(
            spec=models_fixture.checker_specs[0],
            exit_code=0,
            started_at=2.0,
            finished_at=5.0,
            report_stats=ReportStats(line_count=1, byte_count=4),
            diagnostic_summary=DiagnosticSummary(
                total_count=0, classifier="unknown", buckets=()
            ),
            result_kind=COMPLETED_KIND,
        ),
        ToolResult(
            spec=models_fixture.checker_specs[1],
            exit_code=0,
            started_at=2.0,
            finished_at=6.0,
            report_stats=ReportStats(line_count=2, byte_count=8),
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
    stream = io.StringIO()
    console = Console(file=stream, width=120, force_terminal=False, color_system=None)

    console.print(
        dashboard_module.build_final_summary(
            cleanup_result=cleanup_result,
            checker_results=checker_results,
            wall_started_at=0.0,
        )
    )
    output = stream.getvalue()

    assert "passed tools: 1/2" in output
    assert "tools with issues: 1/2" in output
    assert "summary file: reports/summary.md" in output
    assert "Checker B" in output
    assert "Diagnostics" in output
    assert "F401 2, UP006 1" in output
