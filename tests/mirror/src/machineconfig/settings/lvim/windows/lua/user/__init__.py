from __future__ import annotations

from importlib.resources import files

import machineconfig.settings.lvim.windows.lua.user as subject


def test_path_references_resolve_to_existing_resources() -> None:
    package_root = files(subject)
    missing_references = tuple(
        reference
        for reference in (subject.CUSTOM_CONFIG_PATH_REFERENCE,)
        if not package_root.joinpath(reference).is_file()
    )
    assert missing_references == (), missing_references
