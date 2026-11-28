import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { agentButton } from "../../../agent_ask.js";
import { openDialog } from "../../../overlays.js";
import { button, glyphTile, iconButton, notice, searchInput, segmented } from "../../../widgets.js";
import { KINDS, readItems } from "./add_entry_items.js";

export const ADD_COMMAND = "utils machine autostart-add";
export const REMOVE_COMMAND = "utils machine autostart-remove";
export const APPLY_COMMAND = "utils machine autostart-apply";
// The systems as the startup list names them, with what a person calls each. `state.boot.platform` is one of the names.
const SYSTEMS = { linux: "Linux", darwin: "macOS", windows: "Windows" };
// Only an administrator can have something start before a sign-in on macOS and Windows, so the choice is offered on Linux alone.
const WHENS = [["login", "When you sign in"], ["boot", "When the computer starts"]];
const STEP_KEYS = { ArrowDown: 1, ArrowUp: -1 };
// The dialog something is added to startup from: one of the scripts StackOps keeps that can start on this system, as the Scripts page
// lists them, or one of the layouts saved in the dotfiles. Adding is what `utils machine autostart-add` does. Nothing is started: it first
// runs at the next sign-in. A layout, or a script of the dotfiles, is also written to the startup list there, for this system and the
// others that are picked, so the person's other machines can start it too. `onAdded` is handed what it is called and when it starts once
// the system has taken it.
export async function openAddEntry({ activity, onAdded }) {
  const { items, problem: layoutsProblem } = await readItems();
  let kind = "script";
  let term = "";
  let chosen = null;
  let when = "login";
  const elsewhere = new Set();
  const here = Object.keys(SYSTEMS).find((system) => SYSTEMS[system] === state.boot.platform);

  const dialog = openDialog({ label: "Add a startup entry", size: "autostart-add" });
  const list = h("div", { class: "prompt-list autostart-add-list", role: "listbox" });
  const blank = h("div", { class: "autostart-add-blank" });
  const hint = h("p", { class: "autostart-add-hint" });
  const problem = h("span", { class: "tool-problem", role: "alert" });
  const add = button({ label: "Start at sign-in", glyph: "power", tone: "primary", onclick: store });
  const kindPick = segmented(Object.keys(KINDS).map((id) => [id, KINDS[id].label]), (value) => {
    kind = value;
    term = "";
    chosen = null;
    search.input.value = "";
    paint();
    search.input.focus();
  });
  const whenPick = segmented(WHENS, (value) => {
    when = value;
    paint();
  });
  const whenField = h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "When it starts" })), whenPick.element, h("span", { class: "field-hint" }));
  const systemChips = Object.keys(SYSTEMS).filter((system) => system !== here).map((system) =>
    h("button", { class: "chip-button", type: "button", text: SYSTEMS[system], "data-system": system, onclick: () => (elsewhere.delete(system) || elsewhere.add(system), paint()) }),
  );
  const systemsField = h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Your other machines" })), h("div", { class: "chip-row" }, systemChips), h("span", { class: "field-hint" }));
  const options = h("div", { class: "autostart-add-options" }, whenField, systemsField);
  const search = searchInput({
    placeholder: "",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const ofKind = () => items.filter((item) => item.kind === kind);
  const shown = () => ofKind().filter((item) => !term || item.haystack.includes(term));
  const leaveFor = (hash) => {
    dialog.close();
    location.hash = hash;
  };

  function pick(item) {
    chosen = item;
    paint();
  }

  function paint() {
    const words = KINDS[kind];
    const all = ofKind();
    const found = shown();
    // What the search no longer shows is no longer the one picked: what is added is always on screen.
    if (chosen && !found.some((item) => item.key === chosen.key)) chosen = null;
    kindPick.set(kind);
    search.element.hidden = all.length === 0;
    search.input.placeholder = words.search;
    search.input.setAttribute("aria-label", words.search);
    list.setAttribute("aria-label", words.list);
    list.replaceChildren(...found.map((item) => item.row({ term, chosen: chosen !== null && item.key === chosen.key, onPick: () => pick(item) })));
    list.hidden = found.length === 0;
    blank.replaceChildren(
      ...(kind === "layout" && layoutsProblem
        ? [notice({ glyph: "alert", tone: "bad", title: "Your layouts could not be read", body: layoutsProblem })]
        : all.length === 0
          ? [notice({ glyph: words.glyph, title: words.none, body: words.about, action: button({ label: words.open, small: true, onclick: () => leaveFor(words.hash) }) })]
          : found.length === 0
            ? [notice({ glyph: "search", title: "Nothing matches", body: "Try a different word." })]
            : []),
    );
    problem.textContent = "";
    add.disabled = chosen === null;
    // Starting with the computer is this system's own way, so it cannot be asked of the other systems.
    const listed = chosen !== null && chosen.listed;
    const others = listed && when === "login" ? systemChips.filter((chip) => elsewhere.has(chip.dataset.system)).map((chip) => chip.textContent) : [];
    whenPick.set(when);
    whenField.hidden = chosen === null || state.boot.platform !== "Linux";
    whenField.lastChild.textContent = when === "boot" ? "Your account's services then start with the computer and stay after you sign out, so whatever else your account starts at sign-in does too." : "";
    systemsField.hidden = !listed || when === "boot";
    systemChips.forEach((chip) => chip.setAttribute("aria-pressed", String(elsewhere.has(chip.dataset.system))));
    systemsField.lastChild.textContent = `Your startup list keeps it for ${state.boot.platform}${others.length > 0 ? `, ${others.join(" and ")}` : ""}. A machine that runs one of them can start it too, from this page.`;
    options.hidden = whenField.hidden && systemsField.hidden;
    add.lastChild.textContent = when === "boot" ? "Start with the computer" : "Start at sign-in";
    const moment = when === "boot" ? "each time this computer starts, from the next start on" : "each time you sign in, from your next sign-in on";
    const onlyHere = chosen !== null && !listed ? " It starts on this machine only, since it is not one of the scripts in your dotfiles." : "";
    hint.textContent = chosen ? `${chosen.runs} ${moment}. Nothing is started now.${onlyHere}` : all.length > 0 ? words.pick : "";
  }

  async function store() {
    if (chosen === null || add.disabled) return;
    add.disabled = true;
    try {
      await chosen.add(when, chosen.listed && when === "login" ? [...elsewhere] : []);
      dialog.close();
      onAdded(chosen.title, when);
    } catch (error) {
      add.disabled = false;
      problem.textContent = error.message;
    }
  }

  // The arrow keys move the pick from the search box and from the list, and Enter adds it.
  function step(event) {
    if (event.key === "Enter" && chosen !== null) return store();
    const move = STEP_KEYS[event.key];
    const found = shown();
    if (move === undefined || found.length === 0) return;
    event.preventDefault();
    const at = chosen ? found.findIndex((item) => item.key === chosen.key) : -1;
    pick(found[Math.max(0, Math.min(found.length - 1, at + move))]);
    const row = list.querySelector(`[aria-selected="true"]`);
    row.scrollIntoView({ block: "nearest" });
    if (event.currentTarget === list) row.focus();
  }
  search.input.addEventListener("keydown", step);
  list.addEventListener("keydown", step);

  dialog.body.append(
    h(
      "header",
      { class: "file-head" },
      glyphTile("power", 252, 46),
      h("div", { class: "file-title" }, h("span", { class: "overline", text: "Startup programs" }), h("h2", { text: "Add an entry" })),
      iconButton("close", "Close", () => dialog.dismiss()),
    ),
    h("div", { class: "autostart-add-tools" }, kindPick.element, search.element),
    list,
    blank,
    options,
    hint,
    // The foot is laid out by the vault form's rule (vault.css).
    h(
      "footer",
      { class: "vault-form-foot" },
      agentButton(activity, { title: "Add a startup entry", commands: [ADD_COMMAND, REMOVE_COMMAND, APPLY_COMMAND], about: "Where one of the scripts StackOps keeps, or one of the terminal layouts saved in the dotfiles, is set to start every time the person signs in or, on Linux, when the computer starts, and is written to the startup list in the dotfiles for the person's other machines." }, { small: true }),
      problem,
      button({ label: "Cancel", onclick: () => dialog.dismiss() }),
      add,
    ),
  );
  paint();
  if (ofKind().length > 0) search.input.focus();
}
