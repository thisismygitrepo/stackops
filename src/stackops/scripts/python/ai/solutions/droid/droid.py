import json
import os
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("DROID.md"),
            content=instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)
    if add_private_config:
        for filename in ("settings.json", "settings.local.json"):
            path = repo_root.joinpath(".factory", filename)
            if not path.exists():
                continue
            settings = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
            original = json.dumps(settings)
            models = cast(list[dict[str, object]], settings.get("customModels", []))
            for model in models:
                base_url = os.path.expandvars(str(model.get("baseUrl", "")))
                host = urlsplit(base_url).hostname or ""
                if host != "openrouter.ai" and not host.endswith(".openrouter.ai"):
                    continue
                extra_args = cast(dict[str, object], model.setdefault("extraArgs", {}))
                provider = cast(dict[str, object], extra_args.setdefault("provider", {}))
                provider["zdr"] = True
            if original == json.dumps(settings):
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
