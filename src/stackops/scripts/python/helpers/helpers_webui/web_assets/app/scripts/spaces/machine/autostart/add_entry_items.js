import { h } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { avatar, highlight } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { scriptRow } from "../../scripts/script_row.js";
import { fileOf, haystackOf, keyOf } from "../../scripts/words.js";
import { addLayout, addScript, readLayouts } from "./api.js";

// The place of the scripts in the dotfiles, as the server names it: the one place that is the same on every machine.
const DOTFILES_PLACE = "user";
// What runs each kind of script when it starts on its own. A Python script is a file that names what it needs in itself, so uv runs it and
// it is the same script on every system; a shell script is offered on the system it is written for.
const RUNNERS = { ".py": "uv", ".sh": "bash", ".ps1": "PowerShell" };
const startsHere = (script) => (state.boot.platform === "Windows" ? [".py", ".ps1"] : [".py", ".sh"]).includes(script.suffix);
// The two things that can be set to start on their own, with the words the dialog uses for each and where a person makes one.
export const KINDS = {
  script: {
    label: "A script", search: "Search your scripts", list: "Scripts that can start on their own", pick: "Pick the script to start on its own.", glyph: "terminal", none: "No script to add yet",
    about: "A startup script is one of the scripts StackOps keeps: a Python file, or a shell script written for this system. Write one on the Scripts page, then add it here.", open: "Open Scripts", hash: "#/scripts",
  },
  layout: {
    label: "A layout", search: "Search your layouts", list: "Layouts that can be launched on their own", pick: "Pick the layout to launch on its own.", glyph: "layers", none: "No layout to add yet",
    about: "A startup layout is one of the terminal layouts saved in your dotfiles: its tabs and panes are started in the background, ready to attach to. Save one on the Sessions page, then add it here.", open: "Open Sessions", hash: "#/sessions",
  },
};

function layoutRow(layout, { term, chosen, onPick }) {
  return h(
    "button",
    { class: "prompt-row", type: "button", role: "option", "aria-selected": String(chosen), tabindex: chosen ? "0" : "-1", onclick: onPick },
    avatar(layout.name, 38),
    h("span", { class: "prompt-row-text" }, h("strong", {}, highlight(layout.name, term)), h("span", { class: "prompt-row-meta" }, h("span", { class: "dim", text: `${plural(layout.tabs, "tab")} · ${plural(layout.panes, "pane")}` }))),
  );
}

// What can be picked, of both kinds, each with what the dialog needs of it: `title` is what it is called once it is added, `runs` how it
// is started, `listed` whether the startup list can name it, and `add` sends it to the server.
export async function readItems() {
  const base = state.settings.workingDirectory;
  const [{ places }, saved] = await Promise.all([api.scripts(base), readLayouts().catch((error) => ({ layouts: [], problem: error.message }))]);
  const scripts = places.flatMap((place) => place.scripts.map((script) => ({ ...script, source: place.name }))).filter(startsHere);
  const several = new Set(scripts.map((script) => script.source)).size > 1;
  return {
    problem: saved.problem ?? "",
    items: [
      ...scripts.map((script) => ({
        kind: "script", key: keyOf(script), title: fileOf(script), haystack: haystackOf(script), listed: script.source === DOTFILES_PLACE, runs: `${RUNNERS[script.suffix]} runs ${fileOf(script)}`,
        row: (context) => scriptRow(script, { ...context, several }), add: (when, systems) => addScript(base, script.path, when, systems),
      })),
      ...saved.layouts.map((layout) => ({
        kind: "layout", key: `layout\n${layout.name}`, title: `The layout ${layout.name}`, haystack: layout.name.toLowerCase(), listed: true, runs: `StackOps launches the layout ${layout.name} in the background`,
        row: (context) => layoutRow(layout, context), add: (when, systems) => addLayout(layout.name, when, systems),
      })),
    ],
  };
}
