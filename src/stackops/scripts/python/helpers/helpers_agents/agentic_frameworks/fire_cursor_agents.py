

from pathlib import Path
# import shlex
from stackops.scripts.python.helpers.helpers_agents.fire_agents_helper_types import AI_SPEC

def fire_cursor(ai_spec: AI_SPEC, prompt_path: Path) -> str:
    if ai_spec["machine"] == "local":
        return f"""

cursor-agent --print --output-format text {prompt_path}

"""
    return f"""

cursor-agent --print --output-format text {prompt_path}

"""
