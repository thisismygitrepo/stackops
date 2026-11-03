from pathlib import Path
from typing import Annotated
from contextlib import nullcontext, redirect_stdout
from dataclasses import asdict
import json
import sys

import typer

from stackops.utils.installer_utils import installer_offline_constants
from stackops.utils.source_of_truth import STACKOPS_REPO_DIR


def export(
    output_root: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Directory where the installer folder and zip archive will be written."),
    ] = installer_offline_constants.DEFAULT_OUTPUT_ROOT,
    no_include_configs: Annotated[
        bool,
        typer.Option("--no-include-configs", "-c", help="Exclude the StackOps config tree from the offline installer."),
    ] = False,
    no_include_uv_bundle: Annotated[
        bool,
        typer.Option("--no-include-uv-bundle", "-b", help="Exclude the uv-managed StackOps runtime bundle."),
    ] = False,
    keep_unpacked: Annotated[
        bool,
        typer.Option("--keep-unpacked", "-k", help="Keep the unpacked installer directory after writing the zip archive."),
    ] = False,
    upload_to_cloud: Annotated[
        bool,
        typer.Option(
            "--upload-to-cloud",
            "-u",
            help="Upload the finished archive to the configured default rclone remote, share it, and refresh the dynamic downloader URL map.",
        ),
    ] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print the installer artifact receipt as JSON.")] = False,
) -> None:
    """📤 export the installation files to get an offline image."""
    output_root = output_root.expanduser()
    if upload_to_cloud:
        from stackops.scripts.python.helpers.helpers_devops import cli_self_repo

        dev_repo_root = cli_self_repo.developer_repo_root()
        if dev_repo_root is None:
            typer.echo(
                f"❌ --upload-to-cloud requires the developer checkout at {STACKOPS_REPO_DIR} so the downloader URL map update is written in-repo."
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
                f"❌ --upload-to-cloud requires an editable install backed by {STACKOPS_REPO_DIR} so the downloader URL map update persists in the repository."
            )
            raise typer.Exit(code=1)

    from rich.console import Console

    from stackops.utils.installer_utils import installer_offline

    with redirect_stdout(sys.stderr) if json_output else nullcontext():
        report = installer_offline.export(
            options=installer_offline.OfflineInstallerOptions(
                output_root=output_root,
                include_configs=not no_include_configs,
                include_uv_bundle=not no_include_uv_bundle,
                keep_unpacked=keep_unpacked,
                upload_to_cloud=upload_to_cloud,
            ),
            console=Console(stderr=json_output),
        )
    if json_output:
        typer.echo(json.dumps(asdict(report), default=str))


def download_installer(
    target: Annotated[
        str | None,
        typer.Option("--target", "-t", help="OS/arch target from the offline installer URL map. Prompts when omitted."),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Override the extraction directory. By default, the directory name includes the target OS/arch."),
    ] = None,
    list_targets: Annotated[bool, typer.Option("--list", "-l", help="List available installer targets without downloading.")] = False,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Print target metadata or the downloaded artifact as JSON.")] = False,
) -> None:
    """📥 Download and extract a published offline installer."""
    from stackops.jobs.scripts_dynamic import download_stackops_offline_installer
    from stackops.utils.cli_utils.interaction import require_interactive

    if list_targets:
        if target is not None or output_dir is not None:
            raise typer.BadParameter("--list cannot be combined with --target or --output-dir.")
        targets = download_stackops_offline_installer.load_installer_targets()
        if json_output:
            typer.echo(json.dumps([{"target": item.pair, "available": item.url is not None} for item in targets]))
        else:
            for item in targets:
                typer.echo(f"""{item.pair}: {'available' if item.url is not None else 'unavailable'}""")
        return
    if target is None:
        if json_output:
            raise typer.BadParameter("--json requires --target, or --list to inspect available targets.")
        require_interactive("Installer target selection; supply --target or use --list --json")

    try:
        with redirect_stdout(sys.stderr) if json_output else nullcontext():
            downloaded = download_stackops_offline_installer.download_installer(target_key=target, output_dir=output_dir)
    except RuntimeError as exc:
        typer.echo(f"❌ {exc}", err=True)
        raise typer.Exit(code=1) from exc
    if json_output:
        typer.echo(json.dumps({"target": target, "output_dir": str(downloaded)}))
