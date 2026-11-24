import { debounce, h } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../../combo.js";
import { checkPlace } from "./api.js";
import { PLACES } from "./words.js";

const CHECK_DELAY_MILLISECONDS = 250;

// A box for a folder or a file on this machine, with path suggestions as the working-folder picker has them, and under it what the server
// found at the typed path. `onChange(text, check)` hears every change: `check` is null while the server is looking and for an empty box,
// then `{ path, verdict }`, or `{ error }` when it could not look.
export function createPlaceField({ kind, label, placeholder, value, hint, onChange }) {
  const status = h("span", { class: "mount-place-status" });
  let text = value;
  let ticket = 0;

  function say(tone, words) {
    status.className = `mount-place-status ${tone}`;
    status.textContent = words;
  }

  async function look() {
    const mine = (ticket += 1);
    if (text.trim() === "") return say("", hint);
    say("", "Checking…");
    let check;
    try {
      check = await checkPlace(text, kind);
    } catch (error) {
      check = { error: error.message };
    }
    if (mine !== ticket) return;
    if (check.error) say("bad", check.error);
    else say(PLACES[check.verdict].tone, PLACES[check.verdict].text);
    onChange(text, check);
  }

  const lookSoon = debounce(look, CHECK_DELAY_MILLISECONDS);
  // Whatever was found belongs to the text before the change, so it is dropped at once and the box is checked again.
  function changed(next, wait) {
    text = next;
    ticket += 1;
    onChange(text, null);
    if (wait) lookSoon();
    else look();
  }

  const combo = createCombo({
    value, label, placeholder, glyph: kind === "key" ? "key" : "folder", emptyText: "Nothing to suggest",
    // An empty box lists the home folder. A folder is the only thing a mount point can be, so files are left out for it.
    suggest: async (typed) => (await api.paths(typed || "~/", state.settings.workingDirectory)).entries.filter((entry) => kind === "key" || entry.endsWith("/")).map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
    onInput: (typed) => changed(typed, true),
    onPick: (option) => changed(option.value, false),
  });
  look();
  return { element: h("div", { class: "mount-place" }, combo.element, status), input: combo.input };
}
