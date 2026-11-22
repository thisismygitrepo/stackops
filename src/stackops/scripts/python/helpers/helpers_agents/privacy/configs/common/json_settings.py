import json
from pathlib import Path
import sys
from typing import cast


def read_privacy_settings(path: Path) -> dict[str, object] | None:
    try:
        settings: object = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError, RecursionError):
        print(f"""Skipping privacy settings at {path} because the JSON could not be read.""", file=sys.stderr)
        return None
    if not isinstance(settings, dict):
        print(f"""Skipping privacy settings at {path} because a JSON object was expected.""", file=sys.stderr)
        return None
    return cast(dict[str, object], settings)
