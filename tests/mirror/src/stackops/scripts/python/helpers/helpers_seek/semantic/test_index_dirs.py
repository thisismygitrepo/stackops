from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.constants import INDEX_DIR_GITIGNORE_CONTENT
from stackops.scripts.python.helpers.helpers_seek.semantic.index_dirs import keep_index_dir_out_of_git


def test_index_dir_gets_a_self_ignoring_gitignore_and_missing_dirs_are_left_alone(tmp_path: Path) -> None:
    index_dir = tmp_path.joinpath(".ck")
    keep_index_dir_out_of_git(index_dir=index_dir)
    assert not index_dir.exists()

    index_dir.mkdir()
    keep_index_dir_out_of_git(index_dir=index_dir)
    assert index_dir.joinpath(".gitignore").read_text(encoding="utf-8") == INDEX_DIR_GITIGNORE_CONTENT


def test_an_existing_index_dir_gitignore_is_never_overwritten(tmp_path: Path) -> None:
    index_dir = tmp_path.joinpath(".qmd")
    index_dir.mkdir()
    index_dir.joinpath(".gitignore").write_text("index.sqlite\n", encoding="utf-8")

    keep_index_dir_out_of_git(index_dir=index_dir)

    assert index_dir.joinpath(".gitignore").read_text(encoding="utf-8") == "index.sqlite\n"
