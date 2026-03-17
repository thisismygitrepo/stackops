
from pathlib import Path

from machineconfig.scripts.python.ai.utils.shared import get_generic_instructions_path


def build_configuration(repo_root: Path, add_private_config: bool, add_instructions: bool) -> None:
    if add_instructions:
        instructions_path = get_generic_instructions_path()
        instructions_text = instructions_path.read_text(encoding="utf-8")

        # opencode_instructions_dir = repo_root.joinpath(".github/instructions")
        # opencode_instructions_dir.mkdir(parents=True, exist_ok=True)
        # opencode_rules_path = opencode_instructions_dir.joinpath("opencode_rules.md")
        # opencode_rules_path.write_text(data=instructions_text, encoding="utf-8")

        agents_path = repo_root.joinpath("AGENTS.md")
        if agents_path.exists() is False:
            agents_path.write_text(data=instructions_text, encoding="utf-8")

    if add_private_config:
        opencode_config = repo_root.joinpath(".opencode/opencode.jsonc")

        # src/machineconfig/scripts/python/ai/solutions/opencode/opencode.py
        import machineconfig.scripts.python.ai.solutions.opencode as module
        library_config_path = Path(module.__file__).parent.joinpath("opencode.jsonc")
        # copy the library config to the repo
        opencode_config.parent.mkdir(parents=True, exist_ok=True)
        opencode_config.write_text(data=library_config_path.read_text(encoding="utf-8"), encoding="utf-8")
