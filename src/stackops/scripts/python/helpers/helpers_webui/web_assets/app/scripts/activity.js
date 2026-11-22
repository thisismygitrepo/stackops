import { debounce, h, icon, toast } from "/assets/scripts/dom.js";
import { api, emit, state } from "/assets/scripts/state.js";
import { createHero, statusOf } from "./activity_hero.js";
import { openConsole } from "./console_session.js";
import { markStale } from "./data.js";
import { burst, replay } from "./motion.js";
import { confirmAction } from "./overlays.js";
import { emojiTile, iconButton } from "./widgets.js";
import { fullTitleOf } from "./words.js";

function describeArguments(runArguments) {
  for (let length = runArguments.length; length > 0; length -= 1) {
    const node = state.nodes.get(runArguments.slice(0, length).join(" "));
    if (node) return { title: fullTitleOf(node), emoji: node.icon };
  }
  return { title: "Task", emoji: "" };
}

export function createActivity({ openReport }) {
  const tasks = new Map();
  let activeId = null;
  const chips = h("div", { class: "task-chips", role: "tablist" });
  const hero = createHero({
    openReport,
    runAgain: (task) => start({ title: task.title, emoji: task.emoji, arguments: task.summary.arguments, interactive: task.summary.interactive, reveal: true, workingDirectory: task.summary.working_directory }).catch((error) => toast(error.message)),
  });
  const consoles = h("div", { class: "task-consoles" });
  const sizeButton = iconButton("expand", "Fill the window", () => setMode(element.dataset.mode === "max" ? "open" : "max"));
  const clearButton = iconButton("trash", "Clear finished tasks", () => remove(...visible().filter((task) => task.summary.exit_code !== null).map((task) => task.id)));
  const element = h(
    "aside",
    { class: "activity", "data-mode": "closed", "aria-label": "Activity", inert: true },
    h("header", { class: "activity-head" }, h("h2", { text: "Activity" }), h("span", { class: "spacer" }), clearButton, sizeButton, iconButton("close", "Hide activity", () => setMode("closed"))),
    chips,
    hero.element,
    consoles,
  );
  const pillGlyph = h("span", { class: "activity-glyph" });
  const pillLabel = h("span");
  const indicator = h("button", { class: "activity-pill", type: "button", title: "Show what is running", onclick: () => setMode(element.dataset.mode === "closed" ? "open" : "closed") }, pillGlyph, pillLabel);

  const visible = () => [...tasks.values()].filter((task) => !task.quiet);

  function fit(task) {
    if (!task?.fit || consoles.clientHeight < 40 || !task.fit.proposeDimensions()) return false;
    task.fit.fit();
    return true;
  }

  function setMode(mode) {
    element.dataset.mode = mode;
    element.inert = mode === "closed";
    sizeButton.replaceChildren(icon(mode === "max" ? "shrink" : "expand", 16));
    sizeButton.title = mode === "max" ? "Back to the usual size" : "Fill the window";
    sizeButton.setAttribute("aria-label", sizeButton.title);
    activate(activeId);
  }

  function paint() {
    const shown = visible();
    for (const task of tasks.values()) {
      task.chip.hidden = task.quiet;
      task.tab.setAttribute("aria-selected", String(task.id === activeId));
      task.chip.dataset.status = statusOf(task.summary);
      task.pane.classList.toggle("active", task.id === activeId);
    }
    const running = shown.filter((task) => task.summary.exit_code === null).length;
    clearButton.hidden = running === shown.length;
    pillGlyph.replaceChildren(running ? h("i", { class: "ring" }) : icon("bolt", 15));
    pillLabel.textContent = running ? `${running} running` : "Activity";
    indicator.classList.toggle("busy", running > 0);
    indicator.dataset.count = shown.length ? String(shown.length) : "";
    hero.paint(tasks.get(activeId));
  }

  function activate(id) {
    activeId = id;
    paint();
    const task = tasks.get(id);
    if (!task || element.dataset.mode === "closed") return;
    // A finished run's console is built only once someone looks at it: after a reload there can be many, each a terminal and a connection.
    if (!task.linked) connect(task);
    // The first console of a page is still loading at this point, so the wish to type into it is noted and `connect` honours it.
    requestAnimationFrame(() => {
      if (fit(task)) task.terminal.focus();
      else if (!task.terminal) task.focusWanted = true;
    });
  }

  async function connect(task) {
    task.linked = true;
    const session = await openConsole({
      pane: task.pane, runId: task.id, echo: false, fitNow: () => fit(task),
      onSummary: (summary) => {
        const wasRunning = task.summary.exit_code === null;
        Object.assign(task.summary, summary);
        paint();
        task.settle(task.summary);
        emit("runs");
        if (!wasRunning || task.quiet) return;
        markStale();
        const status = statusOf(task.summary);
        if (element.dataset.mode === "closed") toast(`${task.title} ${{ done: "finished", stopped: "stopped", failed: "stopped with a problem" }[status]}.`, status === "failed" ? "error" : "info");
        else if (status === "done" && task.id === activeId) burst(hero.element.querySelector(".task-mark"));
        replay(indicator, "pulse");
      },
      // A running task's connection lost to sleep or a network blip is reopened, and the server replays the output. Not exhaustive by choice:
      // after five failed tries in a row the task is given up on. It keeps showing as running, because how it went is not known, but whatever
      // waits for it is told it did not succeed, and a reload catches up. A finished run that cannot be read is one the server let go of.
      onDrop: () => {
        if (!tasks.has(task.id)) return;
        task.terminal.dispose();
        Object.assign(task, { terminal: null, fit: null, socket: null });
        if (task.summary.exit_code !== null) task.pane.replaceChildren(h("p", { class: "console-error", text: "This task's output is no longer kept: only the most recent finished tasks are. Reload the page to see what is." }));
        else if ((task.drops += 1) <= 5) setTimeout(() => tasks.has(task.id) && connect(task), 2000 * task.drops);
        else {
          task.pane.replaceChildren(h("p", { class: "console-error", text: "The live view lost its connection. Reload the page to pick this task up again." }));
          task.settle({ ...task.summary, exit_code: -1, finished_at: Date.now() / 1000 });
        }
      },
    });
    if (!session) return;
    Object.assign(task, session);
    // A connection that delivers anything was a good one, so the next drop starts counting from one again.
    session.socket.addEventListener("message", () => (task.drops = 0), { once: true });
    if (task.id === activeId && fit(task) && task.focusWanted) task.terminal.focus();
    task.focusWanted = false;
  }

  function createTask(summary, { title, emoji, quiet }) {
    const pane = h("div", { class: "console" });
    // The chip holds two buttons side by side, the tab and its remove control, so that both can be reached and pressed from the keyboard.
    const tab = h("button", { class: "chip-tab", type: "button", role: "tab", onclick: () => activate(summary.id) }, h("i", { class: "dot" }), h("span", { text: title }));
    const closer = h("button", { class: "chip-close", type: "button", title: "Remove", "aria-label": `Remove ${title}` }, icon("close", 11));
    const chip = h("div", { class: "task-chip", role: "presentation" }, tab, closer);
    let settle;
    const done = new Promise((resolve) => (settle = resolve));
    const task = { id: summary.id, summary, title, emoji, quiet, pane, chip, tab, done, settle, linked: false, focusWanted: false, drops: 0, terminal: null, fit: null, socket: null };
    closer.addEventListener("click", async () => {
      // Removing a run that is still going stops it on the server, so that takes a yes first.
      const sure = task.summary.exit_code !== null || (await confirmAction({ title: `Stop “${title}”?`, body: "It is still running. Removing it stops it.", confirm: "Stop and remove", tone: "danger" }));
      if (sure) remove(task.id);
    });
    tasks.set(task.id, task);
    chips.append(chip);
    consoles.append(pane);
    // A running task connects at once, open panel or not: the connection is how the app learns that it ended.
    if (summary.exit_code === null) connect(task);
    else settle(summary);
    return task;
  }

  async function remove(...ids) {
    const gone = ids.map((id) => tasks.get(id)).filter(Boolean);
    if (!gone.length) return;
    await Promise.all(gone.map((task) => api.deleteRun(task.id).catch((error) => toast(error.message))));
    for (const task of gone) {
      // Removing a running task stops it, and its connection is closed here before the end can be reported: whatever waits for it is told now.
      if (task.summary.exit_code === null) task.settle({ ...task.summary, exit_code: -1, stopped: true, finished_at: Date.now() / 1000 });
      task.socket?.close();
      task.terminal?.dispose();
      task.chip.remove();
      task.pane.remove();
      tasks.delete(task.id);
    }
    // Only taking away the task on show moves on to another and gives it the keyboard: a background run tidied away must not pull focus from the page.
    if (tasks.has(activeId)) paint();
    else activate(visible().at(-1)?.id ?? null);
    emit("runs");
  }

  function reveal(id) {
    const task = tasks.get(id);
    if (!task) return;
    task.quiet = false;
    activeId = id;
    if (element.dataset.mode === "closed") setMode("open");
    else activate(id);
    emit("runs");
  }

  // `workingDirectory` is only given by "Run again", which repeats a task in the folder it ran in; everything else runs in the folder selected now.
  async function start({ title, emoji, arguments: runArguments, interactive, reveal: show, wide, workingDirectory }) {
    const fitted = tasks.get(activeId);
    const width = Math.min(element.offsetWidth || 760, window.innerWidth);
    const size = fitted?.terminal && fit(fitted) ? { rows: fitted.terminal.rows, columns: fitted.terminal.cols } : { rows: 28, columns: Math.max(60, Math.floor((width - 64) / 7.85)) };
    const summary = await api.startRun({ arguments: runArguments, working_directory: workingDirectory ?? state.settings.workingDirectory, interactive, ...size });
    const described = describeArguments(runArguments);
    const task = createTask(summary, { title: title ?? described.title, emoji: emoji ?? described.emoji, quiet: !show });
    if (show) reveal(task.id);
    else paint();
    if (wide) setMode("max");
    emit("runs");
    return task;
  }

  async function restore() {
    const { runs } = await api.runs();
    for (const run of runs) createTask(run, { ...describeArguments(run.arguments), quiet: false });
    if (runs.length) activate(runs.at(-1).id);
    emit("runs");
  }

  setInterval(() => element.dataset.mode !== "closed" && hero.tick(), 1000);
  // Only the task on show is refitted, once the size settles: each refit re-wraps the console and resizes the program. The others catch up when selected.
  new ResizeObserver(debounce(() => fit(tasks.get(activeId)), 120)).observe(consoles);
  paint();

  return {
    element, indicator, start, restore, reveal, remove,
    runs: () => visible().map((task) => ({ ...task.summary, title: task.title, emoji: task.emoji, tile: emojiTile(task.emoji || "✨", task.title, 34) })),
  };
}
