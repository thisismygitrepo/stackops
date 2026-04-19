

from pathlib import Path
from typing import cast

import pytest

from stackops.profile import dotfiles_mapper as dotfiles_mapper_module


def test_library_mapper_file_exists_and_loads_nonempty_document() -> None:
    mapper_document = dotfiles_mapper_module.load_dotfiles_mapper(dotfiles_mapper_module.LIBRARY_MAPPER_PATH)

    assert dotfiles_mapper_module.LIBRARY_MAPPER_PATH.is_file()
    assert len(mapper_document) > 0


def test_normalize_os_filter_sorts_tokens_into_canonical_order() -> None:
    os_filter = dotfiles_mapper_module.normalize_os_filter("windows, linux")

    assert os_filter == ["linux", "windows"]


def test_load_dotfiles_mapper_rejects_duplicate_os_values(tmp_path: Path) -> None:
    mapper_path = tmp_path / "mapper.yaml"
    mapper_path.write_text(
        """
git:
  config:
    original: /tmp/gitconfig
    self_managed: CONFIG_ROOT/git/config
    os:
      - linux
      - linux
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate OS value"):
        dotfiles_mapper_module.load_dotfiles_mapper(mapper_path)


def test_write_dotfiles_mapper_round_trips_header_and_data(tmp_path: Path) -> None:
    mapper_path = tmp_path / "mapper.yaml"
    mapper_document = cast(
        dotfiles_mapper_module.MapperDocument,
        {"git": {"config": {"original": "/tmp/gitconfig", "self_managed": "CONFIG_ROOT/git/config", "os": ["linux", "darwin"]}}},
    )

    dotfiles_mapper_module.write_dotfiles_mapper(
        path=mapper_path, mapper=mapper_document, header=dotfiles_mapper_module.DEFAULT_DOTFILE_MAPPER_HEADER
    )

    written_text = mapper_path.read_text(encoding="utf-8")

    assert written_text.startswith(dotfiles_mapper_module.DEFAULT_DOTFILE_MAPPER_HEADER)
    assert dotfiles_mapper_module.load_dotfiles_mapper(mapper_path) == mapper_document
