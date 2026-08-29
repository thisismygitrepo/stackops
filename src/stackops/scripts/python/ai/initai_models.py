from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from stackops.utils.schemas.fire_agents.fire_agents_types import CONFIG_AGENTS


type ArtifactAction = Literal["created", "written", "removed"]
@dataclass(frozen=True, slots=True)
class ArtifactChange:
    path: Path
    action: ArtifactAction


@dataclass(frozen=True, slots=True)
class InitConfigPlan:
    repo_root: Path
    frameworks: tuple[CONFIG_AGENTS, ...]
    include_common_scaffold: bool
    add_all_touched_configs_to_gitignore: bool
    add_vscode_task: bool
    add_private_config: bool
    add_instructions: bool
    add_agentops_skill: bool


@dataclass(frozen=True, slots=True)
class InitConfigResult:
    plan: InitConfigPlan
    artifact_changes: tuple[ArtifactChange, ...]
    elapsed_seconds: float
