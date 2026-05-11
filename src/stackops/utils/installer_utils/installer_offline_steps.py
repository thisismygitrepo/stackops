import shutil
from pathlib import Path

from stackops.utils.installer_utils import installer_offline_constants as constants
from stackops.utils.installer_utils.installer_offline_models import BinaryExportResult, ExportStepResult, ExportStatus


def export_binaries(*, install_path: Path, binaries_root: Path, system_name: str) -> list[BinaryExportResult]:
    results: list[BinaryExportResult] = []
    for binary_name in constants.BINARY_NAMES:
        source_name = constants.resolve_binary_source_name(binary_name=binary_name, system_name=system_name)
        source_path = install_path.joinpath(source_name)
        export_path = binaries_root.joinpath(source_name)
        if source_path.exists():
            binaries_root.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, export_path)
            status: ExportStatus = "included"
        else:
            status = "missing"
        results.append(
            BinaryExportResult(
                binary_name=source_name,
                source_path=source_path,
                export_path=export_path,
                status=status,
            )
        )
    return results


def export_configs(*, configs_root: Path, include_configs: bool) -> ExportStepResult:
    if not include_configs:
        return ExportStepResult(label="configs", status="skipped", detail="disabled by CLI option", output_path=None)
    if not constants.CONFIG_ROOT.exists():
        return ExportStepResult(label="configs", status="missing", detail=f"missing source: {constants.CONFIG_ROOT}", output_path=None)
    shutil.copytree(constants.CONFIG_ROOT, configs_root, dirs_exist_ok=True)
    return ExportStepResult(label="configs", status="included", detail=f"copied from {constants.CONFIG_ROOT}", output_path=configs_root)


def archive_output(*, output_dir: Path, keep_unpacked: bool) -> Path:
    archive_base = output_dir.parent.joinpath(output_dir.name)
    archive_path = Path(shutil.make_archive(archive_base.as_posix(), "zip", root_dir=output_dir))
    if not keep_unpacked:
        shutil.rmtree(output_dir)
    return archive_path
