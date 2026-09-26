from pathlib import Path
from typing import Final, cast

import yaml

from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.solutions.omp.constants import OPENROUTER_ZDR_EXTENSION, OPENROUTER_ZDR_EXTENSION_PATH
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path


DEFAULT_OMP_CONFIG: Final[str] = """retry:
  enabled: true
  maxRetries: 10
  baseDelayMs: 500
  maxDelayMs: 300000
"""


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    if add_instructions:
        instructions_text = get_generic_instructions_path().read_text(encoding="utf-8")
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath("AGENTS.md"),
            content=instructions_text,
            write_mode="if_missing",
        )
        if change is not None:
            changes.append(change)

    if add_private_config:
        config_path = repo_root.joinpath(".omp/config.yml")
        config_text = config_path.read_text(encoding="utf-8") if config_path.exists() else DEFAULT_OMP_CONFIG
        loaded_config: object = yaml.safe_load(config_text)
        if not isinstance(loaded_config, dict):
            raise ValueError(f"""Expected a YAML mapping in {config_path}""")
        config = cast(dict[str, object], loaded_config)
        extensions = config.get("extensions", [])
        if not isinstance(extensions, list) or not all(isinstance(path, str) for path in extensions):
            raise ValueError(f"""Expected extensions to be a list of paths in {config_path}""")
        if OPENROUTER_ZDR_EXTENSION_PATH not in extensions:
            config["extensions"] = [*extensions, OPENROUTER_ZDR_EXTENSION_PATH]
        disabled_extensions = config.get("disabledExtensions", [])
        if isinstance(disabled_extensions, list) and "extension-module:stackops-openrouter-zdr" in disabled_extensions:
            config["disabledExtensions"] = [
                extension for extension in disabled_extensions if extension != "extension-module:stackops-openrouter-zdr"
            ]
        updated_config = yaml.safe_dump(config, sort_keys=False)
        if updated_config != config_text:
            change = write_text_artifact(
                repo_root=repo_root,
                path=config_path,
                content=updated_config,
                write_mode="always",
            )
            if change is not None:
                changes.append(change)
        change = write_text_artifact(
            repo_root=repo_root,
            path=repo_root.joinpath(OPENROUTER_ZDR_EXTENSION_PATH),
            content=OPENROUTER_ZDR_EXTENSION,
            write_mode="always",
        )
        if change is not None:
            changes.append(change)
    return tuple(changes)
