import os
from pathlib import Path


def resolve_cortex_home(*, home_dir: Path) -> Path:
    configured_home = os.environ.get("SNOWFLAKE_HOME", "").strip()
    snowflake_home = Path(configured_home).expanduser() if configured_home else home_dir / ".snowflake"
    return snowflake_home / "cortex"
