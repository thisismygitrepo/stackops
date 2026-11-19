import { formatDuration, h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { api, emit, state } from "/assets/scripts/state.js";
import { openConsole } from "./console_session.js";
import { markStale } from "./data.js";
import { burst, replay } from "./motion.js";
import { button, emojiTile, iconButton, notice } from "./widgets.js";
import { fullTitleOf } from "./words.js";

function describeArguments(runArguments) {
  for (let length = runArguments.length; length > 0; length -= 1) {
    const node = state.nodes.get(runArguments.slice(0, length).join(" "));
    if (node) return { title: fullTitleOf(node), emoji: node.icon };
  }
  return { title: "Task", emoji: "" };
}

const statusOf = (summary) => (summary.exit_code === null ? "running" : summary.exit_code === 0 ? "done" : "failed");

export function createActivity({ openReport }) {
  const tasks = new Map();
  let activeId = null;
  const chips = h("div", { class: "task-chips", role: "tablist" });
  const hero = h("div", { class: "task-hero" });
  const consoles = h("div", { class: "task-consoles" });
  const sizeButton = iconButton("expand", "Fill the window", () => setMode(element.dataset.mode === "max" ? "open" : "max"));
  const element = h(
    "aside",
    { class: "activity", "data-mode": "closed", "aria-label": "Activity", inert: true },
    h("header", { class: "activity-head" }, h("h2", { text: "Activity" }), h("span", { class: "spacer" }), sizeButton, iconButton("close", "Hide activity", () => setMode("closed"))),
    chips,
    hero,
    consoles,
  );
  const pillGlyph = h("span", { class: "activity-glyph" });
  const pillLabel = h("span");
  const indicator = h("button", { class: "activity-pill", type: "button", title: "Show what is running", onclick: () => setMode(element.dataset.mode === "closed" ? "open" : "closed") }, pillGlyph, pillLabel);

  const visible = () => [...tasks.values()].filter((task) => !task.quiet);

  function fit(task) {
    if (!task.fit || consoles.clientHeight < 40 || !task.fit.proposeDimensions()) return false;
    task.fit.fit();
    return true;
  }

  function setMode(mode) {
    element.dataset.mode = mode;
    element.inert = mode === "closed";
    sizeButton.replaceChildren(icon(mode === "max" ? "shrink" : "expand", 16));
    document.body.classList.toggle("activity-open", mode !== "closed");
    setTimeout(() => tasks.forEach(fit), 340);
  }

  function paintHero() {
    const task = tasks.get(activeId);
    if (!task) {
      hero.replaceChildren(notice({ glyph: "bolt", title: "Nothing running", body: "Whatever you start shows up here, live." }));
      return;
    }
    const { summary } = task;
    const status = statusOf(summary);
    const where = tildify(summary.working_directory, state.boot.home);
    const elapsed = formatDuration((summary.finished_at ?? Date.now() / 1000) - summary.started_at);
    const line = status === "running" ? `Running for ${elapsed} in ${where}` : status === "done" ? `Finished in ${elapsed}` : `Stopped after ${elapsed} with a problem (code ${summary.exit_code})`;
    const mark = h("span", { class: `task-mark ${status}` }, status === "running" ? h("i", { class: "ring" }) : icon(status === "done" ? "check" : "alert", 22));
    hero.replaceChildren(
      mark,
      h("div", { class: "task-text" }, h("h3", { text: task.title }), h("p", { text: line })),
      h(
        "div",
        { class: "task-actions" },
        summary.reports.map((name) => button({ label: "View report", glyph: "report", small: true, onclick: () => openReport({ title: task.title, blurb: "", file: name }) })),
        status === "running"
          ? button({ label: "Stop", glyph: "stop", small: true, tone: "danger", onclick: () => api.stopRun(task.id).catch((error) => toast(error.message)) })
          : button({ label: "Run again", glyph: "refresh", small: true, onclick: () => start({ title: task.title, emoji: task.emoji, arguments: summary.arguments, interactive: summary.interactive, reveal: true }).catch((error) => toast(error.message)) }),
      ),
    );
    hero.dataset.status = status;
  }

  function paint() {
    const shown = visible();
    for (const task of tasks.values()) {
      task.chip.hidden = task.quiet;
      task.chip.setAttribute("aria-selected", String(task.id === activeId));
      task.chip.dataset.status = statusOf(task.summary);
      task.pane.classList.toggle("active", task.id === activeId);
    }
    const running = shown.filter((task) => task.summary.exit_code === null).length;
    pillGlyph.replaceChildren(running ? h("i", { class: "ring" }) : icon("bolt", 15));
    pillLabel.textContent = running ? `${running} running` : "Activity";
    indicator.classList.toggle("busy", running > 0);
    indicator.dataset.count = shown.length ? String(shown.length) : "";
    paintHero();
  }

  function activate(id) {
    activeId = id;
    paint();
    requestAnimationFrame(() => {
      const task = tasks.get(id);
      if (task && fit(task) && element.dataset.mode !== "closed") task.terminal.focus();
    });
  }

  async function connect(task) {
    const session = await openConsole({
      pane: task.pane, runId: task.id, fitNow: () => fit(task),
      onSummary: (summary) => {
        const wasRunning = task.summary.exit_code === null;
        Object.assign(task.summary, summary);
        paint();
        task.settle(task.summary);
        emit("runs");
        if (!wasRunning || task.quiet) return;
        markStale();
        const succeeded = task.summary.exit_code === 0;
        if (element.dataset.mode === "closed") toast(succeeded ? `${task.title} finished.` : `${task.title} stopped with a problem.`, succeeded ? "info" : "error");
        else if (succeeded && task.id === activeId) burst(hero.querySelector(".task-mark"));
        replay(indicator, "pulse");
      },
    });
    if (!session) return;
    Object.assign(task, session);
    if (task.id === activeId) fit(task);
  }

  function createTask(summary, { title, emoji, quiet }) {
    const pane = h("div", { class: "console" });
    const closer = h("span", { class: "chip-close", role: "button", title: "Remove" }, icon("close", 11));
    const chip = h("button", { class: "task-chip", type: "button", role: "tab" }, h("i", { class: "dot" }), h("span", { text: title }), closer);
    let settle;
    const done = new Promise((resolve) => (settle = resolve));
    const task = { id: summary.id, summary, title, emoji, quiet, pane, chip, done, settle, terminal: null, fit: null, socket: null };
    chip.addEventListener("click", (event) => (closer.contains(event.target) ? remove(task.id) : activate(task.id)));
    tasks.set(task.id, task);
    chips.append(chip);
    consoles.append(pane);
    connect(task);
    return task;
  }

  async function remove(id) {
    const task = tasks.get(id);
    if (!task) return;
    try {
      await api.deleteRun(id);
    } catch (error) {
      toast(error.message);
    }
    task.socket?.close();
    task.terminal?.dispose();
    task.chip.remove();
    task.pane.remove();
    tasks.delete(id);
    if (activeId === id) activeId = visible().at(-1)?.id ?? null;
    activate(activeId);
    emit("runs");
  }

  function reveal(id) {
    const task = tasks.get(id);
    if (!task) return;
    task.quiet = false;
    if (element.dataset.mode === "closed") setMode("open");
    activate(id);
    emit("runs");
  }

  async function start({ title, emoji, arguments: runArguments, interactive, reveal: show }) {
    const fitted = tasks.get(activeId);
    const width = Math.min(element.offsetWidth || 760, window.innerWidth);
    const size = fitted?.terminal && fit(fitted) ? { rows: fitted.terminal.rows, columns: fitted.terminal.cols } : { rows: 28, columns: Math.max(60, Math.floor((width - 64) / 7.85)) };
    const summary = await api.startRun({ arguments: runArguments, working_directory: state.settings.workingDirectory, interactive, ...size });
    const described = describeArguments(runArguments);
    const task = createTask(summary, { title: title ?? described.title, emoji: emoji ?? described.emoji, quiet: !show });
    if (show) reveal(task.id);
    else paint();
    emit("runs");
    return task;
  }

  async function restore() {
    const { runs } = await api.runs();
    for (const run of runs) createTask(run, { ...describeArguments(run.arguments), quiet: false });
    if (runs.length) activate(runs.at(-1).id);
    emit("runs");
  }

  setInterval(() => element.dataset.mode !== "closed" && tasks.get(activeId)?.summary.exit_code === null && paintHero(), 1000);
  new ResizeObserver(() => requestAnimationFrame(() => tasks.forEach(fit))).observe(consoles);
  paint();

  return {
    element, indicator, start, restore, reveal, remove,
    runs: () => visible().map((task) => ({ ...task.summary, title: task.title, emoji: task.emoji, tile: emojiTile(task.emoji || "✨", task.title, 34) })),
  };
}
