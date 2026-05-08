from pathlib import Path

import pytest
import yaml

from stackops.scripts.python.helpers.helpers_agents import agents_run_context
from stackops.utils.options_utils import tv_options


def testbuild_named_prompt_selection_maps_uses_compact_labels_and_source_yaml() -> None:
    locations = [
        ("repo", Path("/tmp/repo/.stackops/prompts.yaml")),
        ("private", Path("/tmp/private/prompts.yaml")),
    ]

    original_resolve_named_candidates = agents_run_context.collect_named_yaml_candidates

    def fakecollect_named_yaml_candidates(raw_data: object, prefix: str = "") -> dict[str, str]:
        if raw_data == "repo-data":
            return {"shared.backend": "repo preview", "repo_only": "repo only preview"}
        if raw_data == "private-data":
            return {"shared.backend": "private preview", "private_only": "private only preview"}
        return original_resolve_named_candidates(raw_data, prefix)

    def fake_read_yaml(path: Path) -> object:
        if "repo/.stackops" in str(path):
            return "repo-data"
        return "private-data"

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(agents_run_context, "collect_named_yaml_candidates", fakecollect_named_yaml_candidates)
    monkeypatch.setattr("stackops.utils.files.read.read_yaml", fake_read_yaml)
    try:
        preview_map, value_map = agents_run_context.build_named_prompt_selection_maps(existing_yaml_locations=locations)
    finally:
        monkeypatch.undo()

    assert "repo_only" in preview_map
    assert "private_only" in preview_map
    assert "shared.backend@repo" in preview_map
    assert "shared.backend@private" in preview_map
    assert "source_yaml: /tmp/repo/.stackops/prompts.yaml" in preview_map["shared.backend@repo"]
    assert value_map["shared.backend@repo"] == "repo preview"


def test_resolve_context_picker_shows_source_yaml_and_uses_wide_preview(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_yaml = tmp_path / ".stackops" / "prompts.yaml"
    private_yaml = tmp_path / "private" / "prompts.yaml"
    repo_yaml.parent.mkdir(parents=True, exist_ok=True)
    private_yaml.parent.mkdir(parents=True, exist_ok=True)
    repo_yaml.write_text("backend: repo prompt\n", encoding="utf-8")
    private_yaml.write_text("frontend: private prompt\n", encoding="utf-8")

    captured_options: dict[str, str] = {}
    captured_preview_size_percent: float | None = None

    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float
    ) -> str:
        nonlocal captured_preview_size_percent
        assert extension == "yaml"
        assert multi is False
        captured_options.update(options_to_preview_mapping)
        captured_preview_size_percent = preview_size_percent
        return "backend"

    monkeypatch.setattr(
        agents_run_context,
        "resolve_prompts_yaml_paths",
        lambda prompts_yaml_path, where: [("repo", repo_yaml), ("private", private_yaml)],
    )
    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    selected = agents_run_context.resolve_context(
        context=None,
        context_path=None,
        prompts_yaml_path=None,
        context_name=None,
        where="all",
    )

    assert selected == "repo prompt"
    assert captured_preview_size_percent == agents_run_context.PROMPTS_PREVIEW_SIZE_PERCENT
    assert "source_yaml: " in captured_options["backend"]
    assert str(repo_yaml) in captured_options["backend"]


def test_resolve_named_prompts_yaml_entry_fuzzy_picker_shows_source_yaml(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    repo_yaml = tmp_path / ".stackops" / "prompts.yaml"
    private_yaml = tmp_path / "private" / "prompts.yaml"
    repo_yaml.parent.mkdir(parents=True, exist_ok=True)
    private_yaml.parent.mkdir(parents=True, exist_ok=True)
    repo_yaml.write_text("backend: repo prompt\n", encoding="utf-8")
    private_yaml.write_text("backend: private prompt\n", encoding="utf-8")

    captured_options: dict[str, str] = {}

    def fake_choose_from_dict_with_preview(
        options_to_preview_mapping: dict[str, str], extension: str | None, multi: bool, preview_size_percent: float
    ) -> str:
        assert extension == "yaml"
        assert multi is False
        assert preview_size_percent == agents_run_context.PROMPTS_PREVIEW_SIZE_PERCENT
        captured_options.update(options_to_preview_mapping)
        return "backend@repo"

    monkeypatch.setattr(
        agents_run_context,
        "resolve_prompts_yaml_paths",
        lambda prompts_yaml_path, where: [("repo", repo_yaml), ("private", private_yaml)],
    )
    monkeypatch.setattr(tv_options, "choose_from_dict_with_preview", fake_choose_from_dict_with_preview)

    selected = agents_run_context.resolve_named_prompts_yaml_entry(
        prompts_yaml_path=None,
        entry_name="missing",
        where="all",
        entry_label="Context name",
    )

    assert selected == "repo prompt"
    assert "source_yaml: " in captured_options["backend@repo"]
    assert str(repo_yaml) in captured_options["backend@repo"]


def test_ensure_prompts_yaml_exists_creates_single_entry_example(tmp_path: Path) -> None:
    yaml_path = tmp_path / ".stackops" / "prompts.yaml"

    created = agents_run_context.ensure_prompts_yaml_exists(yaml_path=yaml_path)

    assert created is True
    yaml_text = yaml_path.read_text(encoding="utf-8")
    assert yaml_text.startswith("# yaml-language-server: $schema=./prompts.schema.json\n")
    assert "entryExample: {prompt: replace me, description: short label}\n" in yaml_text
    assert "default: |\n" not in yaml_text
    assert "team:\n" not in yaml_text
    loaded_yaml = yaml.safe_load(yaml_text)
    assert isinstance(loaded_yaml, dict)
    assert loaded_yaml["entryExample"]["prompt"] == "replace me"
    assert loaded_yaml["entryExample"]["description"] == "short label"
