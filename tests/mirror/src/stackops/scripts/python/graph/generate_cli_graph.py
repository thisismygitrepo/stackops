import ast
from typing import cast

import stackops.scripts.python.graph.generate_cli_graph as target


def _first_argument_annotation(source: str) -> ast.AST | None:
    module = ast.parse(source)
    function_node = cast(ast.FunctionDef, module.body[0])
    return function_node.args.args[0].annotation


def test_default_output_path_exists() -> None:
    assert target.DEFAULT_OUTPUT_PATH.name == "cli_graph.json"
    assert target.DEFAULT_OUTPUT_PATH.exists()
    assert target.DEFAULT_OUTPUT_PATH.is_file()


def test_module_to_path_resolves_modules_and_packages() -> None:
    module_path = target.module_to_path(
        "stackops.scripts.python.graph.generate_cli_graph"
    )
    package_path = target.module_to_path("stackops.scripts.python.graph")

    assert module_path.name == "generate_cli_graph.py"
    assert package_path.name == "__init__.py"


def test_extract_typer_info_parses_flags_help_and_default() -> None:
    annotation = _first_argument_annotation(
        """
def func(
    verbose: Annotated[
        bool,
        typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    ],
) -> None:
    pass
"""
    )

    typer_info = target.extract_typer_info(annotation)

    assert typer_info == {
        "kind": "option",
        "param_decls": ["--verbose", "-v"],
        "long_flags": ["--verbose"],
        "short_flags": ["-v"],
        "help": "Enable verbose output",
        "default": False,
    }


def test_build_cli_graph_returns_root_payload() -> None:
    payload = target.build_cli_graph()
    root = payload["root"]

    assert payload["schema"]["version"] == "1.0"
    assert root["kind"] == "root"
    assert root["name"] == "mcfg"
    assert root["source"]["module"] == target.ROOT_MODULE
    assert isinstance(root["children"], list)
    assert len(root["children"]) > 0
