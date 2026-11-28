import { h } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../../../agent_ask.js";
import { openDialog } from "../../../overlays.js";
import { button, glyphTile, iconButton, notice, searchInput, segmented } from "../../../widgets.js";
import { scriptRow } from "../../scripts/script_row.js";
import { fileOf, haystackOf, keyOf } from "../../scripts/words.js";
import { addScript } from "./api.js";

export const ADD_COMMAND = "utils machine autostart-add";
export const REMOVE_COMMAND = "utils machine autostart-remove";
export const APPLY_COMMAND = "utils machine autostart-apply";
// The systems as the startup list names them, with what a person calls each. `state.boot.platform` is one of the names.
const SYSTEMS = { linux: "Linux", darwin: "macOS", windows: "Windows" };
// The place of the scripts in the dotfiles, as the server names it: the one place that is the same on every machine.
const DOTFILES_PLACE = "user";
// Only an administrator can have something start before a sign-in on macOS and Windows, so the choice is offered on Linux alone.
const WHENS = [["login", "When you sign in"], ["boot", "When the computer starts"]];
const SCRIPTS_HASH = "#/scripts";
const STEP_KEYS = { ArrowDown: 1, ArrowUp: -1 };
// What runs each kind of script when it starts on its own. A Python script is a file that names what it needs in itself, so uv runs it and
// it is the same script on every system; a shell script is offered on the system it is written for.
const RUNNERS = { ".py": "uv", ".sh": "bash", ".ps1": "PowerShell" };
const startsHere = (script) => (state.boot.platform === "Windows" ? [".py", ".ps1"] : [".py", ".sh"]).includes(script.suffix);

// The dialog a script is added to startup from: the scripts StackOps keeps that can start on this system, as the Scripts page lists them,
// to pick one from. Adding is what `utils machine autostart-add` does. Nothing is started: the script first runs at the next sign-in.
// A script of the dotfiles is also written to the startup list there, for this system and the others that are picked, so the person's
// other machines can start it too. `onAdded` is handed the script's file name and when it starts once the system has taken it.
export async function openAddScript({ activity, onAdded }) {
  const { places } = await api.scripts(state.settings.workingDirectory);
  const scripts = places
    .flatMap((place) => place.scripts.map((script) => ({ ...script, source: place.name })))
    .filter(startsHere)
    .map((script) => ({ ...script, haystack: haystackOf(script) }));
  const several = new Set(scripts.map((script) => script.source)).size > 1;
  let term = "";
  let chosen = null;
  let when = "login";
  const elsewhere = new Set();
  const here = Object.keys(SYSTEMS).find((system) => SYSTEMS[system] === state.boot.platform);

  const dialog = openDialog({ label: "Add a startup script", size: "autostart-add" });
  const list = h("div", { class: "prompt-list autostart-add-list", role: "listbox", "aria-label": "Scripts that can start when you sign in" });
  const blank = h("div", { class: "autostart-add-blank" });
  const hint = h("p", { class: "autostart-add-hint" });
  const problem = h("span", { class: "tool-problem", role: "alert" });
  const add = button({ label: "Start at sign-in", glyph: "power", tone: "primary", onclick: store });
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
    placeholder: "Search your scripts",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const shown = () => scripts.filter((script) => !term || script.haystack.includes(term));
  const toScripts = () => {
    dialog.close();
    location.hash = SCRIPTS_HASH;
  };

  function pick(script) {
    chosen = script;
    paint();
  }

  function paint() {
    const found = shown();
    // A script the search no longer shows is no longer the one picked: what is added is always on screen.
    if (chosen && !found.some((script) => keyOf(script) === keyOf(chosen))) chosen = null;
    list.replaceChildren(...found.map((script) => scriptRow(script, { term, several, chosen: chosen !== null && keyOf(script) === keyOf(chosen), onPick: pick })));
    list.hidden = found.length === 0;
    blank.replaceChildren(
      ...(scripts.length === 0
        ? [notice({ glyph: "terminal", title: "No script to add yet", body: "A startup script is one of the scripts StackOps keeps: a Python file, or a shell script written for this system. Write one on the Scripts page, then add it here.", action: button({ label: "Open Scripts", small: true, onclick: toScripts }) })]
        : found.length === 0
          ? [notice({ glyph: "search", title: "No script matches", body: "Try a different word." })]
          : []),
    );
    problem.textContent = "";
    add.disabled = chosen === null;
    // Starting with the computer is this system's own way, so it cannot be asked of the other systems.
    const listed = chosen !== null && chosen.source === DOTFILES_PLACE;
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
    hint.textContent = chosen ? `${RUNNERS[chosen.suffix]} runs ${fileOf(chosen)} ${moment}. Nothing is started now.${onlyHere}` : scripts.length > 0 ? "Pick the script to start on its own." : "";
  }

  async function store() {
    if (chosen === null || add.disabled) return;
    add.disabled = true;
    try {
      await addScript(state.settings.workingDirectory, chosen.path, when, chosen.source === DOTFILES_PLACE && when === "login" ? [...elsewhere] : []);
      dialog.close();
      onAdded(fileOf(chosen), when);
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
    const at = chosen ? found.findIndex((script) => keyOf(script) === keyOf(chosen)) : -1;
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
      h("div", { class: "file-title" }, h("span", { class: "overline", text: "Startup programs" }), h("h2", { text: "Add a script" })),
      iconButton("close", "Close", () => dialog.dismiss()),
    ),
    ...(scripts.length > 0 ? [h("div", { class: "autostart-add-tools" }, search.element)] : []),
    list,
    blank,
    options,
    hint,
    // The foot is laid out by the vault form's rule (vault.css).
    h(
      "footer",
      { class: "vault-form-foot" },
      agentButton(activity, { title: "Add a startup script", commands: [ADD_COMMAND, REMOVE_COMMAND, APPLY_COMMAND], about: "Where one of the scripts StackOps keeps is set to start every time the person signs in or, on Linux, when the computer starts, and is written to the startup list in the dotfiles for the person's other machines." }, { small: true }),
      problem,
      button({ label: "Cancel", onclick: () => dialog.dismiss() }),
      add,
    ),
  );
  paint();
  if (scripts.length > 0) search.input.focus();
}
