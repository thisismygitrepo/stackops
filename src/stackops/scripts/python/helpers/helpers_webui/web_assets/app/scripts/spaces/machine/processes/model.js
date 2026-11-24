import { HEAVY_CPU, HEAVY_MEMORY, statusOf } from "./words.js";

const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

// A process is named by its ID together with its start time: an ID is handed out again once its process has gone.
export const keyOf = (process) => `${process.pid}:${process.started}`;

export const FLAGS = {
  cpu: (process) => (process.cpu ?? 0) >= HEAVY_CPU,
  memory: (process) => (process.memory ?? 0) >= HEAVY_MEMORY,
  ports: (process) => process.ports.length > 0,
  apps: (process) => process.role !== "system",
};

function addUp(process) {
  let cpu = process.cpu;
  let memory = process.memory;
  let size = 0;
  for (const child of process.children) {
    addUp(child);
    if (child.groupCpu !== null) cpu = (cpu ?? 0) + child.groupCpu;
    if (child.groupMemory !== null) memory = (memory ?? 0) + child.groupMemory;
    size += 1 + child.groupSize;
  }
  Object.assign(process, { groupCpu: cpu, groupMemory: memory, groupSize: size });
}

// One reading of the machine, with what the page works out from it: each process's place under the one that started it, the totals of each
// such group, and why a process cannot be stopped from here (`lock`).
export function buildModel(snapshot) {
  const processes = snapshot.processes.map((row) => ({
    ...row, key: keyOf(row), children: [], parentRef: null,
    lock: row.status === "zombie" ? "ended" : row.mine || snapshot.privileged ? "" : "foreign",
    text: `${row.name} ${row.command} ${row.pid} ${row.user} ${row.ports.join(" ")}`.toLowerCase(),
  }));
  const byPid = new Map(processes.map((process) => [process.pid, process]));
  const roots = [];
  for (const process of processes) {
    // What the system's first process started sits at the top level. Nearly everything hangs off that one, and a single tree of the whole machine says nothing.
    const parent = process.parent > 1 && process.parent !== process.pid ? byPid.get(process.parent) : undefined;
    if (!parent) roots.push(process);
    else {
      process.parentRef = parent;
      parent.children.push(process);
    }
  }
  // An ID can be handed out again while the list is being read, which can leave two processes each naming the other as its starter.
  // Nothing reaches such a ring from the top level, so it is cut at one of its processes, which then stands at the top level itself.
  const reached = new Set();
  const reach = (process) => {
    reached.add(process);
    process.children.forEach(reach);
  };
  roots.forEach(reach);
  for (const process of processes) {
    if (reached.has(process)) continue;
    process.parentRef.children = process.parentRef.children.filter((child) => child !== process);
    process.parentRef = null;
    roots.push(process);
    reach(process);
  }
  roots.forEach(addUp);
  return { ...snapshot, processes, roots, byPid, byKey: new Map(processes.map((process) => [process.key, process])) };
}

export const isNarrowed = (filters) => filters.term !== "" || filters.flags.size > 0 || filters.status !== "" || filters.given.length > 0;

export function matcher(filters) {
  const words = filters.term.toLowerCase().split(/\s+/).filter(Boolean);
  return (process) =>
    (filters.scope === "all" || process.mine) &&
    words.every((word) => process.text.includes(word)) &&
    [...filters.flags].every((flag) => FLAGS[flag](process)) &&
    (filters.status === "" || process.status === filters.status) &&
    filters.given.every((condition) => condition.test(process));
}

const READERS = {
  name: (process) => process.name,
  pid: (process) => process.pid,
  user: (process) => process.user,
  cpu: (process) => process.cpu,
  memory: (process) => process.memory,
  status: (process) => statusOf(process.status).label,
  started: (process) => process.started,
  ports: (process) => process.ports[0] ?? null,
  command: (process) => process.command || null,
};

// A process with nothing to compare goes last whichever way the column is sorted, and equal ones keep the order of their IDs, so rows do not
// change places from one reading to the next for no reason. `grouped` compares a process together with everything it started.
export function comparer({ column, descending }, grouped) {
  const read = grouped && column === "cpu" ? (process) => process.groupCpu : grouped && column === "memory" ? (process) => process.groupMemory : READERS[column];
  return (left, right) => {
    const [first, second] = [read(left), read(right)];
    if (first === null || second === null) return first === second ? left.pid - right.pid : first === null ? 1 : -1;
    const order = typeof first === "number" ? first - second : collator.compare(first, second);
    return (descending ? -order : order) || left.pid - right.pid;
  };
}

export function listRows(model, filters, sort) {
  const rows = model.processes.filter(matcher(filters)).sort(comparer(sort, false)).map((process) => ({ process, depth: 0, inside: 0, expanded: false, context: false }));
  return { rows, matched: rows.length };
}

// Each process under the one that started it. A process that does not fit the filters is kept, dimmed, when something under it does.
// While the list is narrowed every branch that leads to a match is open; otherwise a branch is open when the person opened it.
export function treeRows(model, filters, sort, open) {
  const fits = matcher(filters);
  const matched = new Set(model.processes.filter(fits));
  const kept = new Set();
  const keep = (process) => {
    const below = process.children.map(keep).some(Boolean);
    if (below || matched.has(process)) kept.add(process);
    return kept.has(process);
  };
  model.roots.forEach(keep);
  const compare = comparer(sort, true);
  const openAll = isNarrowed(filters);
  const rows = [];
  const walk = (process, depth) => {
    const inside = process.children.filter((child) => kept.has(child)).sort(compare);
    const expanded = inside.length > 0 && (openAll || open.has(process.key));
    rows.push({ process, depth, inside: inside.length, expanded, context: !matched.has(process) });
    if (expanded) for (const child of inside) walk(child, depth + 1);
  };
  for (const root of model.roots.filter((process) => kept.has(process)).sort(compare)) walk(root, 0);
  return { rows, matched: matched.size };
}

// The groups that use the most of one thing right now: a process together with everything it started, largest first.
export function topGroups(model, field, count) {
  return model.roots.filter((process) => (process[field] ?? 0) > 0).sort((left, right) => right[field] - left[field]).slice(0, count);
}

export function descendants(process) {
  return process.children.flatMap((child) => [child, ...descendants(child)]);
}

export function ancestors(process) {
  const chain = [];
  for (let current = process.parentRef; current; current = current.parentRef) chain.unshift(current);
  return chain;
}

// How many processes each quick filter and each state would leave, counted within the chosen owner only.
export function tally(model, scope) {
  const inScope = model.processes.filter((process) => scope === "all" || process.mine);
  const statuses = new Map();
  for (const process of inScope) statuses.set(process.status, (statuses.get(process.status) ?? 0) + 1);
  return {
    mine: model.processes.filter((process) => process.mine).length,
    all: model.processes.length,
    flags: Object.fromEntries(Object.entries(FLAGS).map(([flag, test]) => [flag, inScope.filter(test).length])),
    statuses: [...statuses].sort(([left], [right]) => collator.compare(statusOf(left).label, statusOf(right).label)),
  };
}
