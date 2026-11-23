import { h, tildify } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { openDialog } from "../../overlays.js";
import { button, field, glyphTile, iconButton, segmented, textBox } from "../../widgets.js";
import { PLACE_BLURBS, canChange, kindOf, newKinds, placeLabel } from "./words.js";

// The form a script is added from. `places` are the folders one can be added to, as the server lists them, and `place` is the one to start on.
// The script is made with one line that says what it does and one that shows it ran; `onCreated` is handed where it is, to open it for editing.
export function openNewScript({ places, place, onCreated }) {
  const kinds = newKinds();
  let target = places.find((candidate) => candidate.name === place) ?? places.find((candidate) => candidate.name === "user");
  let suffix = kinds[0][0];
  const dialog = openDialog({ label: "New script", size: "script-new" });

  const name = textBox("", { placeholder: "Such as cleanup, or tools/cleanup to put it in a folder", oninput: paint, onkeydown: (event) => event.key === "Enter" && store() });
  const summary = textBox("", { placeholder: "One line, shown in the list", onkeydown: (event) => event.key === "Enter" && store() });
  const where = h("span", { class: "field-hint" });
  const kindPicker = segmented(kinds, (value) => {
    suffix = value;
    paint();
  });
  const placePicker = segmented(places.map((candidate) => [candidate.name, placeLabel(candidate.name)]), (value) => {
    target = places.find((candidate) => candidate.name === value);
    paint();
  });
  const problem = h("span", { class: "tool-problem", role: "alert" });
  const create = button({ label: "Create and edit", glyph: "check", tone: "primary", title: "Makes the file and opens it in a text editor inside the activity panel", onclick: store });

  function paint() {
    problem.textContent = "";
    kindPicker.set(suffix);
    placePicker.set(target.name);
    const typed = name.value.trim();
    const file = typed.endsWith(suffix) ? typed : `${typed}${suffix}`;
    where.textContent = `${PLACE_BLURBS[kindOf(target.name)]} ${typed ? `This creates ${tildify(`${target.path}/${file}`, state.boot.home)}.` : `It goes in ${tildify(target.path, state.boot.home)}.`}`;
  }

  async function store() {
    if (create.disabled) return;
    problem.textContent = name.value.trim() ? "" : "Give the script a name.";
    if (problem.textContent) return name.focus();
    create.disabled = true;
    try {
      const made = await api.createScript({ base: state.settings.workingDirectory, source: target.name, name: name.value.trim(), suffix, summary: summary.value });
      dialog.close();
      onCreated(made);
    } catch (error) {
      create.disabled = false;
      problem.textContent = error.message;
    }
  }

  dialog.body.append(
    h(
      "header",
      { class: "file-head" },
      glyphTile("terminal", 215, 46),
      h("div", { class: "file-title" }, h("span", { class: "overline", text: "New script" }), h("h2", { text: "Add a script" })),
      iconButton("close", "Close", () => dialog.dismiss()),
    ),
    h(
      "div",
      { class: "script-new-fields" },
      field("Name", name),
      field("What it does", summary),
      h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Written in" })), kindPicker.element),
      h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Keep it in" })), places.length > 1 && placePicker.element, where),
    ),
    // The foot is laid out by the vault form's rule (vault.css).
    h("footer", { class: "vault-form-foot" }, problem, button({ label: "Cancel", onclick: () => dialog.dismiss() }), create),
  );
  paint();
  name.focus();
}

// A new script, in the place being looked at when one can be added there and in the user's own otherwise. The places are read first.
export async function addScript({ place, onCreated }) {
  const { places } = await api.scripts(state.settings.workingDirectory);
  openNewScript({ places: places.filter((candidate) => canChange(candidate.name)), place, onCreated });
}
