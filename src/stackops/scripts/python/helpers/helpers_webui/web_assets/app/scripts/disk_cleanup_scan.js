import { capture } from "./data.js";
import { CLEANUP_TOOL } from "./disk_cleanup_words.js";

const PARALLEL_SCANS = 4;
const SLOW_SECONDS = 85;

// Measuring everything takes longer than one read-only request may run, so each place is measured by its own request and fills in as it arrives.
// Everything found by searching project folders shares one request: walking the folders is the slow part, so it happens once.
export function createCleanupScanner({ onChange }) {
  const targets = new Map();
  const lastBytes = new Map();
  const queue = [];
  const waiters = [];
  let catalog = [];
  let disk = null;
  let failure = "";
  let loading = false;
  let roots = [];
  let active = 0;
  let tickets = 0;
  let generation = 0;
  let startedAt = 0;
  let finishedAt = 0;
  let measuredAt = 0;

  const isPending = (key) => ["waiting", "measuring"].includes(targets.get(key)?.phase);
  const pending = () => [...targets.keys()].some(isPending);

  function settle() {
    if (loading) return;
    for (const waiter of waiters.splice(0)) {
      if (waiter.keys.some(isPending)) waiters.push(waiter);
      else waiter.resolve();
    }
    if (pending() || !startedAt || finishedAt) return;
    finishedAt = performance.now();
    measuredAt = Date.now();
  }

  function pump() {
    while (active < PARALLEL_SCANS && queue.length) measure(queue.shift());
    settle();
    onChange();
  }

  function apply(target, record) {
    if (!record) return Object.assign(target, { phase: "error", problem: "The scan did not report on this one." });
    const bytes = record.estimate_bytes ?? 0;
    lastBytes.set(target.key, bytes);
    Object.assign(target, {
      phase: "done", status: record.status === "ready" && record.estimate_bytes === 0 ? "empty" : record.status, bytes, sized: record.estimate_bytes !== null,
      estimateKind: record.estimate_kind, paths: record.paths, commands: record.commands, message: record.message, requires_root: record.requires_root,
    });
  }

  async function measure(keys) {
    const issued = keys.map((key) => targets.get(key)?.ticket);
    const current = () => keys.filter((key, index) => issued[index] !== undefined && targets.get(key)?.ticket === issued[index]);
    if (current().length === 0) return;
    const began = performance.now();
    const searching = keys.some((key) => targets.get(key)?.action_kind === "projects");
    active += 1;
    for (const key of current()) targets.get(key).phase = "measuring";
    try {
      const { json } = await capture([...CLEANUP_TOOL, "--dry-run", "--json", ...current().flatMap((key) => ["--target", key]), ...(searching ? roots.flatMap((root) => ["--root", root]) : [])]);
      if (!Array.isArray(json)) throw new Error("The scan answered in a form this page does not understand.");
      const records = new Map(json.map((record) => [record.key, record]));
      for (const key of current()) apply(targets.get(key), records.get(key));
    } catch (error) {
      // A design choice: a project search that fails (usually out of time) is not split into one request per place. Each of those would walk the
      // same folders again, so a slow search became eight slow searches. Its places say so and point at Options, where the search can be narrowed.
      for (const key of current()) Object.assign(targets.get(key), { phase: "error", problem: error.message, slow: (performance.now() - began) / 1000 >= SLOW_SECONDS });
    }
    active -= 1;
    pump();
  }

  function enqueue(keys) {
    const wanted = keys.filter((key) => targets.has(key));
    if (wanted.length === 0) {
      settle();
      return onChange();
    }
    if (!pending()) {
      startedAt = performance.now();
      finishedAt = 0;
    }
    for (const key of wanted) Object.assign(targets.get(key), { phase: "waiting", ticket: (tickets += 1), problem: "", slow: false });
    const searched = wanted.filter((key) => targets.get(key).action_kind === "projects");
    const single = wanted.filter((key) => targets.get(key).action_kind !== "projects").sort((left, right) => (lastBytes.get(right) ?? 0) - (lastBytes.get(left) ?? 0));
    queue.push(...(searched.length ? [searched] : []), ...single.map((key) => [key]));
    pump();
  }

  async function readCatalog() {
    const { json } = await capture([...CLEANUP_TOOL, "--list", "--json"]);
    if (!Array.isArray(json?.targets)) throw new Error("The list of places to clean could not be read.");
    disk = { free: json.free_bytes, total: json.total_bytes };
    return json.targets;
  }

  function adopt(categories) {
    for (const key of [...targets.keys()]) if (!categories.has(targets.get(key).category)) targets.delete(key);
    const added = catalog.filter((record) => categories.has(record.category) && !targets.has(record.key));
    for (const record of added) targets.set(record.key, { ...record, phase: "new", ticket: 0, status: "", bytes: 0, sized: false, estimateKind: "exact", paths: [], commands: [], message: "", problem: "", slow: false });
    return added.map((record) => record.key);
  }

  async function start({ categories, searchRoots }) {
    const mine = (generation += 1);
    roots = searchRoots;
    failure = "";
    loading = true;
    queue.length = 0;
    targets.clear();
    startedAt = performance.now();
    finishedAt = 0;
    onChange();
    try {
      const listed = await readCatalog();
      if (mine !== generation) return;
      catalog = listed;
    } catch (error) {
      if (mine !== generation) return;
      failure = error.message;
      catalog = [];
    }
    loading = false;
    enqueue(adopt(categories));
  }

  return {
    targets, start,
    disk: () => disk,
    failure: () => failure,
    // Resolves once these places have an answer, however much of the scan is still going for the others.
    whenMeasured: (keys) => (loading || keys.some(isPending) ? new Promise((resolve) => waiters.push({ keys, resolve })) : Promise.resolve()),
    refreshDisk: () => readCatalog().then(onChange),
    remeasure: (keys) => enqueue(keys),
    // One search measures every project place, so trying one of them again takes along the others that failed.
    retry: (key) => enqueue(targets.get(key).action_kind === "projects" ? [...targets.values()].filter((target) => target.action_kind === "projects" && target.phase === "error").map((target) => target.key) : [key]),
    setCategories: (categories) => enqueue(adopt(categories)),
    setRoots(searchRoots) {
      roots = searchRoots;
      enqueue([...targets.values()].filter((target) => target.action_kind === "projects").map((target) => target.key));
    },
    progress() {
      const all = [...targets.values()];
      return {
        loading, total: all.length, done: all.filter((target) => target.phase === "done" || target.phase === "error").length, busy: loading || pending(),
        measuring: all.filter((target) => target.phase === "measuring"), seconds: ((finishedAt || performance.now()) - startedAt) / 1000, measuredAt,
      };
    },
  };
}
