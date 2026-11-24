import { h, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { confirmAction, openDialog } from "./overlays.js";
import { button, pill } from "./widgets.js";

// How long an editor gets to act on a key before it counts as still open.
const CLOSE_WAIT_MILLISECONDS = 1500;
// Escape, twice. Helix reads Escape followed at once by another key as Alt with that key, and two Escape bytes as one press, so each press goes
// out as two bytes. The second press is for a menu that takes the first one for itself. Left in typing, Helix would put the command into the file.
const ESCAPE = "\x1b\x1b\x1b\x1b";
// The editors the CLI runs inside the console, by the word `--editor` takes, with the keys that ask each one for something. An editor closes on
// `close` only while nothing is unsaved. nano then asks in its own last lines, so it has no other keys here. VS Code is left out: it opens in a
// window of its own and the run only waits for it, so stopping that run loses nothing.
const EDITORS = {
  hx: { close: `${ESCAPE}:qa\r`, save: `${ESCAPE}:w\r`, saveAndClose: `${ESCAPE}:wqa\r`, discard: `${ESCAPE}:qa!\r` },
  nano: { close: "\x18" },
};
const UNREACHABLE = "The editor cannot be reached right now. Try again in a moment.";
const STILL_OPEN = "The editor is still open, so the file may not be saved. Its last line says why.";

const running = (task) => task.summary.exit_code === null;
// An editor takes over the whole console while it is open, which the console knows as its second screen. Not exact after a reload of a very long
// session: the server keeps a limited stretch of output, and once the switch has dropped out of it an open editor reads as not on screen.
const onScreen = (task) => task?.terminal?.buffer.active.type === "alternate";

// Which editor a run has in the console, or null for any other run. Read from the arguments, since they are all that is known of a run restored
// after a reload. Design choice: an edit command is known by its name in the command tree, where every `edit` opens the CLI's editor, and that
// is Helix unless `--editor` names another. Listing the commands instead would leave a new one with Stop, which loses unsaved work.
export function editorOf(runArguments) {
  const length = runArguments.findLastIndex((_, index) => state.nodes.has(runArguments.slice(0, index + 1).join(" "))) + 1;
  const node = state.nodes.get(runArguments.slice(0, length).join(" "));
  if (node?.kind !== "command" || node.name !== "edit") return null;
  let editor = "hx";
  runArguments.slice(length).forEach((token, index, rest) => {
    if (token === "--editor" || token === "-e") editor = rest[index + 1];
    else if (token.startsWith("--editor=")) editor = token.slice("--editor=".length);
  });
  return Object.hasOwn(EDITORS, editor) ? editor : null;
}

// Resolves to whether the editor left the screen, or its run ended, in the time it is given.
function left(task) {
  return new Promise((resolve) => {
    const finish = (answer) => {
      watch.dispose();
      clearTimeout(timer);
      resolve(answer);
    };
    const watch = task.terminal.buffer.onBufferChange((buffer) => buffer.type === "normal" && finish(true));
    const timer = setTimeout(() => finish(false), CLOSE_WAIT_MILLISECONDS);
    task.done.then(() => finish(true));
  });
}

// Presses the keys that save and then close, and says whether the editor closed. It stays open when it could not write the file.
async function saveAndClose(task) {
  if (!task.type?.(EDITORS[task.editor].saveAndClose)) {
    toast(UNREACHABLE);
    return false;
  }
  if (await left(task)) return true;
  toast(STILL_OPEN);
  task.terminal?.focus();
  return false;
}

function askAboutUnsaved() {
  const dialog = openDialog({ label: "Save before closing?", size: "small editor-ask" });
  dialog.body.append(
    h("h2", { text: "Save before closing?" }),
    h("p", { text: "The editor is still open. It stays open while a change is not saved." }),
    h(
      "div",
      { class: "dialog-actions" },
      button({ label: "Keep editing", onclick: () => dialog.close("stay") }),
      button({ label: "Close without saving", tone: "danger", onclick: () => dialog.close("discard") }),
      button({ label: "Save and close", tone: "primary", onclick: () => dialog.close("save") }),
    ),
  );
  return dialog.closed;
}

async function attemptClose(task) {
  const keys = EDITORS[task.editor];
  const stop = () => api.stopRun(task.id).catch((error) => toast(error.message));
  // An editor that is not on screen (still starting, or already gone) or is out of reach cannot be asked, so the person is.
  if (!onScreen(task) || !task.type?.(keys.close)) {
    const why = task.terminal && !onScreen(task) ? "is not on screen" : "cannot be reached";
    const sure = await confirmAction({
      title: "Stop the editor?", body: `The editor ${why} right now, so it cannot be asked to save. Stopping it loses any change that is not saved.`, confirm: "Stop the editor", tone: "danger",
    });
    if (sure && running(task)) await stop();
    return sure;
  }
  if (await left(task)) return true;
  if (!keys.discard) {
    toast("The editor is asking whether to save first. Answer it there with Y or N.", "info");
    task.terminal?.focus();
    return false;
  }
  const answer = await askAboutUnsaved();
  if (!running(task)) return true;
  if (answer === "save") return saveAndClose(task);
  if (answer === "discard") {
    // The person has agreed to lose the changes, so an editor that does not take the keys is stopped.
    if (!(task.type?.(keys.discard) && (await left(task)))) await stop();
    return true;
  }
  task.terminal?.focus();
  return false;
}

// Closes a running editor without losing work: the editor is asked to quit, which it does only when nothing is unsaved, and the person chooses
// when something is. Resolves to whether the editor is closed, or on its way out. A second press while one is under way joins it.
export function closeEditor(task) {
  task.closing ??= attemptClose(task).finally(() => (task.closing = null));
  return task.closing;
}

// The strip between a running editor's header and its console, for someone who has not used an editor where keys are commands until typing is
// switched on. Its buttons press the keys in the console for the person. Only Helix has one: nano takes typing as it comes and lists its own keys.
export function createEditorBar() {
  let shown = null;
  let watched = null;
  let watch = null;
  // Each button with what its tooltip says while it can be pressed.
  const controls = [
    [button({ label: "Save", glyph: "check", small: true, onclick: () => (shown.type?.(EDITORS.hx.save) ? shown.terminal.focus() : toast(UNREACHABLE)) }), "Writes the file and keeps the editor open. By hand: Esc, then :w and Enter."],
    [button({ label: "Save and close", small: true, tone: "primary", onclick: () => saveAndClose(shown) }), "Writes the file and closes the editor. By hand: Esc, then :wq and Enter."],
  ];
  const key = (text) => h("kbd", { text });
  const element = h(
    "div",
    { class: "editor-bar", hidden: true },
    pill("Helix", "accent"),
    h("p", {}, "Press ", key("i"), " to type and ", key("Esc"), " when done. If keys do something odd, press ", key("Esc"), ", then ", key("u"), " to undo."),
    h("div", { class: "task-actions" }, controls.map(([control]) => control)),
  );
  function refresh() {
    const ready = onScreen(shown);
    for (const [control, says] of controls) {
      control.disabled = !ready;
      control.title = ready ? says : "Works while the editor is on screen.";
    }
  }

  // Called with the task on show whenever that changes, and when its console connects: the buttons only work while the editor is on screen.
  function paint(task) {
    shown = task?.editor === "hx" && running(task) ? task : null;
    element.hidden = !shown;
    const terminal = shown?.terminal ?? null;
    if (terminal !== watched) {
      watch?.dispose();
      watch = terminal?.buffer.onBufferChange(refresh) ?? null;
      watched = terminal;
    }
    refresh();
  }

  return { element, paint };
}
