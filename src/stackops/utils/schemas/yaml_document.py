from collections.abc import Mapping
from typing import override

import yaml


class _StackopsYamlDumper(yaml.SafeDumper):
    @override
    def ignore_aliases(self, data: object) -> bool:
        return True

    @override
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:  # defaults mirror the PyYAML Emitter signature
        super().increase_indent(flow=flow, indentless=False)


def yaml_document_text(document: Mapping[str, object]) -> str:
    return yaml.dump(document, Dumper=_StackopsYamlDumper, sort_keys=False, default_flow_style=False, allow_unicode=True, width=float("inf"))
