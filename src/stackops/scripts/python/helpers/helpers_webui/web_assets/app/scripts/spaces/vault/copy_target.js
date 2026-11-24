import { debounce, h, tildify } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { segmented } from "../../widgets.js";
import { plural } from "../../words.js";
import { readTarget } from "./file_api.js";
import { mark } from "./tools_kit.js";

const CHECK_DELAY_MILLISECONDS = 300;
// What can be done with a file that is already at the place, by what the server found there.
const CHOICES = { append: "Add to it", overwrite: "Replace it" };

// Where the copy goes: a path to type or pick, the places most copies go to as shortcuts, and under it what stands at that place now and what
// the copy will do there. `read()` gives the path, how a file already there is to be treated, and whether the copy can be made.
export function createTargetField({ path, conflict, onChange }) {
  let source = "";
  let found = null;
  let trouble = "";
  let choice = conflict;
  let asked = null;
  const combo = createCombo({
    value: path, placeholder: "A file name, such as ~/vault-copy.json", glyph: "folder", label: "Where the copy goes",
    suggest: async (text) => (await api.paths(text || "~/", state.settings.workingDirectory)).entries.map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
    onInput: () => look(),
    onPick: () => look(),
  });
  const shortcuts = h("div", { class: "vault-copy-shortcuts" });
  const standing = h("div", { class: "vault-copy-standing", role: "status" });
  const element = h("div", { class: "vault-copy-target" }, combo.element, shortcuts, standing);

  function paint() {
    const shown = found && tildify(found.path, state.boot.home);
    const line = (tone, text, extra) => standing.replaceChildren(mark(tone), h("div", {}, h("p", { text }), extra));
    if (trouble) return line("bad", trouble);
    if (!found) return line("busy", "Looking at that place");
    if (found.state === "free") return line("good", `A new file is written at ${shown}. Only you can read it.`);
    if (found.state === "same") return line("bad", "That is the file the logins are taken from. Choose another place.");
    if (found.state === "folder") return line("bad", `${shown} is a folder. Add a file name to it, such as vault-copy.json.`);
    const options = Object.keys(CHOICES).filter((id) => id === "overwrite" || (found.state === "vault" && found.same_version));
    if (!options.includes(choice)) choice = "";
    const picker = segmented(options.map((id) => [id, CHOICES[id]]), (value) => {
      choice = value;
      paint();
      onChange();
    });
    picker.set(choice);
    const there =
      found.state === "vault"
        ? `A vault file with ${plural(found.logins, "login")} is already at ${shown}.${found.same_version ? "" : " It was written for another version of the vault, so nothing can be added to it."}`
        : `A file that is not a vault file is already at ${shown}.`;
    const effect = choice === "append" ? "The chosen logins are added after the ones it holds." : choice === "overwrite" ? "Everything in it is replaced by the chosen logins." : "Say what happens to it.";
    line(choice ? "warn" : "note", there, h("div", { class: "vault-copy-choice" }, picker.element, h("span", { class: "dim", text: effect })));
  }

  const ask = debounce(async () => {
    asked?.abort();
    const mine = (asked = new AbortController());
    try {
      const answer = await readTarget(source, combo.input.value.trim(), mine.signal);
      if (mine.signal.aborted) return;
      found = answer;
      trouble = "";
    } catch (error) {
      if (mine.signal.aborted) return;
      found = null;
      // A bare "not found" is a server that was started before this view existed.
      trouble = error.status === 404 && !error.payload ? "Restart the web UI before copying. This view is newer than the server that is running." : error.message;
    }
    paint();
    onChange();
  }, CHECK_DELAY_MILLISECONDS);

  function look() {
    found = null;
    trouble = combo.input.value.trim() === "" ? "Say where the copy goes." : "";
    paint();
    onChange();
    if (!trouble) ask();
  }

  return {
    element,
    // `places` are the shortcuts: [label, path] pairs for the file being copied from.
    show(from, places) {
      source = from;
      shortcuts.replaceChildren(
        ...places.map(([label, place]) =>
          h("button", {
            class: "chip-button", type: "button", text: label,
            onclick: () => {
              combo.setValue(tildify(place, state.boot.home));
              look();
            },
          }),
        ),
      );
      look();
    },
    look,
    read() {
      const settled = found !== null && !trouble;
      const taken = settled && (found.state === "vault" || found.state === "other");
      const ready = settled && (found.state === "free" || (taken && choice !== ""));
      const why = trouble || (!settled ? "Looking at where the copy goes." : taken && !choice ? "Say what happens to the file that is already there." : !ready ? "Choose another place for the copy." : "");
      return { path: combo.input.value.trim(), shown: found?.path ?? "", conflict: taken ? choice : "throw-error", replaces: taken && choice === "overwrite", ready, why };
    },
  };
}
