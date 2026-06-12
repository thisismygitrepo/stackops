from pathlib import Path
from typing import Annotated

import typer

from stackops.utils.installer_utils import installer_offline_constants
from stackops.scripts.python.helpers.helpers_devops.cli_self import developer_repo_root


def export(
    output_root: Annotated[
        Path,
        typer.Option("--output-root", "-o", help="Directory where the installer folder and zip archive will be written."),
    ] = installer_offline_constants.DEFAULT_OUTPUT_ROOT,
    include_configs: Annotated[
        bool,
        typer.Option("--no-include-configs", "-c", help="Exclude the StackOps config tree from the offline installer."),
    ] = True,
    include_uv_bundle: Annotated[
        bool,
        typer.Option("--no-include-uv-bundle", "-b", help="Exclude the uv-managed StackOps runtime bundle."),
    ] = True,
    keep_unpacked: Annotated[
        bool,
        typer.Option("--keep-unpacked", "-k", help="Keep the unpacked installer directory after writing the zip archive."),
    ] = False,
    upload_to_cloud: Annotated[
        bool,
        typer.Option(
            "--upload-to-cloud",
            "-u",
            help="Upload the finished archive to its mirrored gdp:myhome/ path, share it, and refresh the dynamic downloader URL map.",
        ),
    ] = False,
) -> None:
    """📤 export the installation files to get an offline image."""
    output_root = output_root.expanduser()
    if upload_to_cloud:
        dev_repo_root = developer_repo_root()
        if dev_repo_root is None:
            typer.echo(
                "❌ --upload-to-cloud requires the developer checkout at ~/code/stackops so the downloader URL map update is written in-repo."
            )
            raise typer.Exit(code=1)
        dev_repo_root = dev_repo_root.resolve()
        from stackops.jobs import scripts_dynamic as scripts_dynamic_assets
        from stackops.utils.path_reference import (
            get_path_reference_library_relative_path,
            get_path_reference_path,
        )

        path_reference = scripts_dynamic_assets.OFFLINE_INSTALLER_PATH_REFERENCE
        active_url_map_path = get_path_reference_path(
            module=scripts_dynamic_assets,
            path_reference=path_reference,
        )
        expected_url_map_path = dev_repo_root.joinpath(
            "src",
            "stackops",
            get_path_reference_library_relative_path(
                module=scripts_dynamic_assets,
                path_reference=path_reference,
            ),
        ).resolve()
        if active_url_map_path != expected_url_map_path:
            typer.echo(
                "❌ --upload-to-cloud requires an editable install backed by ~/code/stackops so the downloader URL map update persists in the repository."
            )
            raise typer.Exit(code=1)

    from rich.console import Console

    from stackops.utils.installer_utils import installer_offline

    installer_offline.export(
        options=installer_offline.OfflineInstallerOptions(
            output_root=output_root,
            include_configs=include_configs,
            include_uv_bundle=include_uv_bundle,
            keep_unpacked=keep_unpacked,
            upload_to_cloud=upload_to_cloud,
        ),
        console=Console(),
    )


def download_installer(
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="OS/arch target from the offline installer URL map. Prompts when omitted."),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Directory where the downloaded offline installer will be extracted."),
    ] = None,
) -> None:
    """📥 Download and extract a published offline installer."""
    from stackops.jobs.scripts_dynamic import download_stackops_offline_installer

    try:
        download_stackops_offline_installer.download_installer(target_key=target, output_dir=output_dir)
    except RuntimeError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(code=1) from exc
