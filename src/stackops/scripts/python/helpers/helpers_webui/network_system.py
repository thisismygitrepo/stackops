import subprocess


# The text a system tool printed, or None when it is missing, failed or took too long.
def read_tool(command: list[str], seconds: float) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=seconds, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None
