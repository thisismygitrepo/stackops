import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import stackops.scripts.python.graph as graph_assets
from stackops.utils.path_reference import get_path_reference_path

REPO_ROOT = Path(__file__).resolve().parents[5]
SRC_ROOT = REPO_ROOT / "src"
ROOT_MODULE = "stackops.scripts.python.stackops_entry"
ROOT_FACTORY = "get_app"
DEFAULT_OUTPUT_PATH = get_path_reference_path(
    module=graph_assets,
    path_reference=graph_assets.CLI_GRAPH_PATH_REFERENCE,
)


@dataclass(frozen=True)
class AppRef:
    module: str
    factory: str = "get_app"


@dataclass
class ModuleInfo:
    module: str
    path: Path
    tree: ast.Module
    source: str
    lines: list[str]
    functions: dict[str, ast.FunctionDef] = field(default_factory=dict)
    imported_modules: dict[str, str] = field(default_factory=dict)
    imported_names: dict[str, tuple[str, str]] = field(default_factory=dict)
    assignments: dict[str, ast.AST] = field(default_factory=dict)

    def relative_path(self) -> str:
        return self.path.relative_to(REPO_ROOT).as_posix()


@dataclass
class Registration:
    kind: str
    app_var: str
    target_expr: ast.AST
    order: int
    local_modules: dict[str, str] = field(default_factory=dict)
    local_names: dict[str, tuple[str, str]] = field(default_factory=dict)
    name: str | None = None
    hidden: bool = False
    help: Any = None
    short_help: Any = None
    context_settings: Any = None
    typer_config: dict[str, Any] = field(default_factory=dict)


@dataclass
class AppModel:
    ref: AppRef
    module_info: ModuleInfo
    app_var: str
    app_config: dict[str, Any]
    registrations: list[Registration]


@dataclass
class ResolvedCallable:
    module: str
    callable_name: str

    def module_ref(self) -> str:
        return f"{self.module}.{self.callable_name}"


MODULE_CACHE: dict[str, ModuleInfo] = {}
APP_CACHE: dict[AppRef, AppModel] = {}
EXPORT_CACHE: dict[tuple[str, str], Any] = {}


class Unresolved:
    def __init__(self, text: str) -> None:
        self.text = text

    def __repr__(self) -> str:
        return self.text