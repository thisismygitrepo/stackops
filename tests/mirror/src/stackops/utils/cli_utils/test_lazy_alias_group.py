import pytest
import typer
import typer.main
from typer.testing import CliRunner

from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cli_utils.lazy_alias_group import LazyAliasGroup


def _build_tools_app(with_callback: bool) -> typer.Typer:
    tools_app = typer.Typer(no_args_is_help=True, context_settings={"help_option_names": ["-h", "--help"]})
    if with_callback:
        tools_app.callback()(lambda: None)

    def build() -> None:
        """Build things"""
        typer.echo("built")

    def clean() -> None:
        """Clean things"""
        typer.echo("cleaned")

    tools_app.command("build")(build)
    tools_app.command("clean")(clean)
    return tools_app


def _build_root_app(with_callback: bool) -> typer.Typer:
    root_app = typer.Typer(no_args_is_help=True)
    root_app.add_typer(_build_tools_app(with_callback=with_callback), name="tools", help="Tools")
    root_app.add_typer(_build_tools_app(with_callback=with_callback), name="t", help="Tools", hidden=True)
    return apply_alias_markers(root_app)


def test_duplicate_alias_group_is_converted_only_when_used() -> None:
    root_app = _build_root_app(with_callback=False)
    alias_info = root_app.registered_groups[1]
    assert alias_info.typer_instance is not None
    assert isinstance(alias_info.typer_instance.info.cls, type)
    assert issubclass(alias_info.typer_instance.info.cls, LazyAliasGroup)

    root_group = typer.main.get_group(root_app)
    alias_group = root_group.commands["t"]
    assert isinstance(alias_group, LazyAliasGroup)
    assert alias_group._converted_commands is None  # pyright: ignore[reportPrivateUsage]

    assert sorted(alias_group.commands) == ["build", "clean"]
    assert alias_group._converted_commands is not None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("subcommand", ["build", "clean"])
def test_alias_group_runs_the_same_commands_as_the_primary_group(subcommand: str) -> None:
    root_app = _build_root_app(with_callback=False)
    runner = CliRunner()

    primary_result = runner.invoke(root_app, ["tools", subcommand])
    alias_result = runner.invoke(root_app, ["t", subcommand])

    assert primary_result.exit_code == 0, primary_result.output
    assert alias_result.exit_code == 0, alias_result.output
    assert alias_result.output == primary_result.output
    assert runner.invoke(root_app, ["t", "--help"]).output.count("Build things") == 1
    assert "Did you mean 'build'?" in runner.invoke(root_app, ["t", "biuld"]).output


def test_group_with_callback_keeps_its_full_duplicate() -> None:
    root_app = _build_root_app(with_callback=True)
    alias_info = root_app.registered_groups[1]
    assert alias_info.typer_instance is not None

    assert not isinstance(alias_info.typer_instance.info.cls, type)
    assert len(alias_info.typer_instance.registered_commands) == 2
