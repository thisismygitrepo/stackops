from pathlib import Path

import pytest
import yaml

from stackops.utils.schemas.layouts.layout_constants import LAYOUT_SCHEMA_URL
from stackops.utils.schemas.layouts.layout_file import read_layouts_file, write_layouts_file
from stackops.utils.schemas.layouts.layout_types import LayoutsFile, TabConfig, single_pane_tab


def _write_layout_yaml(tmp_path: Path, tab: dict[str, object]) -> Path:
    layout_path = tmp_path / "layout.yaml"
    layout_path.write_text(yaml.safe_dump({"version": "0.1", "layouts": [{"layoutName": "demo", "layoutTabs": [tab]}]}), encoding="utf-8")
    return layout_path


def _pane(name: str) -> dict[str, str]:
    return {"paneName": name, "startDir": "/work", "command": "echo hi"}


def test_valid_multi_pane_tab_is_loaded(tmp_path: Path) -> None:
    layout_path = _write_layout_yaml(tmp_path, {"tabName": "dev", "arrangement": "rows", "panes": [_pane("a"), _pane("b")]})
    layouts = read_layouts_file(path=layout_path)["layouts"]
    assert [pane["paneName"] for pane in layouts[0]["layoutTabs"][0]["panes"]] == ["a", "b"]


@pytest.mark.parametrize(
    ("tab", "message"),
    [
        ({"tabName": "dev", "startDir": "/work", "command": "ls"}, "'panes' must be a non-empty list"),
        ({"tabName": "dev", "panes": []}, "'panes' must be a non-empty list"),
        ({"tabName": "dev", "panes": [{"paneName": "a", "startDir": "/work"}]}, "'command' must be a string"),
        ({"tabName": "dev", "panes": [_pane("a"), _pane("a")]}, "duplicate paneName"),
        ({"tabName": "dev", "arrangement": "diagonal", "panes": [_pane("a")]}, "'arrangement' must be one of"),
    ],
)
def test_invalid_tabs_are_rejected(tmp_path: Path, tab: dict[str, object], message: str) -> None:
    layout_path = _write_layout_yaml(tmp_path, tab)
    with pytest.raises(ValueError, match=message):
        read_layouts_file(path=layout_path)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("version: 0.1\nlayouts: []\n", "'version' must be a quoted string"),
        (
            'version: "0.1"\nlayouts:\n  - layoutName: demo\n    layoutTabs:\n      - tabName: dev\n        panes:\n          - {paneName: a, startDir: ~, command: ls}\n',
            "'startDir' must be a string, got None",
        ),
        ('version: "0.1"\nlayouts: [\n', "Invalid YAML in layout file"),
    ],
)
def test_yaml_typing_traps_are_rejected(tmp_path: Path, document: str, message: str) -> None:
    layout_path = tmp_path / "layout.yaml"
    layout_path.write_text(document, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        read_layouts_file(path=layout_path)


@pytest.mark.parametrize("file_name", ("layout.json", "layout.yml"))
def test_non_yaml_suffix_is_rejected(tmp_path: Path, file_name: str) -> None:
    layout_path = tmp_path / file_name
    layout_path.write_text('{"version": "0.1", "layouts": []}', encoding="utf-8")
    with pytest.raises(ValueError, match="must be YAML with the '.yaml' suffix"):
        read_layouts_file(path=layout_path)
    with pytest.raises(ValueError, match="must be YAML with the '.yaml' suffix"):
        write_layouts_file(path=layout_path, layouts_file={"version": "0.1", "layouts": []})


def test_written_layout_round_trips_without_aliases(tmp_path: Path) -> None:
    command = """bunx -y supergateway --stdio "claude mcp serve" --port 12010 # not: a comment"""
    shared_tab: TabConfig = single_pane_tab(tab_name="brain", start_dir="~", command=command)
    layouts_file: LayoutsFile = {"version": "0.1", "layouts": [{"layoutName": "one", "layoutTabs": [shared_tab, shared_tab]}]}
    layout_path = tmp_path / "nested" / "layout.yaml"

    write_layouts_file(path=layout_path, layouts_file=layouts_file)

    written_text = layout_path.read_text(encoding="utf-8")
    assert written_text.startswith(f"# yaml-language-server: $schema={LAYOUT_SCHEMA_URL}\n")
    assert "&id" not in written_text
    assert read_layouts_file(path=layout_path) == layouts_file
