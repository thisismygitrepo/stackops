from pathlib import Path

import stackops.scripts.python.ai.solutions.copilot as copilot_assets
from stackops.scripts.python.ai.initai_artifacts import write_text_artifact
from stackops.scripts.python.ai.initai_models import ArtifactChange
from stackops.scripts.python.ai.utils.shared import get_generic_instructions_path



def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> tuple[ArtifactChange, ...]:
    changes: list[ArtifactChange] = []
    instructions_repository_dir = Path(copilot_assets.__file__).resolve().parent.joinpath("instructions")
    agents_dir = Path(copilot_assets.__file__).resolve().parent.joinpath("agents")
    prompts_dir = Path(copilot_assets.__file__).resolve().parent.joinpath("prompts")

    github_dir = repo_root.joinpath(".github")
    agents_target_dir = github_dir.joinpath("agents")
    prompts_target_dir = github_dir.joinpath("prompts")
    instructions_target_dir = github_dir.joinpath("instructions")

    if add_private_config:
        for agent_profile in sorted(agents_dir.iterdir()):
            if agent_profile.is_file() is False:
                continue
            if agent_profile.name.endswith(".agent.md"):
                target_name = agent_profile.name
            else:
                target_name = f"{agent_profile.name.split('.')[0]}.agent.md"
            agent_target = agents_target_dir.joinpath(target_name)
            change = write_text_artifact(
                repo_root=repo_root,
                path=agent_target,
                content=agent_profile.read_text(encoding="utf-8"),
                write_mode="always",
            )
            assert change is not None
            changes.append(change)

        for prompt in sorted(prompts_dir.iterdir()):
            if prompt.is_file() is False:
                continue
            if prompt.name.endswith(".prompt.md"):
                target_name = prompt.name
            else:
                target_name = f"{prompt.name.split('.')[0]}.prompt.md"
            prompt_target = prompts_target_dir.joinpath(target_name)
            change = write_text_artifact(
                repo_root=repo_root,
                path=prompt_target,
                content=prompt.read_text(encoding="utf-8"),
                write_mode="always",
            )
            assert change is not None
            changes.append(change)

    if add_instructions:
        for instruction in sorted(instructions_repository_dir.rglob("*.md")):
            if instruction.name.endswith(".instructions.md"):
                target_name = instruction.name
            else:
                target_name = f"{instruction.name.split('.')[0]}.instructions.md"
            instruction_target = instructions_target_dir.joinpath(target_name)
            change = write_text_artifact(
                repo_root=repo_root,
                path=instruction_target,
                content=instruction.read_text(encoding="utf-8"),
                write_mode="always",
            )
            assert change is not None
            changes.append(change)

        generic_instructions_path = get_generic_instructions_path()
        change = write_text_artifact(
            repo_root=repo_root,
            path=github_dir.joinpath("copilot-instructions.md"),
            content=generic_instructions_path.read_text(encoding="utf-8"),
            write_mode="always",
        )
        assert change is not None
        changes.append(change)
    return tuple(changes)
