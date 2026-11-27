import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { replay } from "../../../motion.js";
import { confirmAction } from "../../../overlays.js";
import { iconButton } from "../../../widgets.js";
import { change } from "./api.js";
import { switchWords } from "./words.js";

// What the last change did, in a line above the list, with a way to take it back where there is one.
export function createOutcome() {
  const text = h("span");
  const undo = h("button", { class: "link", type: "button", onclick: () => offered?.() });
  const element = h("div", { class: "autostart-outcome", role: "status", hidden: true }, icon("check", 16), text, undo, h("span", { class: "spacer" }), iconButton("close", "Dismiss", () => (element.hidden = true)));
  let offered = null;
  return {
    element,
    show({ said, undoLabel, onUndo }) {
      text.textContent = said;
      undo.hidden = !onUndo;
      undo.textContent = undoLabel ?? "";
      offered = onUndo ?? null;
      element.hidden = false;
      replay(element, "autostart-pop");
    },
  };
}

// Turning an entry off or back on, and removing it. Each asks first and says what the system will do; the server then checks the entry
// against a fresh read before it touches anything. Taking back what was just done needs no second question.
export function createActions({ view, repaint, reload, outcome }) {
  async function carry(entry, action, done) {
    if (view.busy.has(entry.id)) return;
    view.busy.add(entry.id);
    repaint();
    try {
      await change(action, entry.id);
      outcome.show(done);
    } catch (error) {
      toast(error.message);
    }
    view.busy.delete(entry.id);
    await reload();
  }

  const off = (entry) => carry(entry, "turn-off", { said: `${entry.title} is turned off.`, undoLabel: "Turn it back on", onUndo: () => on(entry) });
  const on = (entry) => carry(entry, "turn-on", { said: `${entry.title} is on again.`, undoLabel: "Turn it off again", onUndo: () => off(entry) });

  async function toggle(entry, platform) {
    const words = switchWords(entry, platform);
    const asked = entry.enabled ? { title: `Turn off ${entry.title}?`, body: words.off, confirm: "Turn off" } : { title: `Turn ${entry.title} back on?`, body: words.on, confirm: "Turn on" };
    if (await confirmAction(asked)) await (entry.enabled ? off(entry) : on(entry));
  }

  async function remove(entry) {
    if (entry.kind === "login_item") {
      const sure = await confirmAction({
        title: `Stop opening ${entry.title} when you sign in?`, confirm: "Take it off the list",
        body: "It comes off the list of login items. The app itself stays installed. You can put it back from this page until StackOps is restarted, and after that in System Settings under General, Login Items & Extensions.",
      });
      if (!sure) return;
      await carry(entry, "remove", {
        said: `${entry.title} no longer opens when you sign in.`, undoLabel: "Put it back",
        onUndo: () => carry(entry, "put-back", { said: `${entry.title} opens when you sign in again.` }),
      });
      return;
    }
    const sure = await confirmAction({
      title: `Move ${entry.title} to the Trash?`, confirm: "Move to the Trash", tone: "danger",
      body: `${entry.live === "idle" ? "Its file" : "macOS stops it, and its file"}, ${tildify(entry.file, state.boot.home)}, goes to the Trash. After that it no longer starts on its own. The program it runs is not removed. To undo this, drag the file out of the Trash back into its folder, then sign out and in again.`,
    });
    if (sure) await carry(entry, "remove", { said: `${entry.title} no longer starts on its own. Its file is in the Trash.` });
  }

  return { toggle, remove };
}
