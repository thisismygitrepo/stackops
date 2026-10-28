
from typing import Literal, TypeAlias
from pathlib import Path


SCRIPT_SOURCE: TypeAlias = Literal["all", "a", "workspace", "w", "user", "u", "library", "l", "dynamic", "d"]


def list_available_scripts(source: SCRIPT_SOURCE) -> None:
    from stackops.scripts.python.helpers.helpers_devops.script_discovery import SCRIPT_SUFFIXES, is_supported_script_path, list_dynamic_script_names
    from stackops.scripts.python.helpers.helpers_devops.script_sources import get_script_locations

    locations = get_script_locations(source=source)
    def _print_files_by_type(files: list[str] | list[Path]) -> None:
        categories: dict[str, list[str]] = {".py": [], ".sh": [], ".ps1": [], ".cmd": [], ".bat": [], "other": []}
        for f in files:
            ext = Path(f).suffix.lower() if "." in str(f) else ""
            if ext in categories: categories[ext].append(str(f))
            else: categories["other"].append(str(f))
        for ext, cat_files in categories.items():
            if cat_files:
                label = ext if ext else "other"
                print(f"    [{label}]")
                for cf in sorted(cat_files): print(f"      • {cf}")

    for loc_name, loc_path in locations.items():
        print(f"\n📁 {loc_name.upper()} ({loc_path}):")
        print("-" * 60)
        if isinstance(loc_path, Path):
            if loc_path.is_dir():
                files = [
                    file_path
                    for file_path in loc_path.rglob("*")
                    if file_path.is_file()
                    and is_supported_script_path(relative_path=file_path.relative_to(loc_path), supported_suffixes=SCRIPT_SUFFIXES)
                ]
                if files:
                    relative_files = [str(f.relative_to(loc_path)) for f in files]
                    _print_files_by_type(relative_files)
                else:
                    print("  (empty)")
            else:
                print("  ⚠️  Directory does not exist")
        else:
            try:
                _print_files_by_type(list_dynamic_script_names())
            except Exception as e:
                print(f"  ⚠️  Could not fetch from GitHub: {e}")
