from __future__ import annotations

from machineconfig.scripts.python.ai.solutions.copilot.instructions import python as copilot_python_instructions
from machineconfig.utils.path_reference import get_path_reference_path


def test_path_references_resolve_to_existing_instruction_assets() -> None:
    dev_instructions_path = get_path_reference_path(
        module=copilot_python_instructions,
        path_reference=copilot_python_instructions.DEV_INSTRUCTIONS_PATH_REFERENCE,
    )
    watch_exec_prompt_path = get_path_reference_path(
        module=copilot_python_instructions,
        path_reference=copilot_python_instructions.WATCH_EXEC_PROMPT_PATH_REFERENCE,
    )

    assert dev_instructions_path.name == "dev.instructions.md"
    assert dev_instructions_path.is_file()
    assert dev_instructions_path.read_text(encoding="utf-8") != ""
    assert watch_exec_prompt_path.name == "watch_exec.prompt.md"
    assert watch_exec_prompt_path.is_file()
    assert watch_exec_prompt_path.read_text(encoding="utf-8") != ""
