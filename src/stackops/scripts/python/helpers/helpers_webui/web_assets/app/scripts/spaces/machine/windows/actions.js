import { toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../../agent_ask.js";
import { windowsApi } from "./api.js";
import { confirmClose } from "./confirm.js";
import { CLOSE_CHECK_MILLISECONDS, POLL_MILLISECONDS, SETTLE_MILLISECONDS, WINDOWS_PATH, outcomeNotes, stillOpenNote } from "./words.js";

const pause = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

// One of the command's actions on one window or on several. Closing asks first and names every window. The rows wait, greyed, until the list
// has been read again, so the same button cannot be pressed twice. `windows()` is the list as it stands; `sync` repaints what `view.busy` changes.
export function createActions({ activity, view, watcher, windows, sync }) {
  return async function act(name, entries) {
    const targets = entries.filter((entry) => !view.busy.has(entry.id));
    // The agent is told which apps the windows belong to and not their titles, which can name a document or a message.
    const ask = () =>
      agentButton(activity, { title: "Close windows", commands: [WINDOWS_PATH], notes: [`About to be closed: windows of ${[...new Set(targets.map((entry) => entry.app))].join(", ")}.`], ideas: ["Will I lose anything by closing these?"] }, { small: true });
    if (targets.length === 0 || (name === "close" && !(await confirmClose(targets, ask())))) return;
    const ids = targets.map((entry) => entry.id);
    for (const id of ids) view.busy.add(id);
    sync();
    let results = [];
    try {
      ({ results } = await windowsApi.act(name, ids));
    } catch (error) {
      toast(error.message);
    }
    // A close is a request the app may answer with a question of its own, so the list is read a moment later and the page says what is still there.
    if (name === "close") await pause(CLOSE_CHECK_MILLISECONDS);
    await watcher.load();
    for (const id of ids) view.busy.delete(id);
    sync();
    for (const [message, tone] of outcomeNotes(name, targets, results)) toast(message, tone);
    const asked = new Set(results.filter((result) => name === "close" && result.status === "done").map((result) => result.id));
    const note = stillOpenNote(windows().filter((entry) => asked.has(entry.id)));
    if (note) toast(note, "info");
    // Once more shortly after, for a change that shows only when the window has finished moving.
    watcher.schedule(name === "close" ? POLL_MILLISECONDS : SETTLE_MILLISECONDS);
  };
}
