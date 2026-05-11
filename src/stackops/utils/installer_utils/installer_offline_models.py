from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypeAlias

ExportStatus: TypeAlias = Literal["included", "missing", "skipped"]


@dataclass(frozen=True)
class OfflineInstallerOptions:
    output_root: Path
    include_configs: bool
    include_uv_bundle: bool
    keep_unpacked: bool
    upload_to_cloud: bool


@dataclass(frozen=True)
class BinaryExportResult:
    binary_name: str
    source_path: Path
    export_path: Path
    status: ExportStatus


@dataclass(frozen=True)
class ExportStepResult:
    label: str
    status: ExportStatus
    detail: str
    output_path: Path | None


@dataclass(frozen=True)
class OfflineInstallerReport:
    platform_name: str
    arch_name: str
    output_dir: Path
    archive_path: Path
    binary_results: list[BinaryExportResult]
    step_results: list[ExportStepResult]
