"""Cross-platform PATH explorer backend."""

import os
import platform
from pathlib import Path
from typing import Literal


PlatformType = Literal["Windows", "Linux", "Darwin"]


def get_platform() -> PlatformType:
    """Get the current platform."""
    return platform.system()  # type: ignore[return-value]


def get_path_entries() -> list[str]:
    """Get all PATH entries for the current platform."""
    path_str = os.environ.get("PATH", "")
    separator = ";" if get_platform() == "Windows" else ":"
    return [entry for entry in path_str.split(separator) if entry.strip()]


def get_directory_contents(directory: str, max_items: int = 50) -> list[str]:
    """Get contents of a directory, limited to max_items."""
    try:
        path = Path(directory)
        if not path.exists():
            return ["⚠️  Directory does not exist"]
        if not path.is_dir():
            return ["⚠️  Not a directory"]
        
        items: list[str] = []
        for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if len(items) >= max_items:
                items.append(f"... and {sum(1 for _ in path.iterdir()) - max_items} more items")
                break
            prefix = "📁 " if item.is_dir() else "📄 "
            items.append(f"{prefix}{item.name}")
        
        if not items:
            return ["📭 Empty directory"]
        return items
    except PermissionError:
        return ["⚠️  Permission denied"]
    except Exception as e:
        return [f"⚠️  Error: {e!s}"]
