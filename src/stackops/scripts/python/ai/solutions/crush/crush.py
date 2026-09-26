import json
import os
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def _enforce_provider_options(settings: dict[str, object], inherited: dict[str, object]) -> None:
    options = cast(dict[str, object], settings.setdefault("provider_options", {}))
    extra_body = cast(dict[str, object], options.setdefault("extra_body", {}))
    provider = {
        **inherited,
        **cast(dict[str, object], options.get("provider", {})),
        **cast(dict[str, object], extra_body.get("provider", {})),
        "zdr": True,
    }
    extra_body["provider"] = provider


def _enforce_openrouter_zdr(repo_root: Path) -> tuple[ArtifactChange, ...]:
    paths = [repo_root.joinpath(".crush.json")]
    if repo_root.joinpath("crush.json").exists():
        paths.append(repo_root.joinpath("crush.json"))
    configurations: dict[Path, dict[str, object]] = {
        path: cast(dict[str, object], json.loads(path.read_text(encoding="utf-8"))) if path.exists() else {}
        for path in paths
    }
    originals = {path: json.dumps(settings) for path, settings in configurations.items()}
    primary_providers = cast(dict[str, object], configurations[paths[0]].setdefault("providers", {}))
    primary_providers.setdefault("openrouter", {})
    native_providers: set[str] = set()
    for settings in configurations.values():
        providers = cast(dict[str, dict[str, object]], settings.get("providers", {}))
        for name, provider in providers.items():
            base_url = os.path.expandvars(str(provider.get("base_url", "")))
            host = urlsplit(base_url).hostname or ""
            if (
                name != "openrouter"
                and provider.get("type") != "openrouter"
                and host != "openrouter.ai"
                and not host.endswith(".openrouter.ai")
            ):
                continue
            provider_type = provider.get("type", "openrouter")
            if provider_type == "openai-compat":
                extra_body = cast(dict[str, object], provider.setdefault("extra_body", {}))
                routing = cast(dict[str, object], extra_body.setdefault("provider", {}))
                routing["zdr"] = True
            elif provider_type in ("openai", "openrouter"):
                provider["type"] = "openrouter"
                native_providers.add(name)
                extra_body = cast(dict[str, object], provider.get("extra_body", {}))
                _enforce_provider_options(provider, inherited=cast(dict[str, object], extra_body.get("provider", {})))
    changes: list[ArtifactChange] = []
    for path, settings in configurations.items():
        models = cast(dict[str, dict[str, object]], settings.get("models", {}))
        for model in models.values():
            provider_name = str(model.get("provider", ""))
            if provider_name in native_providers:
                _enforce_provider_options(model, inherited={})
        if originals[path] == json.dumps(settings):
            continue
        change = write_text_artifact(
            repo_root=repo_root,
            path=path,
            content=json.dumps(settings, indent=2) + "\n",
            write_mode="always",
        )
        assert change is not None
        changes.append(change)
    return tuple(changes)


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("CRUSH.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)

    if add_private_config:
        changes.extend(_enforce_openrouter_zdr(repo_root))
    return tuple(changes)
