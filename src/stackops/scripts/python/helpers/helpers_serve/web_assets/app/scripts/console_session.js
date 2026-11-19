import { h } from "/assets/scripts/dom.js";
import { TERMINAL_THEME } from "/assets/scripts/presets.js";

const TERMINAL_FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", monospace';
const CONSOLE_BACKGROUND = "#0b0c16";
const ECHO_PREFIX = [0x1b, 0x5b, 0x32, 0x6d, 0x24, 0x20];
let terminalLibrary = null;

function loadTerminalLibrary() {
  terminalLibrary ??= Promise.all([import("/vendor/xterm.mjs"), import("/vendor/addon-fit.mjs")]).then(([terminal, fit]) => ({ Terminal: terminal.Terminal, FitAddon: fit.FitAddon }));
  return terminalLibrary;
}

// Every run's output opens with a dimmed echo of its command line; the app view names the task instead.
function withoutCommandEcho(bytes) {
  const lineEnd = bytes.indexOf(0x0a);
  return ECHO_PREFIX.every((byte, index) => bytes[index] === byte) && lineEnd > 0 ? bytes.subarray(lineEnd + 1) : bytes;
}

// Shows one run live inside `pane` and forwards typing to it. `fitNow` sizes the console to its pane; `onSummary` gets the run's final state.
export async function openConsole({ pane, runId, fitNow, onSummary }) {
  let library;
  try {
    library = await loadTerminalLibrary();
  } catch {
    terminalLibrary = null;
    pane.replaceChildren(h("p", { class: "console-error", text: "The live view could not be loaded. It is downloaded once, on first use: check the connection, then reload this page." }));
    return null;
  }
  const terminal = new library.Terminal({ fontFamily: TERMINAL_FONT, fontSize: 13, lineHeight: 1.25, cursorBlink: true, scrollback: 20000, theme: { ...TERMINAL_THEME, background: CONSOLE_BACKGROUND } });
  const fit = new library.FitAddon();
  terminal.loadAddon(fit);
  terminal.open(pane);
  const socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/runs/${runId}`);
  socket.binaryType = "arraybuffer";
  const send = (message) => socket.readyState === WebSocket.OPEN && socket.send(JSON.stringify(message));
  let first = true;
  socket.addEventListener("open", () => fitNow() && send({ type: "resize", rows: terminal.rows, columns: terminal.cols }));
  socket.addEventListener("message", (event) => {
    if (typeof event.data !== "string") {
      const bytes = new Uint8Array(event.data);
      terminal.write(first ? withoutCommandEcho(bytes) : bytes);
      first = false;
      return;
    }
    terminal.write("\x1b[?25l");
    terminal.options.disableStdin = true;
    onSummary(JSON.parse(event.data));
  });
  terminal.onData((data) => send({ type: "input", data }));
  terminal.onResize(({ rows, cols }) => send({ type: "resize", rows, columns: cols }));
  return { terminal, fit, socket };
}
