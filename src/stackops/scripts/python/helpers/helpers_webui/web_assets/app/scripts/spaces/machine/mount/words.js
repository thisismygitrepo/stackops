import { plural } from "../../../words.js";

export const MOUNT_HASH = "#/machine/mount";
export const MOUNT_PATH = "utils machine mount";
export const MOUNT_TOOL = MOUNT_PATH.split(" ");

export const SYSTEM_NAMES = { Darwin: "macOS", Linux: "Linux", Windows: "Windows" };

// The three states a device can be in, in the order the list settles into: what can be mounted comes first.
export const STATES = {
  ready: { label: "Not mounted", group: "Ready to mount", tone: "accent", hue: 252 },
  mounted: { label: "Mounted", group: "Mounted", tone: "good", hue: 160 },
  blocked: { label: "Cannot be mounted", group: "Cannot be mounted here", tone: "", hue: 228 },
};
export const STATE_ORDER = Object.keys(STATES);
export const SORTS = [["state", "Ready first"], ["size", "Biggest first"], ["disk", "By disk"]];

// File systems by the names the system tools give them, lower case. One that is not here is shown as the tool wrote it.
const FILE_SYSTEMS = {
  apfs: "APFS", hfs: "Mac OS Extended", msdos: "FAT", vfat: "FAT", fat32: "FAT32", exfat: "exFAT", ntfs: "NTFS", refs: "ReFS", ext2: "ext2", ext3: "ext3", ext4: "ext4",
  btrfs: "Btrfs", xfs: "XFS", zfs: "ZFS", f2fs: "F2FS", udf: "UDF", cd9660: "CD or DVD", iso9660: "CD or DVD", swap: "Swap", bitlocker: "BitLocker, encrypted",
  crypto_luks: "LUKS, encrypted", lvm2_member: "Volume group member", linux_raid_member: "Disk array member",
};
export const fileSystemName = (device) => FILE_SYSTEMS[device.file_system.toLowerCase()] ?? device.file_system;

// lsblk writes "465.8G" where the other systems' sizes read "465.8 GB". The number is the command's own either way.
export const sizeText = (device) => device.size.replace(/^([\d.,]+)([KMGTP])$/, "$1 $2B");

const UNREADABLE = { Darwin: "macOS finds no file system on it that it can read.", Linux: "No file system was found on it.", Windows: "Windows cannot read what is on it." };
const SYSTEM_PART = { Darwin: "A startup partition (EFI). It belongs to the system and is left alone here.", Windows: "Windows keeps this part for itself. It is left alone here." };
const BLOCKS = {
  apfs_container: (device) => `Holds ${plural(device.inside, "APFS volume")}. macOS mounts those itself. If one is not mounted, Disk Utility can mount it.`,
  apfs_store: () => "The storage behind an APFS container. There is nothing on it to mount directly.",
  unreadable: (_device, system) => UNREADABLE[system],
  whole_disk: () => "A whole disk. Choose one of its parts.",
  bare_disk: () => "A disk without parts. StackOps mounts parts of a disk, and this one has none.",
  swap: () => "Swap space. The system uses it as extra memory.",
  member: () => "Belongs to a volume group or a disk array. What is inside is not listed here.",
  unlocked: () => "Already unlocked and in use. What is inside is not listed here.",
  system_part: (_device, system) => SYSTEM_PART[system],
  no_way(device) {
    const whys = device.ways.map((way) => way.why);
    if (whys.includes("not_elevated")) return "Giving it a drive letter takes administrator rights. Close StackOps, open a terminal as administrator, and start it from there.";
    if (device.encryption === "bitlocker") return "Encrypted with BitLocker. Mounting it takes dislocker or udisksctl, and neither can be used on this machine. Install one of them, then refresh.";
    if (device.encryption === "luks") return "Encrypted with LUKS. Mounting it takes udisksctl, which is not installed. Install the udisks2 package, then refresh.";
    return "Mounting takes administrator rights, and this machine has no sudo.";
  },
};
export const blockText = (device, system) => BLOCKS[device.block](device, system);

// The command's three ways of mounting. `blurb` says what the standard way is on each system.
export const WAYS = {
  mount: { title: "The standard way", blurb: { Darwin: "macOS mounts it itself.", Linux: "The system's own mount command, run as administrator.", Windows: "Windows gives the part a drive letter." } },
  dislocker: { title: "dislocker", blurb: "Opens BitLocker devices. Runs as administrator." },
  udisksctl: { title: "udisksctl", blurb: "Unlocks an encrypted device and mounts it where the system chooses. Needs no administrator." },
};
export const wayBlurb = (backend, system) => (backend === "mount" ? WAYS.mount.blurb[system] : WAYS[backend].blurb);
export const WAY_BLOCKS = {
  other_system: () => "Only on Linux.",
  not_installed: (backend) => `${backend} is not installed on this machine.`,
  not_encrypted: () => "Only for encrypted devices.",
  not_bitlocker: () => "Only for BitLocker devices.",
  encrypted: () => "This device is encrypted, so the standard way cannot open it.",
  not_elevated: () => "StackOps has to be started as administrator.",
  no_sudo: () => "Takes administrator rights, and this machine has no sudo.",
};

// What the person is told before mounting: what the Activity panel will ask for, or that it asks for nothing. `lock` marks a line about a prompt.
export function asksLine({ asks, withKey, system, elevated }) {
  const admin = asks.includes("admin");
  if (asks.includes("device")) {
    if (asks.includes("account")) return { lock: true, text: "The Activity panel opens and asks for the device's password. It may ask for your account password too." };
    return { lock: true, text: admin ? "The Activity panel opens and asks how to unlock the device, then for your administrator password." : "The Activity panel opens and asks how to unlock the device." };
  }
  if (admin) return { lock: true, text: "Takes administrator rights. The Activity panel opens and asks for your password." };
  if (withKey) return { lock: false, text: "The key file unlocks it, so no password is asked for." };
  if (system === "Darwin") return { lock: false, text: "macOS mounts it without asking for a password." };
  if (system === "Windows") return { lock: false, text: "Windows gives it the letter straight away." };
  return { lock: false, text: elevated ? "StackOps runs as root here, so no password is asked for." : "No password is asked for." };
}

// What a typed folder or key file turned out to be. `stops` keeps the Mount button off until another one is chosen.
export const PLACES = {
  new: { tone: "good", text: "This folder does not exist yet. It is made when you mount." },
  empty: { tone: "good", text: "This folder is empty and ready." },
  not_empty: { tone: "warn", text: "This folder is not empty. What is in it stays hidden while the device is mounted there." },
  in_use: { tone: "bad", stops: true, text: "Something is already mounted at this folder. Choose another one." },
  is_file: { tone: "bad", stops: true, text: "That is a file, or a file is in the way. Choose a folder." },
  no_access: { tone: "bad", stops: true, text: "You cannot make or use a folder there. Choose one inside your home folder." },
  key: { tone: "good", text: "Found." },
  missing: { tone: "bad", stops: true, text: "There is no file at this path." },
  is_folder: { tone: "bad", stops: true, text: "That is a folder. Choose the key file inside it." },
};

export const READ_ONLY_OFF = { Darwin: "Not available on macOS. StackOps always mounts for reading and writing here.", Windows: "Not available on Windows.", Linux: "Not available for this device." };
