from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Protocol, cast


SCRIPT_PATH = Path("src/machineconfig/settings/yazi/scripts/fullscreen_preview.py")


class FullscreenPreviewModule(Protocol):
    def build_command(self, target_path: Path, terminal_columns: int) -> list[str]: ...
    def resolve_target(self, arguments: tuple[str, ...]) -> Path: ...


def load_module() -> FullscreenPreviewModule:
    spec = spec_from_file_location("test_fullscreen_preview_module", SCRIPT_PATH)
    assert spec is not None
    loader = spec.loader
    assert isinstance(loader, SourceFileLoader)
    module = module_from_spec(spec)
    loader.exec_module(module)
    return cast(FullscreenPreviewModule, module)


def test_resolve_target_prefers_hovered_path(tmp_path: Path) -> None:
    module = load_module()
    hovered_path = tmp_path / "hovered.txt"
    hovered_path.write_text("hovered\n", encoding="utf-8")
    selected_path = tmp_path / "selected.txt"
    selected_path.write_text("selected\n", encoding="utf-8")

    resolved = module.resolve_target(
        ("__YAZI_HOVERED__", str(hovered_path), "__YAZI_SELECTED__", str(selected_path))
    )

    assert resolved == hovered_path.resolve()


def test_build_command_for_markdown_uses_glow_pager(tmp_path: Path) -> None:
    module = load_module()
    target_path = tmp_path / "note.md"
    target_path.write_text("# hello\n", encoding="utf-8")

    command = module.build_command(target_path=target_path, terminal_columns=88)

    assert command == ["glow", "--pager", "--width", "88", "--style", "dark", str(target_path)]


def test_build_command_for_csv_uses_rich_pager(tmp_path: Path) -> None:
    module = load_module()
    target_path = tmp_path / "table.csv"
    target_path.write_text("a,b\n1,2\n", encoding="utf-8")

    command = module.build_command(target_path=target_path, terminal_columns=91)

    assert command == [
        "uvx",
        "--from",
        "rich-cli",
        "rich",
        "--force-terminal",
        "--csv",
        "--pager",
        "--width",
        "91",
        str(target_path),
    ]


def test_build_command_for_tsv_uses_visidata(tmp_path: Path) -> None:
    module = load_module()
    target_path = tmp_path / "table.tsv"
    target_path.write_text("a\tb\n1\t2\n", encoding="utf-8")

    command = module.build_command(target_path=target_path, terminal_columns=120)

    assert command == ["uvx", "--from", "visidata", "--with", "pyarrow", "vd", str(target_path)]
