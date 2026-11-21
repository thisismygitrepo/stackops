import importlib
import json
import re
from enum import Enum
from typing import Literal, TypedDict, cast

from stackops.scripts.python.graph.visualize.graph_paths import DEFAULT_GRAPH_PATH
from stackops.scripts.python.helpers.helpers_serve.constants import LOCAL_PATH_PARAMETER_NAMES

SUMMARY_PATTERN = re.compile(r"^(?:(?P<icon>[^\w\s<]\S*)\s+)?(?:<(?P<alias>[^>\s]+)>\s+)?(?P<summary>.*)$")

type ParameterControl = Literal["switch", "choice", "path", "number", "text"]


class CommandNode(TypedDict):
    name: str
    path: str
    short_path: str
    kind: Literal["root", "group", "command"]
    icon: str
    summary: str
    description: str
    children: list["CommandNode"]


class CommandSource(TypedDict):
    module: str
    callable: str


class ParameterSpec(TypedDict):
    name: str
    kind: Literal["option", "argument"]
    flags: list[str]
    off_flags: list[str]
    control: ParameterControl
    choices: list[str]
    multiple: bool
    required: bool
    default: str
    help: str


def load_command_tree() -> tuple[CommandNode, dict[str, CommandSource]]:
    graph = cast(dict[str, object], json.loads(DEFAULT_GRAPH_PATH.read_text(encoding="utf-8")))
    sources: dict[str, CommandSource] = {}

    def convert(raw_node: dict[str, object]) -> CommandNode:
        kind = cast(Literal["root", "group", "command"], raw_node["kind"])
        path = cast(str, raw_node["fullPath"])
        help_text = cast(str, raw_node.get("help") or raw_node.get("doc") or "")
        headline = cast(str, raw_node.get("short_help") or help_text).strip().split("\n", maxsplit=1)[0]
        headline_match = SUMMARY_PATTERN.match(headline)
        description_lines = help_text.strip().split("\n")
        description_match = SUMMARY_PATTERN.match(description_lines[0])
        if headline_match is None or description_match is None:
            raise ValueError(f"""Cannot read the help text of CLI graph node `{path}`.""")
        if kind == "command":
            source = cast(dict[str, str], raw_node["source"])
            sources[path] = {"module": source["module"], "callable": source["callable"]}
        return {
            "name": cast(str, raw_node["name"]),
            "path": path,
            "short_path": cast(str, raw_node["shortPath"]),
            "kind": kind,
            "icon": headline_match["icon"] or "",
            "summary": headline_match["summary"],
            "description": "\n".join([description_match["summary"], *description_lines[1:]]),
            "children": [convert(child) for child in cast(list[dict[str, object]], raw_node.get("children", []))],
        }

    return convert(cast(dict[str, object], graph["root"])), sources


def load_command_parameters(source: CommandSource) -> list[ParameterSpec] | None:
    import typer
    import typer.main
    from typer.core import TyperArgument, TyperOption

    function = getattr(importlib.import_module(source["module"]), source["callable"], None)
    if not callable(function):
        return None
    app = typer.Typer(add_completion=False)
    app.command()(function)
    specs: list[ParameterSpec] = []
    for parameter in typer.main.get_command(app).params:
        if not isinstance(parameter, TyperArgument | TyperOption) or parameter.hidden:
            continue
        descriptor = parameter.type_descriptor
        is_option = isinstance(parameter, TyperOption)
        raw_choices = [str(choice.value) if isinstance(choice, Enum) else str(choice) for choice in cast(tuple[object, ...], descriptor.choices or ())]
        # Loose literals list a one or two letter alias right after each full value; the form only needs the full values.
        # Design choice: the CLI does not mark its aliases, so one is recognised by its letters appearing in order in the value before it.
        # That keeps real short values (pi, q, oz, t3), and would hide one that happens to be spelled out of its predecessor.
        choices = [
            choice
            for index, choice in enumerate(raw_choices)
            if not (
                len(choice) <= 2
                and index > 0
                and len(raw_choices[index - 1]) > len(choice)
                and re.search(".*".join(re.escape(letter) for letter in choice), raw_choices[index - 1], re.IGNORECASE)
            )
        ]
        control: ParameterControl
        if isinstance(parameter, TyperOption) and (parameter.is_flag or parameter.count):
            control = "switch"
        elif choices:
            control = "choice"
        elif descriptor.is_path or (descriptor.annotation is str and parameter.name in LOCAL_PATH_PARAMETER_NAMES):
            control = "path"
        elif descriptor.annotation in (int, float):
            control = "number"
        else:
            control = "text"
        default: object = parameter.default
        if isinstance(default, Enum):
            default = default.value
        if isinstance(default, bool):
            default_text = "true" if default else ""
        elif isinstance(default, list | tuple):
            default_text = " ".join(str(item) for item in cast(list[object], default))
        elif default is None or callable(default):
            default_text = ""
        else:
            default_text = str(default)
        specs.append(
            {
                "name": parameter.name or "",
                "kind": "option" if is_option else "argument",
                "flags": list(parameter.opts) if is_option else [],
                "off_flags": list(parameter.secondary_opts) if is_option else [],
                "control": control,
                "choices": choices,
                "multiple": bool(getattr(parameter, "multiple", False)) or parameter.nargs == -1,
                "required": parameter.required,
                "default": default_text,
                "help": " ".join((parameter.help or "").split()),
            }
        )
    return specs
