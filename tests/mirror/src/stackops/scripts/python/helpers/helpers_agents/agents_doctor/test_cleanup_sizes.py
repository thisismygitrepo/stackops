import os
from pathlib import Path

from stackops.scripts.python.helpers.helpers_agents.agents_doctor.cleanup_sizes import measure_tree


def test_measure_tree_counts_hard_links_once_and_never_follows_symlinks(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "big.bin").write_bytes(b"x" * 1000)
    directory = tmp_path / ".ai"
    (directory / "venv").mkdir(parents=True)
    first = directory / "a.txt"
    first.write_bytes(b"hello")
    os.link(first, directory / "venv" / "b.txt")
    link = directory / "outside-link"
    link.symlink_to(outside, target_is_directory=True)
    assert measure_tree(path=directory) == (2, 5 + link.lstat().st_size)
