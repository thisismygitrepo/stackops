import { h } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../../../agent_ask.js";
import { openDialog } from "../../../overlays.js";
import { button, glyphTile, iconButton, notice, searchInput } from "../../../widgets.js";
import { scriptRow } from "../../scripts/script_row.js";
import { fileOf, haystackOf, keyOf } from "../../scripts/words.js";
import { addScript } from "./api.js";

export const ADD_COMMAND = "utils machine autostart-add";
export const REMOVE_COMMAND = "utils machine autostart-remove";
const SCRIPTS_HASH = "#/scripts";
const STEP_KEYS = { ArrowDown: 1, ArrowUp: -1 };
// What runs each kind of script when it starts on its own. A Python script is a file that names what it needs in itself, so uv runs it and
// it is the same script on every system; a shell script is offered on the system it is written for.
const RUNNERS = { ".py": "uv", ".sh": "bash", ".ps1": "PowerShell" };
const startsHere = (script) => (state.boot.platform === "Windows" ? [".py", ".ps1"] : [".py", ".sh"]).includes(script.suffix);

// The dialog a script is added to startup from: the scripts StackOps keeps that can start on this system, as the Scripts page lists them,
// to pick one from. Adding is what `utils machine autostart-add` does. Nothing is started: the script first runs at the next sign-in.
// `onAdded` is handed the script's file name once the system has taken it.
export async function openAddScript({ activity, onAdded }) {
  const { places } = await api.scripts(state.settings.workingDirectory);
  const scripts = places
    .flatMap((place) => place.scripts.map((script) => ({ ...script, source: place.name })))
    .filter(startsHere)
    .map((script) => ({ ...script, haystack: haystackOf(script) }));
  const several = new Set(scripts.map((script) => script.source)).size > 1;
  let term = "";
  let chosen = null;

  const dialog = openDialog({ label: "Add a startup script", size: "autostart-add" });
  const list = h("div", { class: "prompt-list autostart-add-list", role: "listbox", "aria-label": "Scripts that can start when you sign in" });
  const blank = h("div", { class: "autostart-add-blank" });
  const hint = h("p", { class: "autostart-add-hint" });
  const problem = h("span", { class: "tool-problem", role: "alert" });
  const add = button({ label: "Start at sign-in", glyph: "power", tone: "primary", onclick: store });
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
    hint.textContent = chosen ? `${RUNNERS[chosen.suffix]} runs ${fileOf(chosen)} each time you sign in, from your next sign-in on. Nothing is started now.` : scripts.length > 0 ? "Pick the script to start each time you sign in." : "";
  }

  async function store() {
    if (chosen === null || add.disabled) return;
    add.disabled = true;
    try {
      await addScript(state.settings.workingDirectory, chosen.path);
      dialog.close();
      onAdded(fileOf(chosen));
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
    hint,
    // The foot is laid out by the vault form's rule (vault.css).
    h(
      "footer",
      { class: "vault-form-foot" },
      agentButton(activity, { title: "Add a startup script", commands: [ADD_COMMAND, REMOVE_COMMAND], about: "Where one of the scripts StackOps keeps is set to start every time the person signs in." }, { small: true }),
      problem,
      button({ label: "Cancel", onclick: () => dialog.dismiss() }),
      add,
    ),
  );
  paint();
  if (scripts.length > 0) search.input.focus();
}
