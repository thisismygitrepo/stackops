from pathlib import Path

from stackops.scripts.python.ai.solutions.antigravity import antigravity
from stackops.scripts.python.ai.solutions.auggie import auggie
from stackops.scripts.python.ai.solutions.claude import claude
from stackops.scripts.python.ai.solutions.cline import cline
from stackops.scripts.python.ai.solutions.codex import codex
from stackops.scripts.python.ai.solutions.copilot import github_copilot
from stackops.scripts.python.ai.solutions.crush import crush
from stackops.scripts.python.ai.solutions.cursor import cursors
from stackops.scripts.python.ai.solutions.droid import droid
from stackops.scripts.python.ai.solutions.forge import forge
from stackops.scripts.python.ai.solutions.kilocode import kilocode
from stackops.scripts.python.ai.solutions.opencode import opencode
from stackops.scripts.python.ai.solutions.oz import oz
from stackops.scripts.python.ai.solutions.pi import pi
from stackops.scripts.python.ai.solutions.q import amazon_q
from stackops.scripts.python.ai.solutions.qwen_code import qwen_code
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


def build_framework_config(
    *, repo_root: Path, framework: AGENTS, add_private_config: bool, add_instructions: bool
) -> tuple[ArtifactChange, ...]:
    match framework:
        case "agy":
            return antigravity.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "copilot":
            return github_copilot.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "cursor-agent":
            return cursors.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "claude":
            return claude.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "crush":
            return crush.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "cline":
            return cline.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "qwen":
            return qwen_code.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "codex":
            return codex.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "forge":
            return forge.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "q":
            return amazon_q.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "opencode":
            return opencode.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "kilocode":
            return kilocode.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "auggie":
            return auggie.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "oz":
            return oz.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "droid":
            return droid.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case "pi":
            return pi.build_configuration(
                repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions
            )
        case _:
            raise ValueError(f"Unsupported agent configuration target: {framework}")
