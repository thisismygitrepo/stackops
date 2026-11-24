from typing import Final

# A size as the command prints it: a number, then nothing or the first letter of a unit, with or without a space and a closing "B".
SIZE_PATTERN: Final[str] = r"([0-9]+(?:[.,][0-9]+)?)\s*([KMGTP]?)B?"
# The place of a unit's letter is the power of 1024 it stands for.
SIZE_UNITS: Final[tuple[str, ...]] = ("", "K", "M", "G", "T", "P")

# macOS: how a whole disk is named at the start of a part's name, what `diskutil list` calls the part of a disk that stores an APFS container, and
# the parts that belong to the system.
MACOS_WHOLE_DISK_PATTERN: Final[str] = r"disk[0-9]+"
MACOS_APFS_STORE_PREFIX: Final[str] = "Apple_APFS"
MACOS_SYSTEM_CONTENTS: Final[frozenset[str]] = frozenset({"EFI"})

# Linux: what `lsblk` reports for swap in use, for an encrypted part, and for parts that only make sense as a member of a group or an array.
LINUX_SWAP_MOUNT: Final[str] = "[SWAP]"
LINUX_SWAP_FILE_SYSTEM: Final[str] = "swap"
LINUX_LUKS_FILE_SYSTEM: Final[str] = "crypto_LUKS"
# The kind `lsblk` gives the opened content of an unlocked part, and the columns that say which part it belongs to and where it is mounted.
LINUX_UNLOCKED_KIND: Final[str] = "crypt"
LINUX_UNLOCKED_COLUMNS: Final[str] = "NAME,TYPE,MOUNTPOINT,PKNAME"
LINUX_MEMBER_FILE_SYSTEMS: Final[frozenset[str]] = frozenset({"LVM2_member", "linux_raid_member", "zfs_member", "bcache", "ddf_raid_member", "isw_raid_member"})
# The command itself looks for this word in the file system's name to tell a BitLocker part.
BITLOCKER_MARK: Final[str] = "bitlocker"

# Windows: the kinds of part it keeps for itself, the kind it cannot read, and the letters a part can be given.
WINDOWS_SYSTEM_PART_TYPES: Final[frozenset[str]] = frozenset({"System", "Reserved", "Recovery"})
WINDOWS_UNREADABLE_PART_TYPE: Final[str] = "Unknown"
WINDOWS_DRIVE_LETTERS: Final[str] = "DEFGHIJKLMNOPQRSTUVWXYZ"
