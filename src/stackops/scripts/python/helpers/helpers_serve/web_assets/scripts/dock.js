import { formatDuration, h, icon, tildify, toast } from "./dom.js";
import { TERMINAL_THEME } from "./presets.js";
import { api, emit, setSetting, state } from "./state.js";

const TERMINAL_FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", monospace';
let terminalLibrary = null;

function loadTerminalLibrary() {
  terminalLibrary ??= Promise.all([import("/vendor/xterm.mjs"), import("/vendor/addon-fit.mjs")]).then(([terminal, fit]) => ({ Terminal: terminal.Terminal, FitAddon: fit.FitAddon }));
  return terminalLibrary;
}

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
    start({ arguments: summary.arguments, interactive: summary.interactive, reveal: true }).catch((error) => toast(error.message));
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
    if (!tab.fit || body.clientHeight < 40 || !tab.fit.proposeDimensions()) return false;
    tab.fit.fit();
    return true;
  }

  function setMode(mode) {
    element.dataset.mode = mode;
    element.style.setProperty("--dock-height", `${state.settings.dockHeight}px`);
    sizeButton.replaceChildren(icon(mode === "max" ? "shrink" : "expand", 14));
    foldButton.replaceChildren(icon(mode === "collapsed" ? "up" : "down", 15));
    sizeButton.hidden = mode === "collapsed";
    requestAnimationFrame(() => tabs.forEach(fit));
  }

  function paint() {
    const visible = [...tabs.values()].filter((tab) => !tab.quiet);
    element.hidden = visible.length === 0;
    for (const tab of tabs.values()) {
      tab.button.hidden = tab.quiet;
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
    requestAnimationFrame(() => {
      const tab = tabs.get(id);
      if (tab && fit(tab)) tab.terminal.focus();
    });
  }

  async function connect(tab) {
    let library;
    try {
      library = await loadTerminalLibrary();
    } catch {
      terminalLibrary = null;
      tab.pane.replaceChildren(h("p", { class: "dock-error", text: "The terminal could not be loaded. Its library is downloaded once, on first use: check the connection, then reload this page." }));
      return;
    }
    const background = getComputedStyle(document.documentElement).getPropertyValue("--terminal").trim();
    const terminal = new library.Terminal({ fontFamily: TERMINAL_FONT, fontSize: 13, lineHeight: 1.2, cursorBlink: true, scrollback: 20000, theme: { ...TERMINAL_THEME, background } });
    Object.assign(tab, { terminal, fit: new library.FitAddon() });
    terminal.loadAddon(tab.fit);
    terminal.open(tab.pane);
    const socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/runs/${tab.id}`);
    socket.binaryType = "arraybuffer";
    const send = (message) => socket.readyState === WebSocket.OPEN && socket.send(JSON.stringify(message));
    socket.addEventListener("open", () => fit(tab) && send({ type: "resize", rows: terminal.rows, columns: terminal.cols }));
    socket.addEventListener("message", (event) => {
      if (typeof event.data !== "string") return terminal.write(new Uint8Array(event.data));
      Object.assign(tab.summary, JSON.parse(event.data));
      terminal.write("\x1b[?25l");
      terminal.options.disableStdin = true;
      paint();
      tab.settle(tab.summary);
      emit("runs");
    });
    terminal.onData((data) => send({ type: "input", data }));
    terminal.onResize(({ rows, cols }) => send({ type: "resize", rows, columns: cols }));
    tab.socket = socket;
    if (tab.id === activeId && fit(tab)) terminal.focus();
  }

  function createTab(summary, quiet) {
    const pane = h("div", { class: "dock-pane" });
    const glyph = h("span");
    const closer = h("span", { class: "close", role: "button", title: "Close" }, icon("close", 12));
    const label = h("span", { class: "label", text: summary.command_line.replace(/^stackops /, "") });
    const button = h("button", { class: "dock-tab", role: "tab", title: `${summary.command_line}\nin ${summary.working_directory}` }, glyph, label, closer);
    let settle;
    const done = new Promise((resolve) => (settle = resolve));
    const tab = { id: summary.id, summary, quiet, pane, glyph, button, done, settle, terminal: null, fit: null, socket: null };
    button.addEventListener("click", (event) => (closer.contains(event.target) ? close(tab.id, true) : focus(tab.id)));
    tabs.set(tab.id, tab);
    strip.append(button);
    body.append(pane);
    connect(tab);
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
    tab.socket?.close();
    tab.terminal?.dispose();
    tab.button.remove();
    tab.pane.remove();
    tabs.delete(id);
    if (activeId === id) activeId = [...tabs.values()].filter((other) => !other.quiet).at(-1)?.id ?? null;
    activate(activeId);
    emit("runs");
  }

  function focus(id) {
    const tab = tabs.get(id);
    if (!tab) return;
    tab.quiet = false;
    if (element.dataset.mode === "collapsed") setMode("open");
    activate(id);
    emit("runs");
  }

  async function start({ arguments: runArguments, interactive, reveal }) {
    const shown = tabs.get(activeId);
    const size = shown?.terminal && fit(shown)
      ? { rows: shown.terminal.rows, columns: shown.terminal.cols }
      : { rows: Math.max(12, Math.floor((state.settings.dockHeight - 52) / 17)), columns: Math.max(60, Math.floor((window.innerWidth - 300) / 7.85)) };
    const summary = await api.startRun({ arguments: runArguments, working_directory: state.settings.workingDirectory, interactive, ...size });
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
  new ResizeObserver(() => requestAnimationFrame(() => tabs.forEach(fit))).observe(body);
  setMode("collapsed");

  return { element, start, focus, close: (id) => close(id, false), toggle, restore, runs: () => [...tabs.values()].filter((tab) => !tab.quiet).map((tab) => tab.summary) };
}
