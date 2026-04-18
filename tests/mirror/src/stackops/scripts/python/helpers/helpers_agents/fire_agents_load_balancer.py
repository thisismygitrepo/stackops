from __future__ import annotations

from pathlib import Path

import pytest

from stackops.scripts.python.helpers.helpers_agents import fire_agents_load_balancer as module


def _install_panel_capture(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    captured: list[dict[str, object]] = []

    def fake_show_chunking_panel(
        *,
        subject: str,
        total_items: int,
        tasks_per_prompt: int,
        generated_agents: int,
        was_chunked: bool,
    ) -> None:
        captured.append(
            {
                "subject": subject,
                "total_items": total_items,
                "tasks_per_prompt": tasks_per_prompt,
                "generated_agents": generated_agents,
                "was_chunked": was_chunked,
            }
        )

    monkeypatch.setattr(module, "show_chunking_panel", fake_show_chunking_panel)
    return captured


def test_chunk_prompts_keeps_original_prompts_when_capacity_covers_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_material_path = tmp_path / "material.txt"
    prompt_material_path.write_text("""alpha
@-@

@-@
beta""", encoding="utf-8")

    captured = _install_panel_capture(monkeypatch)

    result = module.chunk_prompts(
        prompt_material_path=prompt_material_path,
        joiner="\n@-@\n",
        tasks_per_prompt=5,
    )

    assert result == ["alpha", "beta"]
    assert captured == [
        {
            "subject": "prompts",
            "total_items": 2,
            "tasks_per_prompt": 5,
            "generated_agents": 2,
            "was_chunked": False,
        }
    ]


def test_chunk_prompts_groups_non_blank_entries_by_requested_batch_size(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt_material_path = tmp_path / "material.txt"
    prompt_material_path.write_text("""alpha
@-@
beta
@-@
gamma
@-@
delta""", encoding="utf-8")

    captured = _install_panel_capture(monkeypatch)

    result = module.chunk_prompts(
        prompt_material_path=prompt_material_path,
        joiner="\n@-@\n",
        tasks_per_prompt=2,
    )

    assert result == ["alpha\n@-@\nbeta", "gamma\n@-@\ndelta"]
    assert captured == [
        {
            "subject": "prompts",
            "total_items": 4,
            "tasks_per_prompt": 2,
            "generated_agents": 2,
            "was_chunked": True,
        }
    ]
