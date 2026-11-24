import { MOUNT_TOOL, PLACES, fileSystemName, sizeText } from "./words.js";

const STATE_RANK = { ready: 0, mounted: 1, blocked: 2 };

export const titleOf = (device) => device.name || device.key;

// The command's own rule for naming a device: its path, its key or its label, whole and whatever the case, and only when one device answers to it.
export function findDevice(devices, query) {
  const wanted = query.trim().toLowerCase();
  const found = devices.filter((device) => [device.path, device.key, device.name].some((text) => text !== "" && text.toLowerCase() === wanted));
  return found.length === 1 ? found[0] : null;
}

const bytesOf = (device) => device.size_bytes ?? -1;
const searchText = (device) => [device.name, device.key, device.path, fileSystemName(device), device.about, device.mounted_at, sizeText(device)].join(" ").toLowerCase();

// The devices a filter and a search leave, in the chosen order. "state" puts what can be mounted first, the biggest of those on top, since the
// small parts of a disk are rarely the one that is wanted. "disk" is the order the command lists them in, which keeps a disk's parts together.
export function arrange(devices, { filter, sort, term }) {
  const place = new Map(devices.map((device, index) => [device, index]));
  const orders = {
    state: (left, right) => STATE_RANK[left.state] - STATE_RANK[right.state] || (left.state === "ready" ? bytesOf(right) - bytesOf(left) : 0) || place.get(left) - place.get(right),
    size: (left, right) => bytesOf(right) - bytesOf(left) || place.get(left) - place.get(right),
    disk: (left, right) => place.get(left) - place.get(right),
  };
  return devices.filter((device) => (filter === "all" || device.state === filter) && (term === "" || searchText(device).includes(term))).sort(orders[sort]);
}

// Where a device sits: the parts of its disk in the order the command lists them, each with its share of the disk, and the words for it.
export function sittingOf(devices, device) {
  const parts = device.kind === "part" && device.parent ? devices.filter((other) => other.kind === "part" && other.parent === device.parent) : [device];
  const total = parts.reduce((sum, part) => sum + (part.size_bytes ?? 0), 0);
  const disk = devices.find((other) => other.kind === "disk" && other.key === device.parent);
  const on = disk?.about || device.parent;
  return {
    shares: parts.map((part) => ({ share: total > 0 ? (part.size_bytes ?? 0) / total : 1 / parts.length, own: part === device })),
    text: device.kind === "disk" ? device.about || "A whole disk" : on ? `Part ${parts.indexOf(device) + 1} of ${parts.length} on ${on}` : "",
  };
}

// What a device's plan starts from: where macOS puts it, a suggested folder on Linux, the first free letter on Windows. `preset` holds values by
// the command's parameter names, from whoever opened the view, and wins where it names something this device can do.
export function startingChoice(picture, device, preset) {
  const given = typeof preset.mount_point === "string" ? preset.mount_point.trim() : "";
  const named = given !== "" && given !== "-";
  const asked = device.ways.find((way) => way.usable && way.backend === preset.backend);
  return {
    place: picture.system === "Darwin" && !named ? "usual" : "folder",
    folder: named ? given : picture.system === "Linux" ? `/mnt/${titleOf(device).replaceAll("/", "-")}` : "",
    folderCheck: null,
    letter: picture.letters.find((letter) => letter === given.charAt(0).toUpperCase()) ?? picture.letters[0] ?? "",
    readOnly: Boolean(preset.read_only) && preset.read_only !== "off",
    backend: asked && asked.backend !== device.backend ? asked.backend : "",
    keyFile: typeof preset.key_file === "string" ? preset.key_file : "",
    keyCheck: null,
  };
}

// What stands in the way of using a typed path: nothing typed, the server still looking, or what it found there.
function hindrance(text, check, emptyText, waitingText) {
  if (text.trim() === "") return emptyText;
  if (!check) return waitingText;
  return check.error ?? (PLACES[check.verdict].stops ? PLACES[check.verdict].text : "");
}

// What mounting a device with these choices comes to: the way, the command's arguments, what will be asked for, where it ends up when that is
// known beforehand, and what still stands in the way. The command reads a mount point and a key file as they are typed, with no `~` and from its
// own folder, so both go to it as the full paths the server resolved.
export function planOf(picture, device, choice) {
  const way = device.ways.find((item) => item.backend === (choice.backend || device.backend));
  const problems = [];
  let place = { argument: "", shown: "" };
  if (way.places && picture.system === "Windows") {
    if (choice.letter === "") problems.push("No drive letter is free.");
    place = { argument: choice.letter, shown: `${choice.letter}:\\` };
  } else if (way.places && choice.place === "usual") place = { argument: "-", shown: "" };
  else if (way.places) {
    problems.push(hindrance(choice.folder, choice.folderCheck, "Type a folder, or pick one from the suggestions.", "Checking the folder…"));
    place = { argument: choice.folderCheck?.path ?? "", shown: choice.folderCheck?.path ?? "" };
  }
  const withKey = way.takes_key && choice.keyFile.trim() !== "";
  if (withKey) problems.push(hindrance(choice.keyFile, choice.keyCheck, "", "Checking the key file…"));
  const readOnly = choice.readOnly && way.read_only;
  return {
    way, place, withKey, readOnly,
    problems: problems.filter(Boolean),
    asks: withKey ? way.asks.filter((ask) => ask === "admin") : way.asks,
    arguments: [
      ...MOUNT_TOOL, "--device", device.path,
      ...(place.argument ? ["--mount-point", place.argument] : []),
      ...(way.backend === "mount" ? [] : ["--backend", way.backend]),
      ...(readOnly ? ["--read-only"] : []),
      ...(withKey && choice.keyCheck?.path ? ["--key-file", choice.keyCheck.path] : []),
    ],
  };
}

// The same choices by the command's parameter names, for its own form. A switch that is on is "on" there.
export function formPreset(device, plan) {
  const values = { device_query: device.path, mount_point: plan.place.argument, backend: plan.way.backend === "mount" ? "" : plan.way.backend, read_only: plan.readOnly ? "on" : "", key_file: plan.arguments.includes("--key-file") ? plan.arguments.at(-1) : "" };
  return Object.fromEntries(Object.entries(values).filter(([, value]) => value !== ""));
}
