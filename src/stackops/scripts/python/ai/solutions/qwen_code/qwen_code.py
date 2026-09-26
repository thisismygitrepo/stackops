import json
import os
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def _enforce_openrouter_zdr(repo_root: Path) -> ArtifactChange | None:
    path = repo_root.joinpath(".qwen/settings.json")
    settings = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8"))) if path.exists() else {}
    original = json.dumps(settings)
    security = cast(dict[str, object], settings.get("security", {}))
    auth = cast(dict[str, object], security.get("auth", {}))
    runtime_url = str(auth.get("baseUrl", ""))
    runtime_host = urlsplit(os.path.expandvars(runtime_url)).hostname or ""
    targets: list[dict[str, object]] = []
    if auth.get("selectedType") in ("openai", "openai-responses") and (
        runtime_host == "openrouter.ai" or runtime_host.endswith(".openrouter.ai")
    ):
        targets.append(cast(dict[str, object], settings.setdefault("model", {})))
    providers = cast(dict[str, list[dict[str, object]]], settings.get("modelProviders", {}))
    protocols = cast(dict[str, str], settings.get("providerProtocol", {}))
    for provider_name, models in providers.items():
        if protocols.get(provider_name, provider_name) not in ("openai", "openai-responses"):
            continue
        for model in models:
            base_url = str(model.get("baseUrl", runtime_url))
            host = urlsplit(os.path.expandvars(base_url)).hostname or ""
            if host == "openrouter.ai" or host.endswith(".openrouter.ai"):
                targets.append(model)
    for model in targets:
        generation = cast(dict[str, object], model.setdefault("generationConfig", {}))
        extra_body = cast(dict[str, object], generation.setdefault("extra_body", {}))
        provider = cast(dict[str, object], extra_body.setdefault("provider", {}))
        provider["zdr"] = True
    if original == json.dumps(settings):
        return None
    return write_text_artifact(
        repo_root=repo_root,
        path=path,
        content=json.dumps(settings, indent=2) + "\n",
        write_mode="always",
    )


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("QWEN.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)
    if add_private_config:
        change = _enforce_openrouter_zdr(repo_root)
        if change is not None:
            changes.append(change)
    return tuple(changes)
