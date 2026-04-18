from __future__ import annotations

from pathlib import Path

from stackops.scripts.python.helpers.helpers_devops import themes


def test_theme_path_references_point_to_existing_files() -> None:
    package_dir = Path(themes.__file__).resolve().parent
    relative_paths = (
        themes.CHOOSE_PWSH_THEME_PATH_REFERENCE,
        themes.CHOOSE_STARSHIP_THEME_PS1_PATH_REFERENCE,
        themes.CHOOSE_STARSHIP_THEME_SH_PATH_REFERENCE,
        themes.CHOOSE_WINDOWS_TERMINAL_THEME_PATH_REFERENCE,
    )

    missing_paths = [relative_path for relative_path in relative_paths if not package_dir.joinpath(relative_path).is_file()]

    assert missing_paths == []
