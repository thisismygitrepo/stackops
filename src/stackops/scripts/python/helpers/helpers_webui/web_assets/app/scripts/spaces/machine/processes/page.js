import { h, icon, toast } from "/assets/scripts/dom.js";
import { recall, remember } from "../../../memory.js";
import { replay } from "../../../motion.js";
import { button, notice, skeleton } from "../../../widgets.js";
import { readProcesses, stopProcesses } from "./api.js";
import { confirmStop } from "./confirm.js";
import { openDetail } from "./detail.js";
import { createLive } from "./live.js";
import { ancestors, buildModel, isNarrowed, keyOf, listRows, tally, treeRows } from "./model.js";
import { createOutcome, createTray } from "./outcome.js";
import { createProblem } from "./problem.js";
import { createSummary } from "./summary.js";
import { COLUMNS, createTable } from "./table.js";
import { createToolbar } from "./toolbar.js";
import { REFRESH_MILLISECONDS, TOOL_PATH, givenFilters } from "./words.js";

const MEMORY_ID = "machine processes";
const ROW_STEP = 100;
// The first reading has no CPU figures: they are what a process did since the reading before. So a second one follows this soon.
const SECOND_READING_MILLISECONDS = 1200;
const HEARTBEAT_MILLISECONDS = 500;
// A reading costs the server more the more processes there are. The next one waits this many times as long as the last one took, so
// following the machine never takes more than a few percent of one processor core, and at most this long.
const REST_FACTOR = 25;
const SLOWEST_MILLISECONDS = 12000;

// Processes: every process on arrival, read again every few seconds, narrowed and sorted in the page, and stopped behind a confirmation.
export function createProcessesPage({ tools }) {
  const kept = recall(MEMORY_ID);
  const filters = { scope: kept.get("scope") === "mine" ? "mine" : "all", term: "", flags: new Set(), status: "", given: [] };
  const sort = { column: COLUMNS.some((column) => column.id === kept.get("column")) ? kept.get("column") : "memory", descending: kept.get("descending") !== "no" };
  const view = { mode: kept.get("mode") === "tree" ? "tree" : "list" };
  // Branches the person opened, and the ones they closed while the list was narrowed and every branch was open.
  const open = new Set();
  const closed = new Set();
  const picked = new Set();
  const watchers = new Set();
  const state = { model: null, rows: [], scales: { cpu: 100, memory: 1 }, limit: ROW_STEP, paused: false, loading: false, stopping: false, ended: false, failure: null, asked: 0, every: REFRESH_MILLISECONDS };

  const keep = () => remember(MEMORY_ID, new Map([["scope", filters.scope], ["mode", view.mode], ["column", sort.column], ["descending", sort.descending ? "yes" : "no"]]));
  const chosen = () => [...picked].map((key) => state.model.byKey.get(key)).filter(Boolean);
  const paintTray = () => tray.paint({ processes: state.model ? chosen() : [], busy: state.stopping });
  const paintLive = () => live.paint({ paused: state.paused, failing: state.failure !== null, ended: state.ended, readAt: state.model?.taken_at ?? 0, loading: state.loading });

  function changed() {
    state.limit = ROW_STEP;
    closed.clear();
    keep();
    paint();
  }

  function pick(processes, on) {
    for (const process of processes) {
      if (on && process.lock === "") picked.add(process.key);
      else picked.delete(process.key);
    }
    table.syncPicks();
    paintTray();
    replay(tray.element, "bump");
  }

  const page = {
    model: () => state.model,
    scale: () => state.scales,
    watch(listener) {
      watchers.add(listener);
      return () => watchers.delete(listener);
    },
    stop,
    reveal,
  };
  const live = createLive({
    onRefresh: () => load(true),
    onToggle() {
      state.paused = !state.paused;
      if (state.paused) paint();
      else load(true);
    },
  });
  const summary = createSummary({
    onReveal: (process) => reveal(process.key),
    onFilter({ scope, flags, status }) {
      Object.assign(filters, { scope, term: "", status, given: [] });
      filters.flags.clear();
      for (const flag of flags) filters.flags.add(flag);
      changed();
      toolbar.element.scrollIntoView({ block: "start", behavior: "smooth" });
    },
  });
  const toolbar = createToolbar({ filters, view, onChange: changed });
  const outcome = createOutcome({ onForce: (keys) => stop(keys.map((key) => state.model.byKey.get(key)).filter(Boolean), true), onChange: () => paint() });
  const tray = createTray({ onClear: () => pick(chosen(), false), onStop: (force) => stop(chosen(), force) });
  const table = createTable({
    picked, sort,
    tree: () => view.mode === "tree",
    scale: () => state.scales,
    now: () => state.model.taken_at,
    noteOf: outcome.noteOf,
    onPick: (process, on) => pick([process], on),
    onPickMany: pick,
    onOpen: (process) => openDetail({ process, page }),
    onStop: (process) => stop([process], false),
    onSort(column, biggestFirst) {
      if (sort.column === column) sort.descending = !sort.descending;
      else Object.assign(sort, { column, descending: biggestFirst });
      changed();
    },
    onMore() {
      state.limit += ROW_STEP;
      paint();
    },
    onTwist({ key }) {
      const turned = isNarrowed(filters) ? closed : open;
      if (turned.has(key)) turned.delete(key);
      else turned.add(key);
      paint();
    },
  });
  const problem = createProblem({ tools, onRetry: () => load(true) });
  const waiting = h("div", { class: "procs-waiting" }, skeleton(8, "row"));
  const empty = h("div", { class: "procs-empty" });
  const element = h(
    "div",
    { class: "procs" },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "procs-back", href: "#/machine" }, icon("back", 14), h("span", { text: "Machine" })), h("h1", { text: "Processes" }), h("p", { text: "Everything running on this machine, read again every few seconds. Find what is slowing it down and stop it." })),
      h("div", { class: "view-actions" }, live.elements, button({ label: "All options", glyph: "sliders", title: "The plain form, with every option of the command behind this page", onclick: () => tools.open(TOOL_PATH, { plain: true }) })),
    ),
    problem.element, waiting, summary.element, outcome.element, toolbar.element, table.element, empty, tray.element,
  );

  function paint() {
    const { model } = state;
    paintLive();
    problem.paint({ listed: model !== null, failure: state.failure, ended: state.ended });
    waiting.hidden = model !== null || state.failure !== null;
    for (const part of [summary.element, toolbar.element, table.element, empty]) part.hidden = model === null;
    paintTray();
    if (!model) return;
    const grouped = view.mode === "tree";
    const figures = (field) => (grouped ? model.roots.map((process) => process[`group${field}`] ?? 0) : model.processes.map((process) => process[field.toLowerCase()] ?? 0));
    state.scales = { cpu: Math.max(100, ...figures("Cpu")), memory: Math.max(1, ...figures("Memory")) };
    summary.paint(model);
    const result = grouped ? treeRows(model, filters, sort, open, closed) : listRows(model, filters, sort);
    state.rows = result.rows;
    toolbar.paint(tally(model, filters.scope), result.matched);
    table.render(result.rows.slice(0, state.limit), result.rows.length, ROW_STEP);
    table.element.hidden = result.rows.length === 0;
    empty.hidden = result.rows.length > 0;
    if (result.rows.length === 0 && !empty.hasChildNodes()) empty.append(notice({ glyph: "search", title: "Nothing matches", body: "No process fits these filters.", action: button({ label: "Clear filters", small: true, onclick: () => toolbar.reset() }) }));
  }

  async function load(fresh = false) {
    if (state.loading || state.ended) return;
    state.loading = true;
    state.asked = Date.now();
    paintLive();
    try {
      state.model = buildModel(await readProcesses(fresh));
      state.failure = null;
      state.every = Math.min(SLOWEST_MILLISECONDS, Math.max(REFRESH_MILLISECONDS, (Date.now() - state.asked) * REST_FACTOR));
    } catch (error) {
      state.failure = error;
    }
    state.loading = false;
    if (state.model) {
      for (const key of [...picked]) if ((state.model.byKey.get(key)?.lock ?? "gone") !== "") picked.delete(key);
      outcome.follow(state.model);
    }
    paint();
    for (const watcher of watchers) watcher();
    if (!state.failure && state.model.machine.cpu === null) setTimeout(() => !state.paused && load(), SECOND_READING_MILLISECONDS);
  }

  async function stop(processes, force) {
    if (state.stopping || state.ended || processes.length === 0) return;
    const answer = await confirmStop({ processes, force });
    if (!answer) return;
    const named = new Map(answer.processes.map((process) => [process.key, process]));
    const hosts = answer.processes.filter((process) => process.role === "server" || process.role === "server_parent").map((process) => process.key);
    state.stopping = true;
    paintTray();
    try {
      const { results } = await stopProcesses(answer.processes, answer.force);
      for (const result of results) if (result.outcome !== "still_running") picked.delete(keyOf(result));
      outcome.show({ force: answer.force, entries: results.map((result) => ({ key: keyOf(result), name: named.get(keyOf(result)).name, pid: result.pid, outcome: result.outcome, error: result.error })) });
      state.ended = results.some((result) => hosts.includes(keyOf(result)) && (result.outcome === "stopped" || result.outcome === "still_running"));
    } catch (error) {
      // Stopping StackOps, or what it runs inside, cuts the answer off. That is the stop working, not failing.
      state.ended = hosts.length > 0;
      if (!state.ended) toast(error.message);
    }
    state.stopping = false;
    if (state.ended) paint();
    else await load(true);
    outcome.element.scrollIntoView({ block: "center", behavior: "smooth" });
  }

  // Shows one process in the tree with nothing in its way: its owner, the filters, a closed branch above it or the length of the list.
  function reveal(key) {
    const process = state.model?.byKey.get(key);
    if (!process) return toast("That process has ended.", "info");
    Object.assign(filters, { scope: process.mine ? filters.scope : "all", term: "", status: "", given: [] });
    filters.flags.clear();
    view.mode = "tree";
    for (const above of ancestors(process)) open.add(above.key);
    if (process.children.length > 0) open.add(process.key);
    changed();
    const index = state.rows.findIndex((item) => item.process === process);
    if (index >= state.limit) {
      state.limit = index + ROW_STEP;
      paint();
    }
    const line = table.lineOf(key);
    if (!line) return;
    line.scrollIntoView({ block: "center", behavior: "smooth" });
    replay(line, "procs-flash");
  }

  // Filters another view opened the page with, by the command's parameter names. A state has a chip of its own in the toolbar; the rest get one each.
  function applyPreset(preset) {
    const given = givenFilters(preset);
    if (given.length === 0) return;
    Object.assign(filters, { scope: "all", term: "", status: given.some((item) => item.name === "status") ? String(preset.status).trim() : "", given: given.filter((item) => item.name !== "status") });
    filters.flags.clear();
    changed();
  }

  const onScreen = () => element.isConnected && !element.closest("[hidden]") && document.visibilityState === "visible";
  setInterval(() => !state.paused && onScreen() && Date.now() - state.asked >= state.every && load(), HEARTBEAT_MILLISECONDS);
  paint();
  return { element, applyPreset, show: () => !state.paused && Date.now() - state.asked >= SECOND_READING_MILLISECONDS && load() };
}
