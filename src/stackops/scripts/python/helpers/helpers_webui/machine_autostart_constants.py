from pathlib import Path

from stackops.scripts.python.helpers.helpers_utils.autostart_script_constants import MACOS_LABEL_PREFIX

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
    # The scripts `utils machine autostart-add` adds, so each one is shown by the script's own name.
    MACOS_LABEL_PREFIX: "StackOps",
}

# Where a package manager keeps the programs it installs, for a program that says nothing else about who it belongs to.
MAKERS_BY_PROGRAM_START: dict[str, str] = {
    "/opt/homebrew/": "Homebrew",
    "/usr/local/Cellar/": "Homebrew",
    "/usr/local/opt/": "Homebrew",
    "/opt/local/": "MacPorts",
    "/nix/": "Nix",
}

# How the label starts, in small letters, for a launch agent of software that guards or manages the computer: endpoint protection, network
# security clients and device management. Their agents keep their padlock even where the account could switch them off.
MANAGED_LABEL_STARTS: tuple[str, ...] = (
    "com.jamf.", "com.jamfsoftware.", "com.github.macadmins.", "com.kandji.", "io.kandji.", "com.mosyle.", "com.addigy.", "com.fleetdm.",
    "com.osquery.", "com.googlecode.munki.", "com.microsoft.intune", "com.microsoft.companyportal", "com.airwatch.", "com.vmware.hub",
    "com.jumpcloud.", "com.tanium.", "com.bigfix.", "com.hexnode.", "com.manageengine.",
    "com.crowdstrike.", "com.sentinelone.", "com.paloaltonetworks.", "com.cisco.", "com.google.santa", "com.northpolesec.", "com.proofpoint.",
    "com.microsoft.wdav", "com.microsoft.dlp", "com.sophos.", "com.symantec.", "com.broadcom.", "com.mcafee.", "com.trellix.", "com.trendmicro.",
    "com.eset.", "com.kaspersky.", "com.bitdefender.", "com.carbonblack.", "com.vmware.carbonblack", "com.cylance.", "com.zscaler.",
    "com.netskope.", "com.forcepoint.", "com.fortinet.", "com.checkpoint.", "com.f5.", "net.pulsesecure.", "com.okta.", "com.duosecurity.",
    "com.beyondtrust.", "com.cyberark.", "com.qualys.", "com.rapid7.", "com.tenable.", "com.malwarebytes.", "com.citrix.devicetrust.",
    "com.elastic.endpoint", "com.huntress.", "com.absolute.",
)

# The command's own names for where it found an entry. The ones the page reads again by itself, so it can switch them: on Linux the units of
# the person's service manager and the desktop files in their autostart folder, on Windows their Run key and their Startup folder.
SYSTEMD_SOURCE = "systemd"
DESKTOP_FILE_SOURCE = "XDG autostart"
RUN_KEY_SOURCE = "HKCU Run"
STARTUP_FOLDER_SOURCE = "Startup folder (user)"
# How the command's name starts for what Windows opens at sign-in for every account.
EVERY_ACCOUNT_SOURCE_STARTS: tuple[str, ...] = ("HKLM", "Startup folder (all users)")

SYSTEMCTL_USER: tuple[str, ...] = ("systemctl", "--user")
UNIT_FACTS = "Id,Description,ActiveState,MainPID,ExecMainStatus,UnitFileState,FragmentPath,ExecStart"
# Where a unit is turned on: for the person in their own folder, for every account in the system's.
OWN_UNITS_FOLDER = Path.home() / ".config" / "systemd" / "user"
EVERY_ACCOUNT_UNITS_FOLDER = Path("/etc/systemd/user")
# systemd keeps no record of a unit that was turned off: it looks like one that was never on. The units turned off from the page are named
# here, so the page can go on showing them and turn them back on.
TURNED_OFF_UNITS_FILE = Path.home() / ".local" / "state" / "stackops" / "startup_units_turned_off.json"
DESKTOP_FILES_FOLDER = Path.home() / ".config" / "autostart"
DESKTOP_GROUP = b"[Desktop Entry]"

WINDOWS_VERSION_KEY = "Software\\Microsoft\\Windows\\CurrentVersion"
# What Task Manager writes for a startup app: the first byte says on or off, and after an off comes the moment it was turned off.
STARTUP_APPROVED_ON = bytes([2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
STARTUP_APPROVED_OFF_START = bytes([3, 0, 0, 0])
STARTUP_APPROVED_OFF_MARKS: frozenset[int] = frozenset({3, 7})
# Seconds from the start of Windows' clock, in 1601, to the start of the usual one in 1970.
WINDOWS_CLOCK_OFFSET_SECONDS = 11644473600

LOCKED_MESSAGE = "It cannot be changed from here."
GONE_MESSAGE = "It is no longer in the list. It may have been removed already."
