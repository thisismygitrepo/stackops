from rich.console import Console
from stackops.utils.installer_utils import installer_offline_constants as constants
from stackops.utils.installer_utils.installer_offline_models import ExportStepResult, OfflineInstallerOptions, OfflineInstallerReport
from stackops.utils.installer_utils.installer_offline_publish import publish_archive
from stackops.utils.installer_utils.installer_offline_render import render_report
from stackops.utils.installer_utils.installer_offline_scripts import write_install_script
from stackops.utils.installer_utils.installer_offline_steps import archive_output, export_binaries, export_configs
from stackops.utils.installer_utils.installer_offline_uv import export_uv_bundle


DEFAULT_OUTPUT_ROOT = constants.DEFAULT_OUTPUT_ROOT


def export(*, options: OfflineInstallerOptions, console: Console) -> OfflineInstallerReport:
    import platform
    import shutil

    system_name = platform.system()
    os_name = system_name.lower()
    arch_name = platform.machine().lower()
    output_dir = options.output_root.joinpath(f"stackops-offline-installer-{os_name}-{arch_name}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    binaries_root = output_dir.joinpath("binaries")
    configs_root = output_dir.joinpath("configs")
    install_path = constants.resolve_install_path(system_name=system_name)
    console.print(f"[bold blue]Collecting binaries from[/bold blue] {install_path}")
    binary_results = export_binaries(install_path=install_path, binaries_root=binaries_root, system_name=system_name)
    console.print("[bold blue]Collecting installer assets[/bold blue]")
    step_results = [
        export_configs(configs_root=configs_root, include_configs=options.include_configs),
        export_uv_bundle(res_root=output_dir, install_path=install_path, include_uv_bundle=options.include_uv_bundle, system_name=system_name),
        write_install_script(res_root=output_dir, system_name=system_name),
    ]
    console.print("[bold blue]Creating archive[/bold blue]")
    archive_path = archive_output(output_dir=output_dir, keep_unpacked=options.keep_unpacked)
    step_results.append(
        ExportStepResult(
            label="archive",
            status="included",
            detail="created zip archive" if options.keep_unpacked else "created zip archive and removed unpacked directory",
            output_path=archive_path,
        )
    )
    if options.upload_to_cloud:
        console.print("[bold blue]Uploading archive to cloud[/bold blue]")
        step_results.extend(publish_archive(archive_path=archive_path, system_name=system_name, arch_name=arch_name))
    report = OfflineInstallerReport(
        platform_name=system_name,
        arch_name=arch_name,
        output_dir=output_dir,
        archive_path=archive_path,
        binary_results=binary_results,
        step_results=step_results,
    )
    render_report(report=report, options=options, console=console)
    return report


if __name__ == "__main__":
    export(
        options=OfflineInstallerOptions(
            output_root=DEFAULT_OUTPUT_ROOT,
            include_configs=True,
            include_uv_bundle=True,
            keep_unpacked=False,
            upload_to_cloud=False,
        ),
        console=Console(),
    )
