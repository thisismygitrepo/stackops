import ast
from typing import Any

from stackops.scripts.python.graph.cli_graph_apps import load_app_model
from stackops.scripts.python.graph.cli_graph_node_utils import (
    build_aliases,
    choose_primary,
    choose_short_name,
    extend_path_tokens,
    join_command_path,
    select_help,
)
from stackops.scripts.python.graph.cli_graph_resolver import load_module
from stackops.scripts.python.graph.cli_graph_shared import (
    AppModel,
    AppRef,
    ModuleInfo,
    Registration,
)
from stackops.scripts.python.graph.cli_graph_signature import build_signature
from stackops.scripts.python.graph.cli_graph_targets import (
    registration_key,
    resolve_group_target,
    resolve_registration_callable,
)


def build_children(
    app_model: AppModel,
    parent_full_tokens: tuple[str, ...],
    parent_short_tokens: tuple[str, ...],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[Registration]] = {}
    ordered_keys: list[tuple[str, str]] = []

    for reg in app_model.registrations:
        key = registration_key(reg, app_model.module_info)
        if key not in grouped:
            grouped[key] = []
            ordered_keys.append(key)
        grouped[key].append(reg)

    children: list[dict[str, Any]] = []
    for key in ordered_keys:
        regs = grouped[key]
        primary = choose_primary(regs)
        aliases = build_aliases(regs, primary)
        if key[0] == "group":
            children.append(
                build_group_node(
                    app_model=app_model,
                    reg=primary,
                    aliases=aliases,
                    parent_full_tokens=parent_full_tokens,
                    parent_short_tokens=parent_short_tokens,
                )
            )
        else:
            children.append(
                build_command_node(
                    app_model=app_model,
                    reg=primary,
                    aliases=aliases,
                    parent_full_tokens=parent_full_tokens,
                    parent_short_tokens=parent_short_tokens,
                )
            )
    return children


def build_group_node(
    app_model: AppModel,
    reg: Registration,
    aliases: list[dict[str, Any]],
    parent_full_tokens: tuple[str, ...],
    parent_short_tokens: tuple[str, ...],
) -> dict[str, Any]:
    module_info = app_model.module_info
    child_ref = resolve_group_target(reg, module_info)
    if child_ref is None:
        raise RuntimeError(
            f"Could not resolve group target for {module_info.module}:{reg.name}"
        )

    child_model = load_app_model(child_ref)
    name = reg.name or ""
    short_name = choose_short_name(name=name, aliases=aliases)
    full_tokens = extend_path_tokens(parent_tokens=parent_full_tokens, name=name)
    short_tokens = extend_path_tokens(parent_tokens=parent_short_tokens, name=short_name)
    node: dict[str, Any] = {
        "kind": "group",
        "name": name,
        "fullPath": join_command_path(tokens=full_tokens),
        "shortPath": join_command_path(tokens=short_tokens),
        "help": select_help(reg, default=child_model.app_config.get("help")),
        "source": build_group_source(app_model, reg, child_ref),
        "app": child_model.app_config,
        "children": build_children(
            app_model=child_model,
            parent_full_tokens=full_tokens,
            parent_short_tokens=short_tokens,
        ),
    }

    if reg.context_settings is not None:
        node["command_context_settings"] = reg.context_settings

    doc_value = group_doc_value(reg, module_info)
    if doc_value:
        node["doc"] = doc_value

    if aliases:
        node["aliases"] = aliases

    return node


def build_group_source(
    app_model: AppModel, reg: Registration, child_ref: AppRef
) -> dict[str, Any]:
    source: dict[str, Any] = {
        "file": app_model.module_info.relative_path(),
        "module": app_model.ref.module,
        "dispatches_to": f"{child_ref.module}.{child_ref.factory}",
    }

    if reg.kind == "command":
        resolved = resolve_registration_callable(reg, app_model.module_info)
        if resolved is not None:
            source["callable"] = resolved.callable_name

    return source


def group_doc_value(reg: Registration, module_info: ModuleInfo) -> str | None:
    if reg.kind != "command":
        return None
    resolved = resolve_registration_callable(reg, module_info)
    if resolved is None:
        return None
    function_info = load_module(resolved.module).functions.get(resolved.callable_name)
    if function_info is None:
        return None
    return ast.get_docstring(function_info)


def build_command_node(
    app_model: AppModel,
    reg: Registration,
    aliases: list[dict[str, Any]],
    parent_full_tokens: tuple[str, ...],
    parent_short_tokens: tuple[str, ...],
) -> dict[str, Any]:
    resolved = resolve_registration_callable(reg, app_model.module_info)
    if resolved is None:
        raise RuntimeError(
            f"Could not resolve command target for {app_model.ref.module}:{reg.name}"
        )

    function_module = load_module(resolved.module)
    function_info = function_module.functions.get(resolved.callable_name)
    if function_info is None:
        raise RuntimeError(
            f"Could not find callable {resolved.module}.{resolved.callable_name}"
        )

    doc = ast.get_docstring(function_info)
    name = reg.name or resolved.callable_name.replace("_", "-")
    short_name = choose_short_name(name=name, aliases=aliases)
    full_tokens = extend_path_tokens(parent_tokens=parent_full_tokens, name=name)
    short_tokens = extend_path_tokens(parent_tokens=parent_short_tokens, name=short_name)
    node: dict[str, Any] = {
        "kind": "command",
        "name": name,
        "fullPath": join_command_path(tokens=full_tokens),
        "shortPath": join_command_path(tokens=short_tokens),
        "help": select_help(reg, default=doc),
        "source": {
            "file": function_module.relative_path(),
            "module": resolved.module,
            "callable": resolved.callable_name,
        },
        "signature": build_signature(function_module, function_info),
    }

    short_help = (
        reg.short_help if isinstance(reg.short_help, str) and reg.short_help else None
    )
    if short_help is not None:
        node["short_help"] = short_help

    if reg.context_settings is not None:
        node["command_context_settings"] = reg.context_settings

    if reg.typer_config:
        node["typer"] = reg.typer_config

    if doc:
        node["doc"] = doc

    if aliases:
        node["aliases"] = aliases

    return node