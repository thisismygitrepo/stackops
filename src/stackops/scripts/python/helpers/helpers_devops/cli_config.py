from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Literal, TypeAlias

import typer

from stackops.utils.cli_utils.alias_markers import apply_alias_markers

if TYPE_CHECKING:
    from types import ModuleType

InitScriptKind: TypeAlias = Literal["init", "ia", "live"]
AssetDumpKind: TypeAlias = Literal["layout", "data", "dotfiles", "secrets", "config"]
DumpConfigKind: TypeAlias = Literal["layout", "data", "dotfiles", "secrets", "config", "init", "ia", "live"]


@dataclass(frozen=True, slots=True)
class DumpAssetSpec:
    data_source_path: Path
    schema_source_path: Path
    data_output_path: Path
    schema_output_path: Path


def config() -> None:
    """🤖 <I> interactive configuration of machine."""
    from stackops.scripts.python.helpers.helpers_devops.interactive import main

    main()


def terminal(ctx: typer.Context) -> None:
    """🐚 <t> Configure your terminal profile."""
    from stackops.scripts.python.helpers.helpers_devops import cli_config_terminal

    apply_alias_markers(cli_config_terminal.get_app())(ctx.args, standalone_mode=False)


def _read_init_script(which: InitScriptKind) -> str:
    import platform

    import stackops.settings.shells.bash as bash_shell_assets
    import stackops.settings.shells.pwsh as pwsh_shell_assets
    import stackops.settings.shells.zsh as zsh_shell_assets

    from stackops.utils.path_reference import get_path_reference_path

    platform_name = platform.system()
    if platform_name == "Linux" or platform_name == "Darwin":
        match which:
            case "init":
                if platform_name == "Darwin":
                    init_path = get_path_reference_path(
                        module=zsh_shell_assets,
                        path_reference=zsh_shell_assets.INIT_PATH_REFERENCE,
                    )
                else:
                    init_path = get_path_reference_path(
                        module=bash_shell_assets,
                        path_reference=bash_shell_assets.INIT_PATH_REFERENCE,
                    )
                return init_path.read_text(encoding="utf-8")
            case "ia":
                import stackops.scripts.setup.linux as module

                script_path = get_path_reference_path(module=module, path_reference=module.INTERACTIVE_PATH_REFERENCE)
                return script_path.read_text(encoding="utf-8")
            case "live":
                import stackops.scripts.setup.linux as module

                script_path = get_path_reference_path(module=module, path_reference=module.LIVE_FROM_GITHUB_PATH_REFERENCE)
                return script_path.read_text(encoding="utf-8")

    elif platform_name == "Windows":
        match which:
            case "init":
                init_path = get_path_reference_path(
                    module=pwsh_shell_assets,
                    path_reference=pwsh_shell_assets.INIT_PATH_REFERENCE,
                )
                return init_path.read_text(encoding="utf-8")
            case "ia":
                import stackops.scripts.setup.windows as module

                script_path = get_path_reference_path(module=module, path_reference=module.INTERACTIVE_PATH_REFERENCE)
                return script_path.read_text(encoding="utf-8")
            case "live":
                import stackops.scripts.setup.windows as module

                script_path = get_path_reference_path(module=module, path_reference=module.LIVE_FROM_GITHUB_PATH_REFERENCE)
                return script_path.read_text(encoding="utf-8")
    else:
        typer.echo("Unsupported platform for init scripts.")
        raise typer.Exit(code=1)


def _dump_init_script(which: InitScriptKind, run: bool) -> None:
    script = _read_init_script(which=which)
    if run:
        from stackops.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script, strict=True)
    else:
        print(script)


def dump_config(
    which: Annotated[DumpConfigKind, typer.Option(..., "--which", "-w", help="Which config or init script to dump")],
    data: Annotated[bool, typer.Option("--data", "-d", help="Dump the config data/template file. Defaults to data and schema when omitted.")] = False,
    schema: Annotated[bool, typer.Option("--schema", "-s", help="Dump the matching schema file. Defaults to data and schema when omitted.")] = False,
    default_path: Annotated[
        bool,
        typer.Option("--default-path", "-p", help="Write to the default StackOps path for the selected file instead of the current directory."),
    ] = False,
    force: Annotated[bool, typer.Option("--force", "-f", help="Overwrite existing dump output files.")] = False,
    run: Annotated[bool, typer.Option("--run", "-r", help="Run an init script instead of printing it.")] = False,
) -> None:
    """🔗 Dump example configuration files and init scripts."""
    match which:
        case "layout":
            if run:
                _reject_run_for_non_script_dump()
            _dump_layout_example(data=data, schema=schema, default_path=default_path, force=force)
            return
        case "data" | "dotfiles":
            if run:
                _reject_run_for_non_script_dump()
            _dump_profile_example(which=which, data=data, schema=schema, default_path=default_path, force=force)
            return
        case "secrets":
            if run:
                _reject_run_for_non_script_dump()
            _dump_secrets_example(data=data, schema=schema, default_path=default_path, force=force)
            return
        case "config":
            if run:
                _reject_run_for_non_script_dump()
            _dump_stackops_config_example(data=data, schema=schema, default_path=default_path, force=force)
            return
        case "init" | "ia" | "live":
            if data or schema:
                _reject_data_schema_for_script_dump()
            if default_path:
                _reject_default_path_for_script_dump()
            if force:
                _reject_force_for_script_dump()
            _dump_init_script(which=which, run=run)
            return
    msg = typer.style("Error: ", fg=typer.colors.RED) + f"Unknown config type: {which}"
    typer.echo(msg)
    raise typer.Exit(code=1)


def _reject_run_for_non_script_dump() -> None:
    msg = typer.style("Error: ", fg=typer.colors.RED) + "--run is only valid when dumping init scripts."
    typer.echo(msg)
    raise typer.Exit(code=1)


def _reject_data_schema_for_script_dump() -> None:
    msg = typer.style("Error: ", fg=typer.colors.RED) + "--data and --schema are only valid when dumping configuration files."
    typer.echo(msg)
    raise typer.Exit(code=1)


def _reject_default_path_for_script_dump() -> None:
    msg = typer.style("Error: ", fg=typer.colors.RED) + "--default-path is only valid when dumping configuration files."
    typer.echo(msg)
    raise typer.Exit(code=1)


def _reject_force_for_script_dump() -> None:
    msg = typer.style("Error: ", fg=typer.colors.RED) + "--force is only valid when dumping configuration files."
    typer.echo(msg)
    raise typer.Exit(code=1)


def _resolve_dump_content_selection(*, data: bool, schema: bool) -> tuple[bool, bool]:
    if data or schema:
        return data, schema
    return True, True


def _reject_unwritable_output_paths(paths: Sequence[Path], *, force: bool) -> None:
    non_file_paths = [path for path in paths if path.exists() and not path.is_file()]
    if non_file_paths:
        path_text = _format_paths(non_file_paths)
        msg = typer.style("Error: ", fg=typer.colors.RED) + f"Output path exists but is not a file: {path_text}"
        typer.echo(msg)
        raise typer.Exit(code=1)

    existing_paths = [path for path in paths if path.exists()]
    if existing_paths and not force:
        path_text = _format_paths(existing_paths)
        msg = (
            typer.style("Error: ", fg=typer.colors.RED)
            + f"Refusing to overwrite existing file(s): {path_text}. Pass --force/-f to overwrite."
        )
        typer.echo(msg)
        raise typer.Exit(code=1)


def _format_paths(paths: Sequence[Path]) -> str:
    if len(paths) == 1:
        return str(paths[0])
    return ", ".join(str(path) for path in paths[:-1]) + f" and {paths[-1]}"


def _echo_created_paths(paths: Sequence[Path]) -> None:
    if not paths:
        return
    path_text = _format_paths(paths)
    msg = typer.style("✅ Success: ", fg=typer.colors.GREEN) + f"Wrote {path_text}"
    typer.echo(msg)


def _get_path_reference_asset_path(*, module: "ModuleType", path_reference: str) -> Path:
    from stackops.utils.path_reference import get_path_reference_path

    return get_path_reference_path(module=module, path_reference=path_reference)


def _write_asset(*, source_path: Path, output_path: Path, force: bool) -> Path:
    _reject_unwritable_output_paths([output_path], force=force)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return output_path


def _dump_asset_spec(*, spec: DumpAssetSpec, data: bool, schema: bool, force: bool) -> None:
    dump_data, dump_schema = _resolve_dump_content_selection(data=data, schema=schema)
    created_paths: list[Path] = []
    output_paths: list[Path] = []
    if dump_data:
        output_paths.append(spec.data_output_path)
    if dump_schema:
        output_paths.append(spec.schema_output_path)
    _reject_unwritable_output_paths(output_paths, force=force)

    if dump_data:
        created_paths.append(_write_asset(source_path=spec.data_source_path, output_path=spec.data_output_path, force=force))
    if dump_schema:
        created_paths.append(_write_asset(source_path=spec.schema_source_path, output_path=spec.schema_output_path, force=force))
    _echo_created_paths(created_paths)


def _dump_layout_example(*, data: bool, schema: bool, default_path: bool, force: bool) -> None:
    import stackops.utils.schemas.layouts as layout_assets
    from stackops.utils.source_of_truth import DOTFILES_LAYOUTS_JSON_PATH

    if default_path:
        data_output_path = DOTFILES_LAYOUTS_JSON_PATH
        schema_output_path = DOTFILES_LAYOUTS_JSON_PATH.with_name(layout_assets.LAYOUT_SCHEMA_PATH_REFERENCE)
    else:
        output_dir = Path.cwd() / ".stackops" / "examples"
        data_output_path = output_dir / layout_assets.LAYOUT_PATH_REFERENCE
        schema_output_path = output_dir / layout_assets.LAYOUT_SCHEMA_PATH_REFERENCE
    spec = DumpAssetSpec(
        data_source_path=_get_path_reference_asset_path(module=layout_assets, path_reference=layout_assets.LAYOUT_PATH_REFERENCE),
        schema_source_path=_get_path_reference_asset_path(module=layout_assets, path_reference=layout_assets.LAYOUT_SCHEMA_PATH_REFERENCE),
        data_output_path=data_output_path,
        schema_output_path=schema_output_path,
    )
    _dump_asset_spec(spec=spec, data=data, schema=schema, force=force)


def _dump_profile_example(*, which: Literal["data", "dotfiles"], data: bool, schema: bool, default_path: bool, force: bool) -> None:
    import stackops.utils.schemas.mapper as mapper_assets
    from stackops.utils.source_of_truth import DOTFILES_USER_BACKUP_PATH, DOTFILES_USER_MAPPER_PATH

    if which == "data":
        data_path_reference = mapper_assets.MAPPER_DATA_PATH_REFERENCE
        schema_path_reference = mapper_assets.MAPPER_DATA_SCHEMA_PATH_REFERENCE
        default_data_path = DOTFILES_USER_BACKUP_PATH
    else:
        data_path_reference = mapper_assets.MAPPER_DOTFILES_PATH_REFERENCE
        schema_path_reference = mapper_assets.MAPPER_DOTFILES_SCHEMA_PATH_REFERENCE
        default_data_path = DOTFILES_USER_MAPPER_PATH

    if default_path:
        data_output_path = default_data_path
        schema_output_path = default_data_path.with_name(schema_path_reference)
    else:
        output_dir = Path.cwd() / ".stackops" / "examples"
        data_output_path = output_dir / data_path_reference
        schema_output_path = output_dir / schema_path_reference
    spec = DumpAssetSpec(
        data_source_path=_get_path_reference_asset_path(module=mapper_assets, path_reference=data_path_reference),
        schema_source_path=_get_path_reference_asset_path(module=mapper_assets, path_reference=schema_path_reference),
        data_output_path=data_output_path,
        schema_output_path=schema_output_path,
    )
    _dump_asset_spec(spec=spec, data=data, schema=schema, force=force)


def _dump_secrets_example(*, data: bool, schema: bool, default_path: bool, force: bool) -> None:
    import stackops.secrets.assets as secrets_assets
    from stackops.secrets.paths import SECRETS_DOFILE

    if default_path:
        data_output_path = SECRETS_DOFILE
        schema_output_path = SECRETS_DOFILE.with_name(secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE)
    else:
        output_dir = Path.cwd() / ".stackops" / "secrets"
        data_output_path = output_dir / "secrets.json"
        schema_output_path = output_dir / secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE
    spec = DumpAssetSpec(
        data_source_path=_get_path_reference_asset_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_EXAMPLE_PATH_REFERENCE),
        schema_source_path=_get_path_reference_asset_path(module=secrets_assets, path_reference=secrets_assets.SECRETS_SCHEMA_PATH_REFERENCE),
        data_output_path=data_output_path,
        schema_output_path=schema_output_path,
    )
    _dump_asset_spec(spec=spec, data=data, schema=schema, force=force)


def _dump_stackops_config_example(*, data: bool, schema: bool, default_path: bool, force: bool) -> None:
    import stackops.utils.schemas.config as config_assets
    from stackops.utils.source_of_truth import DOTFILES_STACKOPS_CONFIG_PATH

    if default_path:
        data_output_path = DOTFILES_STACKOPS_CONFIG_PATH
        schema_output_path = DOTFILES_STACKOPS_CONFIG_PATH.with_name(config_assets.CONFIG_SCHEMA_PATH_REFERENCE)
    else:
        output_dir = Path.cwd() / ".stackops" / "config"
        data_output_path = output_dir / config_assets.CONFIG_PATH_REFERENCE
        schema_output_path = output_dir / config_assets.CONFIG_SCHEMA_PATH_REFERENCE
    spec = DumpAssetSpec(
        data_source_path=_get_path_reference_asset_path(module=config_assets, path_reference=config_assets.CONFIG_PATH_REFERENCE),
        schema_source_path=_get_path_reference_asset_path(module=config_assets, path_reference=config_assets.CONFIG_SCHEMA_PATH_REFERENCE),
        data_output_path=data_output_path,
        schema_output_path=schema_output_path,
    )
    _dump_asset_spec(spec=spec, data=data, schema=schema, force=force)


def copy_assets(which: Annotated[Literal["scripts", "s", "settings", "t", "all", "a"], typer.Argument(..., help="Which assets to copy")]) -> None:
    """🔗 Copy asset files from library to machine.

    Strict behavior:
    - Raise typer.Exit(code=1) on unknown asset type or on any failure.
    - Exit immediately on first failure when copying multiple asset groups.
    """
    from stackops.profile import create_helper

    try:
        match which:
            case "all" | "a":
                create_helper.copy_assets_to_machine(which="scripts")
                create_helper.copy_assets_to_machine(which="settings")
                typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + "Copied all assets.")
                return
            case "scripts" | "s":
                create_helper.copy_assets_to_machine(which="scripts")
                typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + "Copied script assets.")
                return
            case "settings" | "t":
                create_helper.copy_assets_to_machine(which="settings")
                typer.echo(typer.style("✅ Success: ", fg=typer.colors.GREEN) + "Copied settings assets.")
                return
    except Exception as exc:
        typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"Failed to copy assets ({which}): {exc}")
        raise typer.Exit(code=1) from exc

    # Unreachable with current Literal type, but keep strict behavior if it occurs.
    typer.echo(typer.style("Error: ", fg=typer.colors.RED) + f"Unknown asset type: {which}")
    raise typer.Exit(code=1)


def get_app() -> typer.Typer:
    import stackops.scripts.python.helpers.helpers_devops.cli_config_secrets as secrets_module

    from stackops.profile import create_links_export
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_mapper import edit_dotfile, register_dotfile
    from stackops.scripts.python.helpers.helpers_devops.cli_config_dotfile_transfer import export_dotfiles, import_dotfiles

    config_apps = typer.Typer(help="🧰 <c> configuration subcommands", no_args_is_help=True, add_help_option=True, add_completion=False)
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }

    config_apps.command("sync", no_args_is_help=True, help="🔄 <s> Sync dotfiles.")(create_links_export.main_from_parser)
    config_apps.command("s", no_args_is_help=True, help="Sync dotfiles.", hidden=True)(create_links_export.main_from_parser)

    config_apps.command("register", no_args_is_help=True, help="📇 <r> Register dotfiles against user mapper.yaml")(register_dotfile)
    config_apps.command("r", no_args_is_help=True, hidden=True)(register_dotfile)
    config_apps.command("edit", no_args_is_help=True, help="📝 <e> Open dotfiles mapper.yaml in nano, hx, or code.")(edit_dotfile)
    config_apps.command("e", no_args_is_help=True, help="Open dotfiles mapper.yaml in nano, hx, or code.", hidden=True)(edit_dotfile)

    config_apps.command("export-dotfiles", no_args_is_help=True, help="📤 <E> Export dotfiles for migration to new machine.")(export_dotfiles)
    config_apps.command("E", no_args_is_help=True, help="Export dotfiles for migration to new machine.", hidden=True)(export_dotfiles)
    config_apps.command("import-dotfiles", no_args_is_help=False, help="📥 <I> Import dotfiles from exported archive.")(import_dotfiles)
    config_apps.command("I", no_args_is_help=False, help="Import dotfiles from exported archive.", hidden=True)(import_dotfiles)

    config_apps.command("terminal", help="🐚 <t> Configure your terminal profile.", context_settings=ctx_settings)(terminal)
    config_apps.command("t", help="🐚 <t> Configure your terminal profile.", hidden=True, context_settings=ctx_settings)(terminal)

    config_apps.command("interactive", no_args_is_help=False, help="🤖 <i> Interactive configuration of machine.")(config)
    config_apps.command("i", no_args_is_help=False, help="Interactive configuration of machine.", hidden=True)(config)

    config_apps.command("copy-assets", no_args_is_help=True, help="📋 <c> Copy asset files from library to machine.", hidden=False)(copy_assets)
    config_apps.command("c", no_args_is_help=True, help="Copy asset files from library to machine.", hidden=True)(copy_assets)

    config_apps.add_typer(
        secrets_module.get_app(),
        name="secrets",
        help=f"🔐 <S> {secrets_module.SECRETS_HELP}",
    )
    config_apps.add_typer(
        secrets_module.get_app(),
        name="S",
        help=secrets_module.SECRETS_HELP,
        hidden=True,
    )

    config_apps.command("dump", no_args_is_help=True, help="📦 <d> Dump example configuration files and init scripts.")(dump_config)
    config_apps.command("d", no_args_is_help=True, help="Dump example configuration files and init scripts.", hidden=True)(dump_config)

    return config_apps
