import { PLACES, diskName, formatOf, roleOf, volumeName } from "./words.js";

const NEARLY_FULL = 0.1;
const GETTING_FULL = 0.2;
// The disk bar tells volumes apart by hue. Six is as many as it gives out: past that, hues are too close to tell apart for someone who is
// colour-blind, so further volumes are drawn in the quiet grey the system parts use and are still named in the list.
const HUE_SLOTS = 6;
const SLIVER = 0.005;

export const isMounted = (volume) => volume.mount_point !== "";

// The picture as groups of rows: each disk with its volumes, then the shares as one group of their own.
export function groupsOf(picture) {
  const disks = picture.disks.map((disk) => ({ id: disk.id, place: disk.place, title: diskName(disk), disk, volumes: disk.volumes }));
  return picture.shares.length ? [...disks, { id: "shares", place: "network", title: PLACES.network.name, disk: null, volumes: picture.shares }] : disks;
}

export const rowsOf = (groups) => groups.flatMap((group) => group.volumes.map((volume) => ({ volume, group })));

// How many other volumes draw on the same free space as this one.
export const sharingOf = (volume, group) => (volume.pool === "" ? 0 : group.volumes.filter((other) => other.pool === volume.pool).length - 1);

// The parts of a row's bar, as shares of the room the volume has: its own files, then what other volumes of its pool hold. The rest is free.
export function fullness(volume) {
  if (volume.used === null || volume.free === null || volume.size <= 0) return null;
  const others = volume.pool === "" ? 0 : Math.max(volume.size - volume.used - volume.free, 0);
  return { own: Math.min(volume.used / volume.size, 1), others: Math.min(others / volume.size, 1), free: volume.free / volume.size };
}

// A warning about room is only raised where room can run out: not for what cannot be written, and not for what the system looks after itself.
export function pressureOf(volume) {
  const full = fullness(volume);
  if (!full || volume.read_only || volume.helper || !isMounted(volume)) return "";
  return full.free < NEARLY_FULL ? "bad" : full.free < GETTING_FULL ? "warn" : "";
}

export function matcher(view) {
  const term = view.term.trim().toLowerCase();
  return ({ volume, group }) => {
    const hay = () => [volumeName(volume), ...formatOf(volume).slice(0, 1), volume.file_system, roleOf(volume)[0], volume.mount_point, volume.device, volume.id, group.title, PLACES[group.place].label].join("\n").toLowerCase();
    // Typing a word looks through the system parts too, so a search for one of them finds it without flipping the switch first.
    if (volume.helper && !view.parts && term === "") return false;
    if (view.place !== "all" && group.place !== view.place) return false;
    if (view.state !== "all" && isMounted(volume) !== (view.state === "mounted")) return false;
    return term === "" || hay().includes(term);
  };
}

const freeShare = (volume) => fullness(volume)?.free ?? 2;
const RANKS = {
  full: (left, right) => freeShare(left.volume) - freeShare(right.volume) || (right.volume.used ?? 0) - (left.volume.used ?? 0),
  data: (left, right) => (right.volume.used ?? -1) - (left.volume.used ?? -1),
  name: (left, right) => volumeName(left.volume).localeCompare(volumeName(right.volume), undefined, { sensitivity: "base", numeric: true }),
};
export const ranked = (rows, order) => [...rows].sort(RANKS[order]);

// Which hue each volume of a disk wears, by its place among the disk's own volumes. It never depends on a filter, so a volume keeps its colour.
export function slotsOf(disk) {
  const named = disk.volumes.filter((volume) => !volume.helper);
  return new Map(disk.volumes.map((volume) => [volume.id, volume.helper || named.indexOf(volume) >= HUE_SLOTS ? "quiet" : String(named.indexOf(volume) + 1)]));
}

const sum = (numbers) => numbers.reduce((total, number) => total + number, 0);

// A disk from end to end as the stretches its bar is drawn from. Each part of the disk is laid out in turn. Where its volumes share a pool,
// every volume's files come first, then what the system keeps there, then the free space they all draw on. Elsewhere each volume has a
// stretch of its own, split into its files and its free room when those are known. A part that holds nothing but system parts is one stretch.
export function stretchesOf(disk) {
  const slots = slotsOf(disk);
  const stretches = [];
  const add = (kind, bytes, volume, slot) => bytes > 0 && stretches.push({ kind, bytes, volume, slot });
  for (const region of disk.regions) {
    const volumes = disk.volumes.filter((volume) => volume.region === region.id);
    const named = volumes.filter((volume) => !volume.helper);
    if (volumes.length === 0) add("blank", region.size, null, "");
    else if (named.length === 0) add("parts", region.size, null, "quiet");
    else if (volumes.some((volume) => volume.pool !== "")) {
      for (const volume of named) add("used", volume.used ?? 0, volume, slots.get(volume.id));
      add("parts", sum(volumes.filter((volume) => volume.helper).map((volume) => volume.used ?? 0)), null, "quiet");
      add("free", Math.max(region.size - sum(volumes.map((volume) => volume.used ?? 0)), 0), null, "");
    } else {
      for (const volume of volumes) {
        if (volume.helper) add("parts", volume.size, null, "quiet");
        else if (volume.used === null) add("room", volume.size, volume, slots.get(volume.id));
        else {
          add("used", volume.used, volume, slots.get(volume.id));
          add("room", Math.max(volume.size - volume.used, 0), volume, slots.get(volume.id));
        }
      }
      add("blank", Math.max(region.size - sum(volumes.map((volume) => volume.size)), 0), null, "");
    }
  }
  const unused = disk.size - sum(disk.regions.map((region) => region.size));
  if (unused > disk.size * SLIVER) add("blank", unused, null, "");
  return stretches;
}

// The free room on a disk that someone can use: what its mounted volumes report, a shared pool counted once. Null when no volume says.
export function freeOn(disk) {
  const seen = new Set();
  let free = null;
  for (const volume of disk.volumes) {
    if (volume.helper || volume.free === null || seen.has(volume.pool || volume.id)) continue;
    seen.add(volume.pool || volume.id);
    free = (free ?? 0) + volume.free;
  }
  return free;
}

export function countsOf(picture) {
  const groups = groupsOf(picture);
  const volumes = rowsOf(groups).filter(({ volume }) => !volume.helper);
  const internal = picture.disks.filter((disk) => disk.place === "internal");
  const free = internal.map(freeOn).filter((amount) => amount !== null);
  return {
    free: free.length ? sum(free) : null, room: sum(internal.map((disk) => disk.size)), internal: internal.length,
    plugged: picture.disks.filter((disk) => disk.place !== "internal"),
    waiting: volumes.filter(({ volume, group }) => group.disk && !isMounted(volume)).length,
    mounted: volumes.filter(({ volume }) => isMounted(volume)).length,
    shares: picture.shares,
  };
}
