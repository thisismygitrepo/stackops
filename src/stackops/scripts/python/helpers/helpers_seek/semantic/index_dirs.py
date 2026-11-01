from pathlib import Path

from stackops.scripts.python.helpers.helpers_seek.semantic.constants import INDEX_DIR_GITIGNORE_CONTENT


def keep_index_dir_out_of_git(index_dir: Path) -> None:
    gitignore = index_dir / ".gitignore"
    if index_dir.is_dir() and not gitignore.exists():
        gitignore.write_text(INDEX_DIR_GITIGNORE_CONTENT, encoding="utf-8")
