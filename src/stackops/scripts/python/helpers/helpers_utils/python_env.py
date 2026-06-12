from pathlib import Path


def find_virtualenv_root(init_path: Path) -> Path | None:
    search_root = init_path if init_path.is_dir() else init_path.parent
    for directory in (search_root, *search_root.parents):
        virtualenv_root = directory.joinpath(".venv")
        if virtualenv_root.is_dir():
            resolved_path = virtualenv_root.resolve()
            print(f"🔮 Using virtual environment found @ {resolved_path}")
            return resolved_path
    print("🔍 No project virtual environment found.")
    return None


def build_virtualenv_activation_line(virtualenv_root: str | Path) -> str:
    import platform

    virtualenv_path = Path(virtualenv_root).expanduser()
    match platform.system():
        case "Windows":
            relative_path = virtualenv_path.relative_to(Path.home()).as_posix()
            return f". $HOME/{relative_path}/Scripts/activate.ps1"
        case "Linux" | "Darwin":
            return f". {virtualenv_path}/bin/activate"
        case platform_name:
            raise NotImplementedError(f"Platform {platform_name} not supported.")
