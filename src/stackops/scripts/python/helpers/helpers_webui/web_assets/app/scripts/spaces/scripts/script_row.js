import { h } from "/assets/scripts/dom.js";
import { highlight } from "../../widgets.js";
import { fileOf, folderOf, keyOf, placeLabel, scriptFace } from "./words.js";

// One line of the list: the script, what it says it does, and where it is. `several` says the scripts come from more than one place, so each line also says which.
export function scriptRow(script, { term, chosen, several, onPick }) {
  return h(
    "button",
    // Only the chosen row is a tab stop: the arrow keys move between rows, and Tab goes on to the script.
    { class: "prompt-row", type: "button", role: "option", "data-key": keyOf(script), "aria-selected": String(chosen), tabindex: chosen ? "0" : "-1", onclick: () => onPick(script) },
    scriptFace(script, 38),
    h(
      "span",
      { class: "prompt-row-text" },
      h("strong", {}, highlight(fileOf(script), term)),
      script.summary && h("span", { class: "prompt-row-blurb" }, highlight(script.summary, term)),
      h("span", { class: "prompt-row-meta" }, h("span", { class: "dim", text: [several && placeLabel(script.source), folderOf(script)].filter(Boolean).join(" · ") })),
    ),
  );
}
