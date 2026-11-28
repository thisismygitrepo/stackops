from pathlib import Path

LAUNCHCTL = "/bin/launchctl"
# What a startup script's entry is called, ahead of the script's own name: the unit on Linux and the file in the Startup folder on Windows.
ENTRY_PREFIX = "stackops-autostart-"
# The same on macOS, where a launch agent is named back to front.
MACOS_LABEL_PREFIX = "com.stackops.autostart."
# An account named here has its services started with the computer and kept after it signs out (lingering), so they wait for no sign-in.
LINGERING_ACCOUNTS_FOLDER = Path("/var/lib/systemd/linger")
# What a person calls each system `platform.system()` names.
SYSTEM_NAMES: dict[str, str] = {"Darwin": "macOS", "Linux": "Linux", "Windows": "Windows"}
