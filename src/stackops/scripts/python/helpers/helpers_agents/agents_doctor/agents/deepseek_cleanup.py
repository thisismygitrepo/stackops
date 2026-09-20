import yaml
from yaml.nodes import MappingNode, Node, ScalarNode, SequenceNode

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.hooks.models import HookRemoval


def edit_deepseek_patch(*, text: str, removals: tuple[HookRemoval, ...]) -> bytes:
    document = yaml.compose(text)
    if not isinstance(document, SequenceNode):
        raise ValueError("DeepSeek patch must be a YAML sequence")
    unique = {removal.selector: removal for removal in removals}
    selected = tuple(removal for selector, removal in unique.items()
                     if not any(selector[:index] in unique for index in range(1, len(selector))))
    for removal in sorted(selected, key=lambda item: tuple((0, part) if isinstance(part, str) else (1, part) for part in item.selector), reverse=True):
        if not removal.selector or removal.action != "delete":
            raise ValueError("DeepSeek patch cleanup requires a nonempty deletion selector")
        current: Node = document
        try:
            for part in removal.selector[:-1]:
                if isinstance(part, int) and isinstance(current, SequenceNode):
                    current = current.value[part]
                elif isinstance(part, str) and isinstance(current, MappingNode):
                    current = next(value for key, value in current.value if isinstance(key, ScalarNode) and key.value == part)
                else:
                    raise ValueError("Invalid DeepSeek patch cleanup selector")
            leaf = removal.selector[-1]
            if isinstance(leaf, int) and isinstance(current, SequenceNode):
                del current.value[leaf]
            elif isinstance(leaf, str) and isinstance(current, MappingNode):
                index = next(index for index, (key, _value) in enumerate(current.value) if isinstance(key, ScalarNode) and key.value == leaf)
                del current.value[index]
            else:
                raise ValueError("Invalid DeepSeek patch cleanup selector")
        except (IndexError, StopIteration) as error:
            raise ValueError("DeepSeek patch changed or has an invalid cleanup selector") from error
    serialized = yaml.serialize(document)
    return serialized.encode("utf-8")
