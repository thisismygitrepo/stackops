LAUNCHCTL = "/bin/launchctl"
PLUTIL = "/usr/bin/plutil"
OSASCRIPT = "/usr/bin/osascript"
SYSTEM_EVENTS = "/System/Library/CoreServices/System Events.app"
SCRIPT_SECONDS = 10

LAUNCHD_USER_SOURCE = "launchd (user)"
LAUNCHD_SYSTEM_SOURCE = "launchd (system)"
# How the command starts every line it prints when macOS does not let it read the login items.
LOGIN_ITEMS_REFUSED = "Login items could not be inspected"

# The first word of a name written back to front, as in com.example.updater: the word after it is who made the thing.
REVERSED_DOMAIN_STARTS: frozenset[str] = frozenset({
    "com", "org", "net", "io", "co", "de", "uk", "us", "me", "app", "dev", "ch", "fr", "jp", "au", "ca", "eu", "edu", "gov", "at", "nl", "se",
    "it", "es", "cn", "tv", "ai", "sh", "xyz", "info", "tech", "cloud", "software",
})

# Makers whose name cannot be read off the start of a label by giving it a capital letter.
MAKERS_BY_LABEL_START: dict[str, str] = {
    "com.apple.": "Apple",
    "homebrew.mxcl.": "Homebrew",
    "com.github.": "GitHub",
    "com.jetbrains.": "JetBrains",
    "com.paloaltonetworks.": "Palo Alto Networks",
    "com.tinyspeck.": "Slack",
    "com.valvesoftware.": "Valve",
    "com.jamfsoftware.": "Jamf",
    "com.crowdstrike.": "CrowdStrike",
    "com.vmware.": "VMware",
    "com.nvidia.": "NVIDIA",
    "com.teamviewer.": "TeamViewer",
    "com.logi.": "Logitech",
    "com.mcafee.": "McAfee",
    "us.zoom.": "Zoom",
    "org.pqrs.": "Karabiner-Elements",
    "com.openssh.": "OpenSSH",
}

# Where a package manager keeps the programs it installs, for a program that says nothing else about who it belongs to.
MAKERS_BY_PROGRAM_START: dict[str, str] = {
    "/opt/homebrew/": "Homebrew",
    "/usr/local/Cellar/": "Homebrew",
    "/usr/local/opt/": "Homebrew",
    "/opt/local/": "MacPorts",
    "/nix/": "Nix",
}

LOCKED_MESSAGE = "It cannot be changed from here."
GONE_MESSAGE = "It is no longer in the list. It may have been removed already."
