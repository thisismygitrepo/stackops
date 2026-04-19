

from importlib.resources import files

import stackops.settings.lf.linux.autocall as subject


def test_path_references_resolve_to_existing_resources() -> None:
    package_root = files(subject)
    missing_references = tuple(
        reference
        for reference in (
            subject.DELETE_PATH_REFERENCE,
            subject.ON_CD_PATH_REFERENCE,
            subject.ON_QUIT_PATH_REFERENCE,
            subject.OPEN_PATH_REFERENCE,
            subject.PASTE_PATH_REFERENCE,
            subject.PRE_CD_PATH_REFERENCE,
            subject.RENAME_PATH_REFERENCE,
        )
        if not package_root.joinpath(reference).is_file()
    )
    assert missing_references == (), missing_references
