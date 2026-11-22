import { tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { plural } from "../../words.js";

export const KINDS = [
  { id: "configuration", label: "Settings files", short: "Settings", one: "settings file", glyph: "sliders", hue: 252, blurb: "The files this agent reads its settings from." },
  { id: "server", label: "Tool servers", short: "Tool servers", one: "tool server", glyph: "plug", hue: 200, blurb: "Outside tools the agent can call while it works." },
  { id: "hook", label: "Hooks", short: "Hooks", one: "hook", glyph: "bolt", hue: 30, blurb: "Commands that run by themselves at certain moments." },
  { id: "plugin", label: "Plugins", short: "Plugins", one: "plugin", glyph: "cube", hue: 290, blurb: "Add-ons that extend what the agent can do." },
  { id: "skill", label: "Skills", short: "Skills", one: "skill", glyph: "sparkle", hue: 330, blurb: "Know-how the agent picks up when a task calls for it." },
  { id: "instructions", label: "Instructions", short: "Instructions", one: "instruction file", glyph: "report", hue: 155, blurb: "Standing guidance the agent reads before it starts." },
];
export const KIND_BY_ID = Object.fromEntries(KINDS.map((kind) => [kind.id, kind]));
export const ORIGINS = {
  local: { label: "This project", hint: "Kept inside the folder being checked." },
  global: { label: "Your account", hint: "Applies to everything you do on this machine." },
  admin: { label: "This computer", hint: "Set by an administrator for every user." },
  system: { label: "Built in", hint: "Shipped with the agent itself." },
};
export const STATES = {
  active: { label: "In use", tone: "good" },
  configured: { label: "Set up", tone: "good" },
  available: { label: "Available", tone: "accent" },
  referenced: { label: "Linked", tone: "accent" },
  disabled: { label: "Switched off", tone: "warn" },
  shadowed: { label: "Overridden", tone: "warn" },
  missing: { label: "Not there", tone: "" },
};
const STATUSES = {
  incomplete: { label: "Incomplete check", tone: "bad", rank: 0 },
  attention: { label: "Needs attention", tone: "warn", rank: 1 },
  ready: { label: "Ready", tone: "good", rank: 2 },
  absent: { label: "Not installed", tone: "", rank: 3 },
};
const PROTECTED_DETAIL = "Protected path excluded from inspection";

const shortPath = (path) => tildify(path, state.boot.home);
export const softenPaths = (text) => text.replaceAll(`${state.boot.home}/`, "~/");

// The check reports a remark as "<where>: <what>"; the place is worth showing as its own copyable path.
function splitRemark(remark) {
  const found = remark.match(/^((?:\/|[A-Za-z]:\\)[^:]*): ([\s\S]+)$/);
  return found ? { where: found[1], text: softenPaths(found[2]) } : { where: null, text: softenPaths(remark) };
}

function toItem(kind, source) {
  const label = STATES[source.state]?.label ?? "";
  // `raw` keeps the name and detail as the check reported them: taking one thing away is asked for in those exact words.
  const item = { kind, raw: source, name: softenPaths(source.name), origin: source.origin, state: source.state ?? null, path: source.path, detail: softenPaths(source.detail), holdsServers: source.is_mcp === true };
  item.present = item.state !== "missing";
  item.reachable = item.present && source.detail !== PROTECTED_DETAIL;
  item.text = [item.name, KIND_BY_ID[kind].label, ORIGINS[item.origin].label, label, shortPath(item.path), item.detail].join(" ").toLowerCase();
  return item;
}

function asidesOf(items) {
  const count = (test) => items.filter(test).length;
  const overridden = count((item) => item.state === "shadowed");
  const off = count((item) => item.state === "disabled");
  const unread = count((item) => item.detail === PROTECTED_DETAIL);
  return [
    overridden > 0 && { text: `${plural(overridden, "item")} ${overridden === 1 ? "is" : "are"} overridden by another one and not used.`, find: STATES.shadowed.label },
    off > 0 && { text: `${plural(off, "item")} ${off === 1 ? "is" : "are"} switched off.`, find: STATES.disabled.label },
    unread > 0 && { text: `${plural(unread, "place")} ${unread === 1 ? "was" : "were"} left unread because ${unread === 1 ? "it is" : "they are"} protected.`, find: "Protected" },
  ].filter(Boolean);
}

export function prepare(reports) {
  return reports
    .map((report, position) => {
      const program = report.executable;
      const items = [...report.resources.map((resource) => toItem(resource.kind, resource)), ...report.mcp_servers.map((server) => toItem("server", server))];
      const issues = [
        ...report.errors.map((error) => ({ tone: "bad", title: "Part of this setup could not be read", ...splitRemark(error) })),
        ...(program.installed && program.error
          ? [{ tone: "warn", title: "It is installed, but it did not respond", text: `Asking it for its version failed: ${softenPaths(program.error)}`, where: program.path }]
          : []),
      ];
      const status = report.errors.length > 0 ? "incomplete" : !program.installed ? "absent" : program.error ? "attention" : "ready";
      return {
        id: report.agent, name: report.display_name, position, installed: program.installed, version: program.version, program: program.name, programPath: program.path,
        status: STATUSES[status], issues, asides: asidesOf(items), items,
        counts: Object.fromEntries(KINDS.map((kind) => [kind.id, items.filter((item) => item.kind === kind.id && item.present).length])),
        thorough: report.support_level === "focused", coverage: report.coverage_notes.map(softenPaths), limits: report.notes.map(splitRemark),
        directory: report.directory, projectRoot: report.project_root,
        text: [report.display_name, report.agent, program.version ?? "", STATUSES[status].label].join(" ").toLowerCase(),
      };
    })
    .sort((left, right) => left.status.rank - right.status.rank || left.position - right.position);
}

export function summarize(agents) {
  const installed = agents.filter((agent) => agent.installed);
  const troubled = agents.filter((agent) => agent.issues.length > 0);
  const ready = installed.filter((agent) => agent.issues.length === 0).length;
  const absent = agents.length - installed.length;
  const others = absent > 0 ? ` ${plural(absent, "other known agent")} ${absent === 1 ? "is" : "are"} not on this machine.` : "";
  let verdict;
  if (troubled.length > 0) {
    const worst = troubled.some((agent) => agent.status.tone === "bad") ? "bad" : "warn";
    const rest = ready > 0 ? `The other ${plural(ready, "installed agent")} ${ready === 1 ? "is" : "are"} ready.` : "";
    verdict = { tone: worst, glyph: "alert", title: `${plural(troubled.length, "agent")} ${troubled.length === 1 ? "needs" : "need"} attention`, body: `${rest}${others}`.trim() };
  } else if (installed.length === 0) {
    verdict = { tone: "", glyph: "info", title: "No agents are installed yet", body: `None of the ${agents.length} known agents were found on this machine.` };
  } else {
    const title = installed.length === 1 ? "The one installed agent is ready" : `All ${installed.length} installed agents are ready`;
    verdict = { tone: "good", glyph: "check", title, body: `${installed.length === 1 ? "It" : "Each one"} responded when asked, and its setup could be read in full.${others}` };
  }
  return { verdict, troubled, counts: { all: agents.length, installed: installed.length, attention: troubled.length, absent } };
}

export const matchesTerm = (item, term) => term === "" || item.text.includes(term);

// Hooks arrive as one entry per moment; the same command at fifteen moments reads better as one row.
function mergeHooks(items) {
  const merged = new Map();
  for (const item of items) {
    const [moment, ...rest] = item.detail.split(": ");
    const command = rest.join(": ");
    const key = `${item.path}\n${item.origin}\n${command}`;
    const title = (command === "" || command === shortPath(item.path) || item.name.endsWith(command) ? item.name : command).replace(/^command: /, "");
    if (!merged.has(key)) merged.set(key, { ...item, name: title, detail: "", moments: [], states: new Set(), command: true });
    const row = merged.get(key);
    row.moments.push(moment);
    row.states.add(item.state);
  }
  return [...merged.values()];
}

// Rows that come out of the same file sit under that file, so where each one comes from is said once.
export function groupBySource(items, kind) {
  const groups = new Map();
  for (const item of kind === "hook" ? mergeHooks(items) : items) {
    const key = `${item.path}\n${item.origin}`;
    if (!groups.has(key)) groups.set(key, { path: item.path, origin: item.origin, rows: [] });
    groups.get(key).rows.push(item);
  }
  return [...groups.values()];
}
