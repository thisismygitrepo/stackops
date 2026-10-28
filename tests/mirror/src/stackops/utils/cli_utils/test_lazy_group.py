import pytest
import typer
import typer.main
from typer.core import TyperGroup
from typer.testing import CliRunner

from stackops.utils.cli_utils.alias_markers import apply_alias_markers
from stackops.utils.cli_utils.ordered_group import ordered_group


def _build_tools_app(with_callback: bool, command_order: tuple[str, ...] | None) -> typer.Typer:
    tools_app = typer.Typer(
        no_args_is_help=True,
        context_settings={"help_option_names": ["-h", "--help"]},
        **({} if command_order is None else {"cls": ordered_group(command_order)}),
    )
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


def _build_root_app(with_callback: bool, command_order: tuple[str, ...] | None) -> typer.Typer:
    root_app = typer.Typer(no_args_is_help=True)
    root_app.add_typer(_build_tools_app(with_callback=with_callback, command_order=command_order), name="tools", help="Tools")
    root_app.add_typer(_build_tools_app(with_callback=with_callback, command_order=command_order), name="t", help="Tools", hidden=True)
    root_app.add_typer(_build_tools_app(with_callback=False, command_order=None), name="other", help="Other")
    return apply_alias_markers(root_app)


def _converted(group: object) -> bool:
    return group._converted_commands is not None  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]


def test_sub_groups_are_converted_only_when_their_commands_are_needed() -> None:
    root_group = typer.main.get_group(_build_root_app(with_callback=False, command_order=None))

    tools_group, alias_group, other_group = root_group.commands["tools"], root_group.commands["t"], root_group.commands["other"]
    assert not any(_converted(group) for group in (tools_group, alias_group, other_group))

    assert sorted(tools_group.commands) == ["build", "clean"]  # pyright: ignore[reportAttributeAccessIssue]
    assert _converted(tools_group)
    assert not _converted(alias_group)
    assert not _converted(other_group)


@pytest.mark.parametrize("path", [["tools", "build"], ["t", "build"]])
def test_invoking_a_command_converts_only_the_groups_on_its_path(path: list[str]) -> None:
    root_app = _build_root_app(with_callback=False, command_order=None)
    result = CliRunner().invoke(root_app, path)

    assert result.exit_code == 0, result.output
    assert result.output.strip() == "built"
    root_group = typer.main.get_group(root_app)
    assert not _converted(root_group.commands["other"])


def test_alias_group_matches_primary_help_and_suggests_commands() -> None:
    root_app = _build_root_app(with_callback=False, command_order=None)
    runner = CliRunner()

    assert runner.invoke(root_app, ["t", "--help"]).output.count("Build things") == 1
    assert "Did you mean 'build'?" in runner.invoke(root_app, ["t", "biuld"]).output


def test_custom_group_class_and_its_command_order_survive_deferral() -> None:
    root_app = _build_root_app(with_callback=False, command_order=("clean", "build"))
    root_group = typer.main.get_group(root_app)

    for name in ("tools", "t"):
        group = root_group.commands[name]
        assert isinstance(group, TyperGroup)
        assert group.list_commands(typer.Context(group)) == ["clean", "build"]  # pyright: ignore[reportArgumentType]


def test_group_with_callback_stays_fully_converted() -> None:
    root_app = _build_root_app(with_callback=True, command_order=None)
    root_group = typer.main.get_group(root_app)

    for name in ("tools", "t"):
        assert sorted(root_group.commands[name].commands) == ["build", "clean"]  # pyright: ignore[reportAttributeAccessIssue]
        assert not hasattr(root_group.commands[name], "_converted_commands")
