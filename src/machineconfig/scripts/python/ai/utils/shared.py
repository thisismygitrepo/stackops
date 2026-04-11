from pathlib import Path
import machineconfig.scripts.python.ai.solutions.copilot.instructions.python as copilot_instructions

from machineconfig.scripts.python.ai.solutions.copilot.instructions.python import DEV_INSTRUCTIONS_PATH_REFERENCE
from machineconfig.utils.path_reference import get_path_reference_path

def get_generic_instructions_path() -> Path:
    path = get_path_reference_path(module=copilot_instructions, path_reference=DEV_INSTRUCTIONS_PATH_REFERENCE)
    text = path.read_text(encoding="utf-8")
    import platform
    if platform.system().lower() == "windows":
        text = text.replace("bash", "powershell").replace(".sh", ".ps1")
    import tempfile
    temp_path = Path(tempfile.gettempdir()).joinpath("generic_instructions.md")
    temp_path.write_text(data=text, encoding="utf-8")
    return temp_path
