"""devops with emojis - lazy loading subcommands."""

from typing import Callable, TypedDict

import typer

from stackops.utils.cli_utils.alias_markers import apply_alias_markers


class EmojiDisplayDiagnostic(TypedDict):
    emoji: str
    codepoints: list[str]
    char_count: int
    has_variation_selector_16: bool
    terminal_width: int | None


def emoji_display_diagnostics(emojis: list[str]) -> list[EmojiDisplayDiagnostic]:
    import unicodedata

    wcswidth_func: Callable[[str], int] | None

    try:
        from wcwidth import wcswidth

        wcswidth_func = wcswidth
    except Exception:
        wcswidth_func = None

    diagnostics: list[EmojiDisplayDiagnostic] = []
    for emoji in emojis:
        codepoints = [f"U+{ord(ch):04X} {unicodedata.name(ch, '?')}" for ch in emoji]
        diagnostics.append(
            {
                "emoji": emoji,
                "codepoints": codepoints,
                "char_count": len(emoji),
                "has_variation_selector_16": "\ufe0f" in emoji,
                "terminal_width": wcswidth_func(emoji) if wcswidth_func is not None else None,
            }
        )
    return diagnostics


def inspect_devops_help_emojis() -> list[EmojiDisplayDiagnostic]:
    return emoji_display_diagnostics(emojis=["🔧", "📁", "🔩", "💾", "🔧", "🌐", "🚀"])


def _run_nested_app(ctx: typer.Context, app_factory: Callable[[], typer.Typer]) -> None:
    nested_app = apply_alias_markers(app_factory())
    nested_result: object = nested_app(ctx.args, prog_name=ctx.command_path, standalone_mode=False)
    if isinstance(nested_result, int):
        raise typer.Exit(code=nested_result)


def software(ctx: typer.Context) -> None:
    from stackops.scripts.python.helpers.helpers_devops import cli_software

    _run_nested_app(ctx, cli_software.get_app)


def repos(ctx: typer.Context) -> None:
    """📁 <r> Manage development repositories"""
    from stackops.scripts.python.helpers.helpers_devops import cli_repos

    _run_nested_app(ctx, cli_repos.get_app)


def config(ctx: typer.Context) -> None:
    """🔩 <c> Configuration management"""
    from stackops.scripts.python.helpers.helpers_devops import cli_config

    _run_nested_app(ctx, cli_config.get_app)


def data(ctx: typer.Context) -> None:
    """💾 <d> Data management"""
    from stackops.scripts.python.helpers.helpers_devops import cli_data

    _run_nested_app(ctx, cli_data.get_app)


def self_cmd(ctx: typer.Context) -> None:
    """🔧 <s> Self management"""
    from stackops.scripts.python.helpers.helpers_devops import cli_self

    _run_nested_app(ctx, cli_self.get_app)


def network(ctx: typer.Context) -> None:
    """🌐 <n> Network management"""
    import stackops.scripts.python.helpers.helpers_devops.cli_nw as cli_network

    _run_nested_app(ctx, cli_network.get_app)


def scripts(ctx: typer.Context) -> None:
    from stackops.scripts.python.helpers.helpers_devops import cli_scripts

    _run_nested_app(ctx, cli_scripts.get_app)


def security(ctx: typer.Context) -> None:
    """🔐 <y> Security related CLI tools."""
    from stackops.jobs.installer.checks import security_cli

    _run_nested_app(ctx, security_cli.get_app)


def vault(ctx: typer.Context) -> None:
    """🔐 <v> Manage credentials, secrets, and vault sessions."""
    from stackops.scripts.python.helpers.helpers_devops import cli_config_secrets

    _run_nested_app(ctx, cli_config_secrets.get_app)


def get_app() -> typer.Typer:
    from stackops.scripts.python.helpers.helpers_devops.cli_status import status

    cli_app = typer.Typer(
        help="🔧 DevOps operations", no_args_is_help=True, add_help_option=True, add_completion=False,
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    ctx_settings: dict[str, object] = {
        "allow_extra_args": True,
        "allow_interspersed_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    }

    cli_app.command("software", help="📦 <w> Install software and manage catalogs", context_settings=ctx_settings)(software)
    cli_app.command("w", hidden=True, context_settings=ctx_settings)(software)

    cli_app.command("data", help="💾 <d> Data management", context_settings=ctx_settings)(data)
    cli_app.command("d", hidden=True, context_settings=ctx_settings)(data)

    cli_app.command("repos", help="📁 <r> Manage development repositories", context_settings=ctx_settings)(repos)
    cli_app.command("r", hidden=True, context_settings=ctx_settings)(repos)

    cli_app.command("config", help="🔩 <c> Configuration management", context_settings=ctx_settings)(config)
    cli_app.command("c", hidden=True, context_settings=ctx_settings)(config)

    cli_app.command("vault", help="🔐 <v> Manage credentials, secrets, and vault sessions", context_settings=ctx_settings)(vault)
    cli_app.command("v", hidden=True, context_settings=ctx_settings)(vault)

    scripts_context = {**ctx_settings, "allow_interspersed_args": False}
    cli_app.command("scripts", help="🚀 <x> Run, list, locate, and edit scripts.", context_settings=scripts_context)(scripts)
    cli_app.command("x", hidden=True, context_settings=scripts_context)(scripts)

    cli_app.command("security", help="🔐 <y> Security related CLI tools.", context_settings=ctx_settings)(security)
    cli_app.command("y", hidden=True, context_settings=ctx_settings)(security)

    cli_app.command("network", help="🌐 <n> Network management", context_settings=ctx_settings)(network)
    cli_app.command("n", hidden=True, context_settings=ctx_settings)(network)

    cli_app.command("status", help="📊 <S> Show machine, repository, application, and configuration status.")(status)
    cli_app.command("S", hidden=True)(status)

    cli_app.command("self", help="🔧 <s> Self management", context_settings=ctx_settings)(self_cmd)
    cli_app.command("s", hidden=True, context_settings=ctx_settings)(self_cmd)


    return apply_alias_markers(cli_app)


def main() -> None:
    app = get_app()
    app()
