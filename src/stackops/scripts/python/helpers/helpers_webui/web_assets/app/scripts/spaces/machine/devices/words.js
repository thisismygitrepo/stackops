import { sizeText } from "../../../disk_cleanup_words.js";
import { plural } from "../../../words.js";

export const DEVICES_HASH = "#/machine/devices";
export const LIST_COMMAND = "utils machine list-devices";
export const MOUNT_COMMAND = "utils machine mount";

export const PLACES = {
  internal: { label: "Internal", name: "Internal disk", glyph: "database", hue: 252 },
  external: { label: "External", name: "External disk", glyph: "plug", hue: 28 },
  image: { label: "Disk images", name: "Disk image", glyph: "cube", hue: 190 },
  network: { label: "Network", name: "Network shares", glyph: "globe", hue: 150 },
};
export const PLACE_ORDER = Object.keys(PLACES);
export const STATES = [["all", "All"], ["mounted", "Mounted"], ["unmounted", "Not mounted"]];
export const ORDERS = [["disk", "By disk"], ["full", "Fullest first"], ["data", "Most data first"], ["name", "By name"]];
export const RANKED_TITLES = { full: "Every volume, fullest first", data: "Every volume, most data first", name: "Every volume, by name" };

// Formats by the name the system gives them: what to call each, and which systems open it.
const FORMATS = {
  apfs: ["APFS", "Apple's format. Windows and Linux need extra software to open it."],
  hfs: ["Mac OS Extended", "The older Mac format. Windows and Linux need extra software to open it."],
  exfat: ["exFAT", "Opens on Mac, Windows and Linux, so it suits a disk that moves between them."],
  msdos: ["FAT", "Opens on nearly everything. One file cannot be larger than 4 GB."],
  vfat: ["FAT", "Opens on nearly everything. One file cannot be larger than 4 GB."],
  fat32: ["FAT32", "Opens on nearly everything. One file cannot be larger than 4 GB."],
  ntfs: ["NTFS", "The Windows format. A Mac reads it but cannot write to it. Linux does both."],
  ext4: ["ext4", "A Linux format. Mac and Windows need extra software to open it."],
  ext3: ["ext3", "A Linux format. Mac and Windows need extra software to open it."],
  ext2: ["ext2", "A Linux format. Mac and Windows need extra software to open it."],
  btrfs: ["Btrfs", "A Linux format. Mac and Windows need extra software to open it."],
  xfs: ["XFS", "A Linux format. Mac and Windows need extra software to open it."],
  zfs: ["ZFS", "Needs ZFS software on whichever system opens it."],
  udf: ["UDF", "The format of DVDs and some large USB disks."],
  cd9660: ["CD format", "The format of CDs and disc images. It cannot be written to."],
  iso9660: ["CD format", "The format of CDs and disc images. It cannot be written to."],
  swap: ["Swap", "Space the system uses as extra memory. It holds no files."],
  crypto_luks: ["LUKS", "Encrypted by Linux. Its content shows once it is unlocked."],
  bitlocker: ["BitLocker", "Encrypted by Windows. Its content shows once it is unlocked."],
  smbfs: ["SMB share", "A folder another computer shares the Windows way."],
  cifs: ["SMB share", "A folder another computer shares the Windows way."],
  smb3: ["SMB share", "A folder another computer shares the Windows way."],
  nfs: ["NFS share", "A folder another computer shares the Unix way."],
  nfs4: ["NFS share", "A folder another computer shares the Unix way."],
  afpfs: ["AFP share", "A folder another Mac shares the old Apple way."],
  webdav: ["WebDAV", "A folder on a web server."],
  davfs: ["WebDAV", "A folder on a web server."],
  sshfs: ["SSH folder", "A folder on another computer, reached over SSH."],
  "fuse.sshfs": ["SSH folder", "A folder on another computer, reached over SSH."],
  "fuse.rclone": ["Cloud storage", "Cloud storage that rclone mounted as a folder."],
  macfuse: ["Mounted by a program", "A program on this computer presents it as a folder."],
  osxfuse: ["Mounted by a program", "A program on this computer presents it as a folder."],
  virtiofs: ["Shared from the host", "A folder the computer running this virtual machine shares with it."],
  vboxsf: ["Shared from the host", "A folder the computer running this virtual machine shares with it."],
  "9p": ["Shared from the host", "A folder the computer running this virtual machine shares with it."],
  unknown: ["Format not known yet", "Windows names the format of a volume once it has a drive letter."],
};
const UNREADABLE = ["No readable format", "This computer cannot read what is on it. It may be blank, or made by another system."];
export const formatOf = (volume) => (volume.file_system === "" ? UNREADABLE : (FORMATS[volume.file_system] ?? [volume.file_system.toUpperCase(), ""]));

const ROLES = {
  system: ["The system", "The operating system itself."],
  data: ["Your files", "Your files, apps and settings."],
  startup: ["Start-up files", "What the computer needs to start."],
  recovery: ["Recovery", "A small system for repairing or reinstalling this one."],
  swap: ["Extra memory", "Space the system uses when the memory is full."],
  update: ["Updates", "Working room for system updates."],
  firmware: ["Hardware data", "Settings and keys the hardware keeps for itself."],
  backup: ["Backups", "Backups of this or another computer."],
  reserved: ["Reserved", "Set aside by the system."],
};
export const roleOf = (volume) => ROLES[volume.role] ?? ["", ""];

const CONNECTIONS = { usb: "USB", sata: "SATA", nvme: "NVMe", ata: "ATA", sas: "SAS", scsi: "SCSI", mmc: "SD card", "Secure Digital": "SD card", "Disk Image": "", "Apple Fabric": "" };
export const connectionOf = (disk) => CONNECTIONS[disk.connection] ?? disk.connection;

export const size = (bytes) => sizeText(bytes);
export const volumeName = (volume) => volume.name || "No name";
export const diskName = (disk) => disk.name || (/^disk \d+$/i.test(disk.id) ? disk.id : PLACES[disk.place].name);
export const share = (part, whole) => (whole > 0 ? `${part / whole < 0.01 && part > 0 ? "under 1" : Math.round((part / whole) * 100)}%` : "");

export function whyNoMount(volume, platform) {
  if (volume.locked) return platform === "macOS" ? "Locked. Unlock it with its password in Finder or Disk Utility first." : "Locked. Unlock it with its password first.";
  if (volume.file_system === "") return "This computer cannot read its format, so it cannot be mounted.";
  return "The mount tool cannot handle this kind of volume. It can still be mounted from a terminal.";
}

export function spaceSentence(volume, sharing) {
  if (volume.used === null || volume.free === null) return `${size(volume.size)} in all. How full it is shows once it is mounted.`;
  const own = `${size(volume.used)} used and ${size(volume.free)} free of ${size(volume.size)}.`;
  return sharing > 0 ? `${own} ${sharing === 1 ? "One other volume draws" : `${sharing} other volumes draw`} on the same free space.` : own;
}

export const partsLine = (count, bytes) => `${plural(count, "system part")} · ${size(bytes)}`;
