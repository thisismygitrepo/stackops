import os
from pathlib import Path


def resolve_prime_agent_directory(*, home_dir: Path) -> Path:
    configured = os.environ.get("PRIME_AGENT_CODING_AGENT_DIR", "").strip()
    return Path(configured).expanduser() if configured else home_dir / ".prime/agent"
