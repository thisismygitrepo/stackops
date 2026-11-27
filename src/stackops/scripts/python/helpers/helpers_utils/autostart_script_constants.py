LAUNCHCTL = "/bin/launchctl"
# What a startup script's entry is called, ahead of the script's own name: the unit on Linux and the file in the Startup folder on Windows.
ENTRY_PREFIX = "stackops-autostart-"
# The same on macOS, where a launch agent is named back to front.
MACOS_LABEL_PREFIX = "com.stackops.autostart."
