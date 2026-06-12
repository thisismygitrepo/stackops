from importlib.resources import files
from pathlib import Path


GENERIC_INSTRUCTIONS_PATH = "generic.instructions.md"

def get_generic_instructions_path() -> Path:
    text = files("stackops.scripts.python.ai.utils").joinpath(GENERIC_INSTRUCTIONS_PATH).read_text(encoding="utf-8")
    import platform
    if platform.system().lower() == "windows":
        text = text.replace("bash", "powershell").replace(".sh", ".ps1")
    import tempfile
    temp_path = Path(tempfile.gettempdir()).joinpath("generic_instructions.md")
    temp_path.write_text(data=text, encoding="utf-8")
    return temp_path
