

from rich.console import Console, RenderableType
from rich.panel import Panel
from rich.table import Table
from pytest import MonkeyPatch

from stackops.scripts.python.graph.visualize.helpers_navigator.command_detail import (
    CommandDetail,
)
from stackops.scripts.python.graph.visualize.helpers_navigator.data_models import (
    ArgumentInfo,
    CommandInfo,
)


class CommandDetailHarness(CommandDetail):
    def render_command_for_test(self, command_info: CommandInfo) -> Panel:
        return self._render_command(command_info)

    def format_usage_for_test(self, command_info: CommandInfo) -> str:
        return self._format_usage(command_info)

    def build_options_table_for_test(self, arguments: list[ArgumentInfo]) -> Table:
        return self._build_options_table(arguments)

    def format_option_flags_for_test(self, argument: ArgumentInfo) -> str:
        return self._format_option_flags(argument)


def test_update_command_renders_empty_state_and_group_panel(monkeypatch: MonkeyPatch) -> None:
    detail = CommandDetailHarness(id="command-detail")
    updates: list[RenderableType | str] = []

    def record_update(renderable: RenderableType | str) -> None:
        updates.append(renderable)

    monkeypatch.setattr(detail, "update", record_update)

    detail.update_command(None)
    detail.update_command(
        CommandInfo(
            name="graph",
            description="Graph tools",
            command="graph",
            is_group=True,
            long_description="Inspect graph commands",
            module_path="stackops.graph",
        )
    )

    assert updates[0] == "Select a command to view details"
    assert isinstance(updates[1], Panel)


def test_render_command_formats_usage_and_options_table() -> None:
    detail = CommandDetailHarness(id="command-detail")
    command_info = CommandInfo(
        name="render",
        description="Render graph",
        command="graph render",
        long_description="Render graph to file",
        module_path="stackops.graph.render",
        arguments=[
            ArgumentInfo(
                name="target",
                is_required=True,
                is_flag=False,
                is_positional=True,
                placeholder="path",
                description="Target path",
            ),
            ArgumentInfo(
                name="verbose",
                is_required=False,
                is_flag=True,
                flag="--verbose",
                negated_flag="--no-verbose",
                long_flags=["--verbose", "--no-verbose"],
                short_flags=["-v"],
                description="Verbose mode",
            ),
            ArgumentInfo(
                name="format",
                is_required=False,
                is_flag=False,
                flag="--format",
                long_flags=["--format"],
                short_flags=["-f"],
                placeholder="kind",
                description="Output format",
            ),
        ],
    )
    arguments = command_info.arguments
    assert arguments is not None

    panel = detail._render_command(command_info)
    usage = detail._format_usage(command_info)
    options_table = detail._build_options_table(command_info.arguments or [])
    panel = detail.render_command_for_test(command_info)
    usage = detail.format_usage_for_test(command_info)
    options_table = detail.build_options_table_for_test(arguments)
    console = Console(record=True, width=120)
    console.print(options_table)
    rendered_options = console.export_text()

    assert isinstance(panel, Panel)
    assert usage == "graph render [OPTIONS] PATH"
    assert detail._format_option_flags(command_info.arguments[1]) == "--verbose / --no-verbose, -v"
    assert detail._format_option_flags(command_info.arguments[2]) == "--format, -f"
    assert detail.format_option_flags_for_test(arguments[1]) == "--verbose / --no-verbose, -v"
    assert detail.format_option_flags_for_test(arguments[2]) == "--format, -f"
    assert "--help" in rendered_options
    assert "--verbose / --no-verbose" in rendered_options
    assert "--format, -f <KIND>" in rendered_options
