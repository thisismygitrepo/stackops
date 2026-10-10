from typing import Annotated, Literal, TypeAlias

import typer

InitScriptKind: TypeAlias = Literal["init", "ia", "live"]
INIT_SCRIPT_HELP = "Print or run a StackOps shell init or machine setup script."


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


def init_script(
    which: Annotated[InitScriptKind, typer.Argument(help="init: shell init script, ia: interactive machine setup, live: setup straight from GitHub.")],
    run: Annotated[bool, typer.Option("--run", "-R", help="Run the script instead of printing it.")] = False,
) -> None:
    script = _read_init_script(which=which)
    if run:
        from stackops.utils.code import exit_then_run_shell_script

        exit_then_run_shell_script(script, strict=True)
    else:
        print(script)
