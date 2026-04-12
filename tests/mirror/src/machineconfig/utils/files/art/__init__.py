from __future__ import annotations

from pathlib import Path

from machineconfig.utils.files import art


def test_all_declared_art_references_exist() -> None:
    module_dir = Path(art.__file__).resolve().parent
    references = {art.FAT_CROCO_PATH_REFERENCE, art.HALFWIT_CROCO_PATH_REFERENCE, art.HAPPY_CROCO_PATH_REFERENCE, art.WATER_CROCO_PATH_REFERENCE}

    assert len(references) == 4
    for reference in references:
        assert module_dir.joinpath(reference).is_file()
