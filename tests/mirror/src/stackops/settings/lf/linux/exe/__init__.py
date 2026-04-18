from __future__ import annotations

from importlib.resources import files

import stackops.settings.lf.linux.exe as subject


def test_path_references_resolve_to_existing_resources() -> None:
    package_root = files(subject)
    missing_references = tuple(
        reference
        for reference in (
            subject.CLEANER_PATH_REFERENCE,
            subject.LEFTPANE_PREVIEWER_PATH_REFERENCE,
            subject.LFCD_PATH_REFERENCE,
            subject.PREVIEWER_PATH_REFERENCE,
            subject.PREVIEWER_ARCHIVE_PATH_REFERENCE,
        )
        if not package_root.joinpath(reference).is_file()
    )
    assert missing_references == (), missing_references
