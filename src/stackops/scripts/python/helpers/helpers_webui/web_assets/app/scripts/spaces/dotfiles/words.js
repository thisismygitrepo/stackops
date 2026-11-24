export const DOTFILES_HASH = "#/dotfiles";
export const EXPORT_HASH = "#/dotfiles/export";
export const IMPORT_HASH = "#/dotfiles/import";
export const EXPORT_PATH = "devops config dotfiles export";
export const IMPORT_PATH = "devops config dotfiles import";
export const REGISTER_PATH = "devops config dotfiles register";
export const SYNC_PATH = "devops config dotfiles sync";
export const COLLECT_PATH = "devops config dotfiles collect";
export const INSTALL_PATH = "devops software install";
// What each command prints when it asks for the archive's password. The page types the password into that prompt for the person (kit.js).
export const EXPORT_PROMPT = "Password for zip encryption";
export const IMPORT_PROMPT = "Password for zip decryption";
// The command that puts every file of a brought-in folder in its place, as the export command itself prints it for the other machine.
export const APPLY_COMMAND = "devops config dotfiles sync down --source user --method symlink --which all";
export const APPLY_PRESET = { direction: "down", source: "user", which: "all" };

export const LEFT_OUT = {
  broken_link: { one: "link that points at nothing", many: "links that point at nothing", why: "There is no file behind it to pack." },
  linked_folder: { one: "linked folder", many: "linked folders", why: "It goes in as an empty folder. What it points to stays behind." },
  special_file: { one: "special file", many: "special files", why: "Sockets and pipes cannot be packed." },
};

// An SSH configuration can name a thousand machines. The box offers this many at a time, and typing narrows them down.
const HOSTS_OFFERED = 40;
export const hostOptions = (hosts, typed) => hosts.filter((host) => host.name.toLowerCase().includes(typed.trim().toLowerCase())).slice(0, HOSTS_OFFERED).map((host) => ({ value: host.name, label: host.name, hint: host.address }));

export const count = (amount, one, many) => `${amount.toLocaleString()} ${amount === 1 ? one : many}`;

// What bringing an archive in costs this machine, in one clause, or nothing when every file here is in the archive unchanged.
export function lossOf(counts) {
  return [counts.removed > 0 && count(counts.removed, "file that is only here goes", "files that are only here go"), counts.replaced > 0 && count(counts.replaced, "file changes to the archive's version", "files change to the archive's version")].filter(Boolean).join(", and ");
}
