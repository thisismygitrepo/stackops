import json
import re
from pathlib import Path
from typing import cast

from stackops.utils.files.read import remove_c_style_comments


def read_openrouter_config(path: Path) -> dict[str, object]:
    text = remove_c_style_comments(path.read_text(encoding="utf-8"))
    normalized_text = re.sub(r'("(?:\\.|[^"\\])*")|,\s*(?=[}\]])', r"\1", text)
    return cast(dict[str, object], json.loads(normalized_text))


def enforce_openrouter_zdr(config: dict[str, object]) -> None:
    providers = cast(dict[str, object], config.setdefault("provider", {}))
    openrouter = cast(dict[str, object], providers.setdefault("openrouter", {}))
    options = cast(dict[str, object], openrouter.setdefault("options", {}))
    extra_body = cast(dict[str, object], options.setdefault("extraBody", {}))
    routing = cast(dict[str, object], extra_body.setdefault("provider", {}))
    routing["zdr"] = True
    models = cast(dict[str, dict[str, object]], openrouter.get("models", {}))
    for model in models.values():
        variants = cast(dict[str, dict[str, object]], model.get("variants", {}))
        model_options = cast(dict[str, object], model.get("options", {}))
        for model_routing_options in (model_options, *variants.values()):
            if "provider" in model_routing_options:
                model_routing = cast(dict[str, object], model_routing_options["provider"])
                model_routing["zdr"] = True
    agents = cast(dict[str, dict[str, object]], config.get("agent", {}))
    for agent in agents.values():
        model_id = agent.get("model")
        if isinstance(model_id, str) and not model_id.startswith("openrouter/"):
            continue
        if "provider" in agent:
            agent_routing = cast(dict[str, object], agent["provider"])
            agent_routing["zdr"] = True
