import { openConsole } from "/assets/app/scripts/console_session.js";
import { debounce, formatDuration, h, icon, tildify, toast } from "./dom.js";
import { api, emit, setSetting, state } from "./state.js";

export function statusGlyph(run) {
  if (run.exit_code === null) return h("span", { class: "status", title: "Running" }, h("span", { class: "spinner" }));
  if (run.exit_code === 0) return h("span", { class: "status ok", title: "Finished" }, icon("check", 14));
  return h("span", { class: "status failed", title: `Exited with code ${run.exit_code}` }, icon("alert", 14));
}

export function createDock() {
  const tabs = new Map();
  let activeId = null;
  const strip = h("div", { class: "dock-tabs", role: "tablist" });
  const body = h("div", { class: "dock-body" });
  const meta = h("span", { class: "dock-meta" });
  const control = (label, onclick) => h("button", { class: "icon-button", title: label, "aria-label": label, onclick });
  const stopButton = control("Stop this command", () => api.stopRun(activeId).catch((error) => toast(error.message)));
  const rerunButton = control("Run it again", () => {
    const { summary } = tabs.get(activeId);
    start({ arguments: summary.arguments, interactive: summary.interactive, reveal: true, workingDirectory: summary.working_directory }).catch((error) => toast(error.message));
  });
  const sizeButton = control("Fill the window", () => setMode(element.dataset.mode === "max" ? "open" : "max"));
  const foldButton = control("Hide the terminal", () => setMode(element.dataset.mode === "collapsed" ? "open" : "collapsed"));
  const resizer = h("div", { class: "dock-resizer" });
  const element = h(
    "section",
    { class: "dock", hidden: true, "data-mode": "collapsed", "aria-label": "Terminal dock" },
    resizer,
    h("div", { class: "dock-head" }, strip, meta, stopButton, rerunButton, sizeButton, foldButton),
    body,
  );
  stopButton.append(icon("stop", 14));
  rerunButton.append(icon("refresh", 14));

  function fit(tab) {
    if (!tab?.fit || body.clientHeight < 40 || !tab.fit.proposeDimensions()) return false;
    tab.fit.fit();
    return true;
  }

  function setMode(mode) {
    element.dataset.mode = mode;
    element.style.setProperty("--dock-height", `${state.settings.dockHeight}px`);
    sizeButton.replaceChildren(icon(mode === "max" ? "shrink" : "expand", 14));
    foldButton.replaceChildren(icon(mode === "collapsed" ? "up" : "down", 15));
    for (const [button, label] of [[sizeButton, mode === "max" ? "Back to the usual size" : "Fill the window"], [foldButton, mode === "collapsed" ? "Show the terminal" : "Hide the terminal"]]) {
      button.title = label;
      button.setAttribute("aria-label", label);
    }
    sizeButton.hidden = mode === "collapsed";
    activate(activeId);
  }

  function paint() {
    const visible = [...tabs.values()].filter((tab) => !tab.quiet);
    element.hidden = visible.length === 0;
    for (const tab of tabs.values()) {
      tab.chip.hidden = tab.quiet;
      tab.button.setAttribute("aria-selected", String(tab.id === activeId));
      tab.pane.classList.toggle("active", tab.id === activeId);
      tab.glyph.replaceChildren(statusGlyph(tab.summary));
    }
    const active = tabs.get(activeId);
    stopButton.hidden = !active || active.summary.exit_code !== null;
    rerunButton.hidden = !active;
    if (!active) meta.textContent = "";
    else if (active.summary.exit_code === null) meta.textContent = `running in ${tildify(active.summary.working_directory, state.boot.home)}`;
    else meta.textContent = `${active.summary.exit_code === 0 ? "done" : `exit ${active.summary.exit_code}`} · ${formatDuration(active.summary.finished_at - active.summary.started_at)}`;
  }

  function activate(id) {
    activeId = id;
    paint();
    const tab = tabs.get(id);
    if (!tab || element.dataset.mode === "collapsed") return;
    // A finished run's terminal is built only once its tab is shown: after a reload there can be twenty, each a terminal and a connection.
    if (!tab.linked) connect(tab);
    requestAnimationFrame(() => fit(tab) && tab.terminal.focus());
  }

  // The terminal and its connection are the app view's, with the command line kept as the first line of the output.
  async function connect(tab) {
    tab.linked = true;
    const session = await openConsole({
      pane: tab.pane, runId: tab.id, echo: true, fitNow: () => fit(tab),
      onSummary: (summary) => {
        Object.assign(tab.summary, summary);
        paint();
        tab.settle(tab.summary);
        emit("runs");
      },
      // Design choice: unlike the app view, a lost connection is not reopened here. The tab says so, whatever waits for the command is told it
      // did not succeed, and a reload picks a running command up again. A finished run that cannot be read is one the server let go of.
      onDrop: () => {
        if (!tabs.has(tab.id)) return;
        tab.terminal.dispose();
        Object.assign(tab, { terminal: null, fit: null, socket: null });
        const running = tab.summary.exit_code === null;
        tab.pane.replaceChildren(h("p", { class: "console-error", text: running ? "The connection to this command was lost. Reload the page to pick it up again." : "This command's output is no longer kept: only the most recent finished runs are." }));
        if (running) tab.settle({ ...tab.summary, exit_code: -1, finished_at: Date.now() / 1000 });
      },
    });
    if (!session) return;
    Object.assign(tab, session);
    if (tab.id === activeId && fit(tab)) tab.terminal.focus();
  }

  function createTab(summary, quiet) {
    const pane = h("div", { class: "dock-pane" });
    const glyph = h("span");
    const label = summary.command_line.replace(/^stackops /, "");
    // The tab and its closer are two buttons side by side, so that both can be reached and pressed from the keyboard.
    const button = h("button", { class: "dock-tab-button", role: "tab", title: `${summary.command_line}\nin ${summary.working_directory}`, onclick: () => focus(summary.id) }, glyph, h("span", { class: "label", text: label }));
    const closer = h("button", { class: "close", title: "Close", "aria-label": `Close ${label}`, onclick: () => close(summary.id, true) }, icon("close", 12));
    const chip = h("div", { class: "dock-tab", role: "presentation" }, button, closer);
    let settle;
    const done = new Promise((resolve) => (settle = resolve));
    const tab = { id: summary.id, summary, quiet, pane, glyph, chip, button, done, settle, linked: false, terminal: null, fit: null, socket: null };
    tabs.set(tab.id, tab);
    strip.append(chip);
    body.append(pane);
    // A running command connects at once, shown or not: the connection is how the page learns that it ended.
    if (summary.exit_code === null) connect(tab);
    else settle(summary);
    return tab;
  }

  async function close(id, confirmStop) {
    const tab = tabs.get(id);
    if (!tab) return;
    if (confirmStop && tab.summary.exit_code === null && !confirm("This command is still running. Stop it and close its tab?")) return;
    try {
      await api.deleteRun(id);
    } catch (error) {
      toast(error.message);
    }
    // Closing a running command stops it, and its connection is closed here before the end can be reported: whatever waits for it is told now.
    if (tab.summary.exit_code === null) tab.settle({ ...tab.summary, exit_code: -1, stopped: true, finished_at: Date.now() / 1000 });
    tab.socket?.close();
    tab.terminal?.dispose();
    tab.chip.remove();
    tab.pane.remove();
    tabs.delete(id);
    // Only closing the tab on show moves on to another and gives it the keyboard: a background report tidied away must not pull focus from the page.
    if (activeId === id) activate([...tabs.values()].filter((other) => !other.quiet).at(-1)?.id ?? null);
    else paint();
    emit("runs");
  }

  function focus(id) {
    const tab = tabs.get(id);
    if (!tab) return;
    tab.quiet = false;
    activeId = id;
    if (element.dataset.mode === "collapsed") setMode("open");
    else activate(id);
    emit("runs");
  }

  // `workingDirectory` is only given by "Run it again", which repeats a command in the folder it ran in; everything else runs in the folder selected now.
  async function start({ arguments: runArguments, interactive, reveal, workingDirectory }) {
    const shown = tabs.get(activeId);
    const size = shown?.terminal && fit(shown)
      ? { rows: shown.terminal.rows, columns: shown.terminal.cols }
      : { rows: Math.max(12, Math.floor((state.settings.dockHeight - 52) / 17)), columns: Math.max(60, Math.floor((window.innerWidth - 300) / 7.85)) };
    const summary = await api.startRun({ arguments: runArguments, working_directory: workingDirectory ?? state.settings.workingDirectory, interactive, ...size });
    const tab = createTab(summary, !reveal);
    if (reveal) focus(tab.id);
    else paint();
    emit("runs");
    return tab;
  }

  async function restore() {
    const { runs } = await api.runs();
    for (const run of runs) createTab(run, false);
    if (runs.length) activate(runs.at(-1).id);
    emit("runs");
  }

  function toggle() {
    if (element.hidden) toast("Nothing has run in this session yet.", "info");
    else setMode(element.dataset.mode === "collapsed" ? "open" : "collapsed");
  }

  resizer.addEventListener("pointerdown", (event) => {
    resizer.setPointerCapture(event.pointerId);
    resizer.classList.add("dragging");
    const move = (moveEvent) => {
      state.settings.dockHeight = Math.round(Math.min(Math.max(window.innerHeight - moveEvent.clientY, 140), window.innerHeight - 140));
      element.style.setProperty("--dock-height", `${state.settings.dockHeight}px`);
    };
    const release = () => {
      resizer.classList.remove("dragging");
      resizer.removeEventListener("pointermove", move);
      setSetting("dockHeight", state.settings.dockHeight);
    };
    resizer.addEventListener("pointermove", move);
    resizer.addEventListener("pointerup", release, { once: true });
  });
  // Only the tab on show is refitted, once the size settles: each refit re-wraps the terminal and resizes the program. The others catch up when shown.
  new ResizeObserver(debounce(() => fit(tabs.get(activeId)), 120)).observe(body);
  setMode("collapsed");

  return { element, start, focus, close: (id) => close(id, false), toggle, restore, runs: () => [...tabs.values()].filter((tab) => !tab.quiet).map((tab) => tab.summary) };
}
