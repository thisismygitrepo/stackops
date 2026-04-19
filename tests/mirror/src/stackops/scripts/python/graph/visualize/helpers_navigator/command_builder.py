

from dataclasses import dataclass
from typing import cast

from textual.widgets import Input

from stackops.scripts.python.graph.visualize.helpers_navigator.command_builder import (
    CommandBuilderScreen,
)
from stackops.scripts.python.graph.visualize.helpers_navigator.data_models import (
    ArgumentInfo,
    CommandInfo,
)


class CommandBuilderHarness(CommandBuilderScreen):
    def build_command_for_test(self) -> str:
        return self._build_command()


@dataclass
class FakeInput:
    value: str


def test_parse_arguments_extracts_options_flags_and_positionals() -> None:
    command_info = CommandInfo(
        name="render",
        description="Render graph",
        command="graph render",
        help_text="""
        --output <dest>
        --force
        <target>
        <dest>
        """,
        arguments=None,
    )

    screen = CommandBuilderHarness(command_info)

    assert [argument.name for argument in screen.arguments] == ["output", "force", "target"]

    output, force, target = screen.arguments
    assert output.flag == "--output"
    assert output.placeholder == "dest"
    assert not output.is_flag

    assert force.is_flag
    assert force.flag == "--force"

    assert target.is_positional
    assert target.is_required


def test_build_command_uses_positional_flags_negated_flags_and_explicit_flag_values() -> None:
    command_info = CommandInfo(
        name="render",
        description="Render graph",
        command="graph render",
        arguments=[
            ArgumentInfo(
                name="target",
                is_required=True,
                is_flag=False,
                is_positional=True,
                placeholder="target",
            ),
            ArgumentInfo(
                name="verbose",
                is_required=False,
                is_flag=True,
                flag="--verbose",
                negated_flag="--no-verbose",
            ),
            ArgumentInfo(
                name="confirm",
                is_required=False,
                is_flag=True,
                flag="--confirm",
            ),
            ArgumentInfo(
                name="format",
                is_required=False,
                is_flag=False,
                flag="--format",
                placeholder="format",
            ),
        ],
    )

    screen = CommandBuilderHarness(command_info)
    screen.input_widgets = cast(
        dict[str, Input],
        {
            "target": FakeInput(value="graph.json"),
            "verbose": FakeInput(value="no"),
            "confirm": FakeInput(value="--force"),
            "format": FakeInput(value="svg"),
        },
    )

    built_command = screen.build_command_for_test()

    assert built_command == "graph render graph.json --no-verbose --force --format svg"
