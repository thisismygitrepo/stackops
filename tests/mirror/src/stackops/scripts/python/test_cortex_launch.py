from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.cortex_launch import render_cortex_prompt_command


def test_windows_cortex_prompt_is_flattened_to_single_line() -> None:
    rendered = render_cortex_prompt_command(command=["cortex", "--bypass"], prompt_file=Path("C:/tmp/p.md"), is_windows=True)
    assert "-p ((Get-Content -Raw" in rendered
    assert """-replace "`r?`n", ' ')""" in rendered
