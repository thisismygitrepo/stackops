import json
from collections.abc import MutableMapping, MutableSequence
from typing import cast

import tomlkit
import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookRemoval, HookSelector
from stackops.utils.files.read import remove_c_style_comments


def _unique_json_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate configuration key: {key}")
        result[key] = value
    return result


def _selector_key(selector: HookSelector) -> tuple[tuple[int, str, int], ...]:
    return tuple((0, part, 0) if isinstance(part, str) else (1, "", part) for part in selector)


def _validate_yaml_keys(*, text: str) -> None:
    root = yaml.compose(text)
    pending: list[Node] = [root] if root is not None else []
    visited: set[int] = set()
    while pending:
        node = pending.pop()
        if id(node) in visited:
            continue
        visited.add(id(node))
        if isinstance(node, MappingNode):
            keys: set[str] = set()
            for key, value in node.value:
                if not isinstance(key, ScalarNode) or key.tag != "tag:yaml.org,2002:str":
                    raise ValueError("YAML configuration requires string mapping keys")
                if key.value in keys:
                    raise ValueError(f"Duplicate configuration key: {key.value}")
                keys.add(key.value)
                pending.append(value)
        elif isinstance(node, SequenceNode):
            pending.extend(node.value)


def _edit_document(*, document: object, removal: HookRemoval) -> None:
    if not removal.selector:
        raise ValueError(f"Empty selector for structured configuration: {removal.path}")
    current = document
    for part in removal.selector[:-1]:
        if isinstance(part, str) and isinstance(current, MutableMapping):
            current = cast(MutableMapping[str, object], current)[part]
        elif isinstance(part, int) and isinstance(current, MutableSequence):
            current = cast(MutableSequence[object], current)[part]
        else:
            raise ValueError(f"Invalid configuration selector in {removal.path}: {removal.selector}")
    leaf = removal.selector[-1]
    if isinstance(leaf, str) and isinstance(current, MutableMapping):
        mapping = cast(MutableMapping[str, object], current)
        if removal.action == "disable":
            mapping[leaf] = False
        else:
            del mapping[leaf]
    elif isinstance(leaf, int) and isinstance(current, MutableSequence):
        sequence = cast(MutableSequence[object], current)
        if removal.action == "disable":
            sequence[leaf] = False
        else:
            del sequence[leaf]
    else:
        raise ValueError(f"Invalid configuration selector in {removal.path}: {removal.selector}")


def edit_cleanup_document(*, original: bytes, removals: tuple[HookRemoval, ...]) -> bytes:
    formats = {removal.format for removal in removals}
    if len(formats) != 1:
        raise ValueError("Conflicting configuration formats in cleanup plan")
    document_format = removals[0].format
    text = original.decode("utf-8")
    match document_format:
        case "json":
            document: object = json.loads(remove_c_style_comments(text), object_pairs_hook=_unique_json_keys)
        case "toml":
            document = tomlkit.parse(text)
        case "yaml":
            _validate_yaml_keys(text=text)
            document = yaml.safe_load(text)
        case _:
            raise ValueError(f"Cannot edit structured configuration as {document_format}")
    unique = {removal.selector: removal for removal in removals}
    selected = tuple(
        removal for selector, removal in unique.items()
        if not any(selector[:index] in unique and unique[selector[:index]].action == "delete" for index in range(1, len(selector)))
    )
    try:
        for removal in sorted(selected, key=lambda item: _selector_key(item.selector), reverse=True):
            _edit_document(document=document, removal=removal)
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError(f"Configuration changed or has an invalid cleanup selector: {error}") from error
    match document_format:
        case "json":
            result = json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        case "toml":
            result = tomlkit.dumps(cast(MutableMapping[str, object], document))
        case "yaml":
            result = yaml.safe_dump(document, sort_keys=False, allow_unicode=True)
        case _:
            raise ValueError(f"Cannot serialize configuration as {document_format}")
    return result.encode("utf-8")
