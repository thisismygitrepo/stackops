
from typing import Literal, TypeAlias
from pathlib import Path


SCRIPT_SOURCE: TypeAlias = Literal["all", "a", "project", "p", "user", "u", "library", "l", "dynamic", "d"]


def list_available_scripts(source: SCRIPT_SOURCE) -> None:
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
                files = [f for f in loc_path.rglob("*") if f.is_file() and f.suffix in (".py", ".sh", ".ps1", ".bat", ".cmd", "")]
                if files:
                    relative_files = [str(f.relative_to(loc_path)) for f in files]
                    _print_files_by_type(relative_files)
                else:
                    print("  (empty)")
            else:
                print("  ⚠️  Directory does not exist")
        else:
            api_url = "https://api.github.com/repos/thisismygitrepo/stackops/contents/src/stackops/jobs/scripts_dynamic"
            try:
                import requests
                response = requests.get(api_url, timeout=10)
                if response.status_code == 200:
                    items = response.json()
                    files = [item["name"] for item in items if item["type"] == "file"]
                    _print_files_by_type(files)
                else:
                    print(f"  ⚠️  Could not fetch from GitHub (status: {response.status_code})")
            except Exception as e:
                print(f"  ⚠️  Could not fetch from GitHub: {e}")
