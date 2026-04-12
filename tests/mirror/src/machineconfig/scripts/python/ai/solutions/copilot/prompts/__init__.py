from __future__ import annotations

from machineconfig.scripts.python.ai.solutions.copilot import prompts as copilot_prompts
from machineconfig.utils.path_reference import get_path_reference_path


def test_path_references_resolve_to_existing_prompt_assets() -> None:
    pyright_fix_path = get_path_reference_path(module=copilot_prompts, path_reference=copilot_prompts.PYRIGHT_FIX_PATH_REFERENCE)
    research_report_path = get_path_reference_path(
        module=copilot_prompts, path_reference=copilot_prompts.RESEARCH_REPORT_SKELETON_PROMPT_PATH_REFERENCE
    )

    assert pyright_fix_path.name == "pyright_fix.md"
    assert pyright_fix_path.is_file()
    assert pyright_fix_path.read_text(encoding="utf-8") != ""
    assert research_report_path.name == "research-report-skeleton.prompt.md"
    assert research_report_path.is_file()
    assert research_report_path.read_text(encoding="utf-8") != ""
