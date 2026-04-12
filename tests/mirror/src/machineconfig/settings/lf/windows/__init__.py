from __future__ import annotations

from importlib.resources import files

import machineconfig.settings.lf.windows as subject


def test_path_references_resolve_to_existing_resources() -> None:
    package_root = files(subject)
    missing_references = tuple(
        reference
        for reference in (
            subject.CD_TERE_PATH_REFERENCE,
            subject.CD_ZOXIDE_PATH_REFERENCE,
            subject.CD_ZOXIDE2_PATH_REFERENCE,
            subject.COLORS_PATH_REFERENCE,
            subject.ICONS_PATH_REFERENCE,
            subject.LEFTPANE_PREVIEWER_PATH_REFERENCE,
            subject.LFCD_PATH_REFERENCE,
            subject.LFRC_PATH_REFERENCE,
            subject.MKDIR_PATH_REFERENCE,
            subject.MKFILE_PATH_REFERENCE,
            subject.PREVIEWER_PATH_REFERENCE,
        )
        if not package_root.joinpath(reference).is_file()
    )
    assert missing_references == (), missing_references
