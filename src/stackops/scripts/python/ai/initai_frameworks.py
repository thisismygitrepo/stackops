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
from stackops.utils.schemas.fire_agents.fire_agents_types import AGENTS


def build_framework_config(*, repo_root: Path, framework: AGENTS, add_private_config: bool, add_instructions: bool) -> None:
    match framework:
        case "agy":
            antigravity.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "copilot":
            github_copilot.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "cursor-agent":
            cursors.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "claude":
            claude.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "crush":
            crush.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "cline":
            cline.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "qwen":
            qwen_code.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "codex":
            codex.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "forge":
            forge.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "q":
            amazon_q.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "opencode":
            opencode.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "kilocode":
            kilocode.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "auggie":
            auggie.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "oz":
            oz.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "droid":
            droid.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case "pi":
            pi.build_configuration(repo_root=repo_root, add_private_config=add_private_config, add_instructions=add_instructions)
        case _:
            raise ValueError(f"Unsupported agent configuration target: {framework}")
