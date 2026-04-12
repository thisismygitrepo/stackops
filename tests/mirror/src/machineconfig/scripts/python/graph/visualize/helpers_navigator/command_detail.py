from __future__ import annotations

from rich.console import Console, RenderableType
from rich.panel import Panel

from machineconfig.scripts.python.graph.visualize.helpers_navigator.command_detail import CommandDetail
from machineconfig.scripts.python.graph.visualize.helpers_navigator.data_models import ArgumentInfo, CommandInfo


def test_update_command_renders_empty_state_and_group_panel(monkeypatch: object) -> None:
    detail = CommandDetail(id="command-detail")
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
            module_path="machineconfig.graph",
        )
    )

    assert updates[0] == "Select a command to view details"
    assert isinstance(updates[1], Panel)


def test_render_command_formats_usage_and_options_table() -> None:
    detail = CommandDetail(id="command-detail")
    command_info = CommandInfo(
        name="render",
        description="Render graph",
        command="graph render",
        long_description="Render graph to file",
        module_path="machineconfig.graph.render",
        arguments=[
            ArgumentInfo(name="target", is_required=True, is_flag=False, is_positional=True, placeholder="path", description="Target path"),
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

    panel = detail._render_command(command_info)
    usage = detail._format_usage(command_info)
    options_table = detail._build_options_table(command_info.arguments or [])
    console = Console(record=True, width=120)
    console.print(options_table)
    rendered_options = console.export_text()

    assert isinstance(panel, Panel)
    assert usage == "graph render [OPTIONS] PATH"
    assert detail._format_option_flags(command_info.arguments[1]) == "--verbose / --no-verbose, -v"
    assert detail._format_option_flags(command_info.arguments[2]) == "--format, -f"
    assert "--help" in rendered_options
    assert "--verbose / --no-verbose" in rendered_options
    assert "--format, -f <KIND>" in rendered_options
