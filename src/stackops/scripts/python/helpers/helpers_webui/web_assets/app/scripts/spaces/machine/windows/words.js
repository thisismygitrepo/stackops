export const WINDOWS_PATH = "utils machine window";
export const WINDOWS_HASH = "#/machine/windows";
export const MEMORY_ID = "machine windows";
export const EVERY_APP = "Every app";
// How often the list is read again while the page is in view. One reading takes about a fifth of a second of this machine's time.
export const POLL_MILLISECONDS = 5000;
// How soon after an action the list is read once more, for a change that shows only when the window has finished moving.
export const SETTLE_MILLISECONDS = 1200;
// How long a window gets to close before the page says it is still open.
export const CLOSE_CHECK_MILLISECONDS = 2000;
const NAME_LIMIT = 60;

// Each action the command has: the word on its button, its picture, the button's hint, and the words for a sentence about how it went.
export const ACTIONS = {
  focus: { label: "Bring to front", glyph: "external", hint: "Show this window in front of the others", verb: "bring to the front", done: "brought to the front" },
  minimize: { label: "Minimize", glyph: "down", hint: "Put this window away without closing it", verb: "minimize", done: "minimized" },
  unminimize: { label: "Restore", glyph: "up", hint: "Put this window back on the screen", verb: "restore", done: "restored" },
  maximize: { label: "Maximize", glyph: "expand", hint: "Stretch this window over its screen", verb: "maximize", done: "maximized" },
  close: { label: "Close", glyph: "close", hint: "Close this window. You are asked first.", verb: "close", done: "closed" },
};

export const titleOf = (entry) => entry.title.trim() || "Untitled window";
export const sizeText = (frame) => `${Math.round(frame.width).toLocaleString()} × ${Math.round(frame.height).toLocaleString()}`;

// A window as a sentence names it: its title in quotes, cut to fit, or its app when it has no title. `first` is for the start of a sentence.
function nameOf(entry, first) {
  const title = entry.title.trim();
  if (!title) return `${first ? "An" : "an"} untitled ${entry.app} window`;
  return `"${title.length > NAME_LIMIT ? `${title.slice(0, NAME_LIMIT - 1)}…` : title}"`;
}

// What to say after an action, as [message, tone] pairs. Windows that did as asked are passed over: the list shows it.
export function outcomeNotes(action, targets, results) {
  const named = (result, first) => nameOf(targets.find((entry) => entry.id === result.id), first);
  const failed = results.filter((result) => result.status === "failed");
  const gone = results.filter((result) => result.status === "gone");
  const notes = [];
  if (failed.length === 1) notes.push([`Could not ${ACTIONS[action].verb} ${named(failed[0], false)}. ${failed[0].reason}`, "error"]);
  if (failed.length > 1) notes.push([`${failed.length} of ${results.length} windows could not be ${ACTIONS[action].done}. ${failed[0].reason}`, "error"]);
  if (gone.length === 1) notes.push([`${named(gone[0], true)} was already closed.`, "info"]);
  if (gone.length > 1) notes.push([`${gone.length} windows were already closed.`, "info"]);
  return notes;
}

// A close is a request: the app decides. This is what to say about windows that were asked to close and are still there a moment later.
export function stillOpenNote(entries) {
  if (entries.length === 0) return "";
  const apps = [...new Set(entries.map((entry) => entry.app))];
  const who = apps.length === 1 ? apps[0] : "Their apps";
  return `${entries.length === 1 ? `${nameOf(entries[0], true)} is` : `${entries.length} windows are`} still open. ${who} may be asking what to do with unsaved changes.`;
}
