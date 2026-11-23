import { h } from "/assets/scripts/dom.js";
import { avatar, highlight, pill } from "../../widgets.js";
import { plural } from "../../words.js";
import { keyOf, placeLabel, rotationNote, valueCount } from "./words.js";

// One line of the list: the login, what it is for or else the names of its values, and what needs attention.
// `several` says the logins come from more than one file, so each line also says which.
export function loginRow(login, { term, chosen, several, onPick }) {
  const due = login.secrets.some((secret) => rotationNote(secret.rotation)?.tone === "warn");
  const names = login.secrets.flatMap((secret) => secret.values.map((row) => row.key)).join(", ");
  const count = plural(valueCount(login), "value");
  return h(
    "button",
    // Only the chosen row is a tab stop: the arrow keys move between rows, and Tab goes on to the login.
    { class: "prompt-row", type: "button", role: "option", "data-key": keyOf(login), "aria-selected": String(chosen), tabindex: chosen ? "0" : "-1", onclick: () => onPick(login) },
    avatar(login.name, 38),
    h(
      "span",
      { class: "prompt-row-text" },
      h("strong", {}, highlight(login.name, term), login.accountName && h("span", { class: "dim", text: ` · ${login.accountName}` })),
      h("span", { class: "prompt-row-blurb", text: login.description ?? (names || "No values yet") }),
      h("span", { class: "prompt-row-meta" }, due && pill("Rotation due", "warn"), (login.tags ?? []).slice(0, 2).map((tag) => pill(tag)), h("span", { class: "dim", text: several ? `${placeLabel(login.source)} · ${count}` : count })),
    ),
  );
}
