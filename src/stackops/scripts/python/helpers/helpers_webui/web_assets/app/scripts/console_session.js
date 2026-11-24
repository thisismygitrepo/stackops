import { h } from "/assets/scripts/dom.js";
import { TERMINAL_THEME } from "/assets/scripts/presets.js";

const TERMINAL_FONT = 'ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", monospace';
const TERMINAL_STYLES = "/vendor/xterm.css";
const ECHO_PREFIX = [0x1b, 0x5b, 0x32, 0x6d, 0x24, 0x20];
const LINK_PATTERN = /https?:\/\/[^\s"'<>]+[^\s"'<>.,;:!?)\]]/g;
let terminalLibrary = null;

// The terminal's stylesheet is fetched with its library, on first use, so that no page waits for it before its first paint.
function loadTerminalStyles() {
  if (document.querySelector(`link[href="${TERMINAL_STYLES}"]`)) return null;
  return new Promise((resolve, reject) => {
    const link = h("link", { rel: "stylesheet", href: TERMINAL_STYLES, onload: resolve });
    // A link that failed is taken out again, so the next console to open asks for the styles afresh.
    link.addEventListener("error", () => {
      link.remove();
      reject(new Error("The terminal styles did not load."));
    });
    document.head.append(link);
  });
}

function loadTerminalLibrary() {
  terminalLibrary ??= Promise.all([import("/vendor/xterm.mjs"), import("/vendor/addon-fit.mjs"), loadTerminalStyles()]).then(([terminal, fit]) => ({ Terminal: terminal.Terminal, FitAddon: fit.FitAddon }));
  return terminalLibrary;
}

// Every run's output opens with a dimmed echo of its command line; the app view names the task instead, the developer view keeps the line.
function withoutCommandEcho(bytes) {
  const lineEnd = bytes.indexOf(0x0a);
  return ECHO_PREFIX.every((byte, index) => bytes[index] === byte) && lineEnd > 0 ? bytes.subarray(lineEnd + 1) : bytes;
}

// Everything the console holds, as text. It goes through the selection because that is what joins wrapped lines; a selection the user had is lost.
export function consoleText(terminal) {
  if (!terminal) return "";
  terminal.selectAll();
  const text = terminal.getSelection().trimEnd();
  terminal.clearSelection();
  return text;
}

// Makes addresses a run prints clickable, including ones wrapped over several lines. Not exact by design: columns are taken from character
// offsets, so a link that follows double-width text on its line is underlined a cell or two off.
function linkProvider(terminal) {
  return {
    provideLinks(row, callback) {
      const buffer = terminal.buffer.active;
      let first = row - 1;
      while (first > 0 && buffer.getLine(first).isWrapped) first -= 1;
      let text = buffer.getLine(first).translateToString(false);
      for (let next = first + 1; buffer.getLine(next)?.isWrapped; next += 1) text += buffer.getLine(next).translateToString(false);
      const place = (offset) => ({ x: (offset % terminal.cols) + 1, y: first + 1 + Math.floor(offset / terminal.cols) });
      const links = [...text.matchAll(LINK_PATTERN)].map((match) => ({
        text: match[0],
        range: { start: place(match.index), end: place(match.index + match[0].length - 1) },
        activate: () => window.open(match[0], "_blank", "noopener"),
      }));
      callback(links.filter((link) => link.range.start.y <= row && row <= link.range.end.y));
    },
  };
}

// Shows one run live inside `pane` and forwards typing to it. Both views use it. `echo` keeps the run's opening line, its command; `fitNow` sizes
// the console to its pane; `onSummary` gets the run's final state; `onDrop` is called when the connection ends before that. The `sendKeys` it
// returns hands keys to the run as if they were typed, for a control that presses them for the person, and says whether they went out.
export async function openConsole({ pane, runId, echo, fitNow, onSummary, onDrop }) {
  let library;
  try {
    library = await loadTerminalLibrary();
  } catch {
    terminalLibrary = null;
    pane.replaceChildren(h("p", { class: "console-error", text: "The live view could not be loaded. It is downloaded once, on first use: check the connection, then reload this page." }));
    return null;
  }
  // The console takes the colour of the box its pane sits in, which each view sets in its stylesheet.
  const background = getComputedStyle(pane.parentElement).backgroundColor;
  const terminal = new library.Terminal({ fontFamily: TERMINAL_FONT, fontSize: 13, lineHeight: 1.25, cursorBlink: true, scrollback: 20000, theme: { ...TERMINAL_THEME, background } });
  const fit = new library.FitAddon();
  terminal.loadAddon(fit);
  terminal.registerLinkProvider(linkProvider(terminal));
  terminal.open(pane);
  const socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/runs/${runId}`);
  socket.binaryType = "arraybuffer";
  const send = (message) => socket.readyState === WebSocket.OPEN && (socket.send(JSON.stringify(message)), true);
  let first = true;
  let ended = false;
  socket.addEventListener("open", () => fitNow() && send({ type: "resize", rows: terminal.rows, columns: terminal.cols }));
  socket.addEventListener("message", (event) => {
    if (typeof event.data !== "string") {
      const bytes = new Uint8Array(event.data);
      terminal.write(first && !echo ? withoutCommandEcho(bytes) : bytes);
      first = false;
      return;
    }
    ended = true;
    terminal.write("\x1b[?25l");
    terminal.options.disableStdin = true;
    onSummary(JSON.parse(event.data));
    // The summary is the last thing a run sends, so the connection has nothing left to carry.
    socket.close();
  });
  socket.addEventListener("close", () => ended || onDrop());
  const sendKeys = (data) => !ended && send({ type: "input", data });
  terminal.onData(sendKeys);
  terminal.onResize(({ rows, cols }) => send({ type: "resize", rows, columns: cols }));
  return { terminal, fit, socket, sendKeys };
}
