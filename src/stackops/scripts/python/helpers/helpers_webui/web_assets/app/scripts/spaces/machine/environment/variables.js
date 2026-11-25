import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { copyChip, copyText, iconButton, pill } from "../../../widgets.js";
import { PARTS_SHOWN, TOOL_PATH } from "./words.js";

// One variable. A value that is a list of folders is drawn as that list, cut short until the row is opened; any other long value is cut to
// two lines the same way. A value that was left out says so and has nothing to copy.
function variableRow(variable, open, toggle) {
  let value;
  if (variable.value === null) value = pill("Left out. It looks like a secret.");
  else if (variable.value === "") value = h("span", { class: "dim", text: "empty" });
  else if (variable.parts) {
    const shown = open ? variable.parts : variable.parts.slice(0, PARTS_SHOWN);
    value = h(
      "ol",
      { class: "env-parts" },
      shown.map((part) => h("li", {}, h("code", { title: part, text: tildify(part, state.boot.home) }))),
      variable.parts.length > shown.length && h("li", { class: "env-more", text: `and ${variable.parts.length - shown.length} more` }),
    );
  } else value = h("code", { class: "env-value", text: variable.value });

  const copy = iconButton("copy", `Copy the value of ${variable.name}`, async (event) => {
    event.stopPropagation();
    if (!(await copyText(variable.value))) return;
    copy.replaceChildren(icon("check", 16));
    setTimeout(() => copy.replaceChildren(icon("copy", 16)), 1200);
  });
  return h(
    "li",
    {
      class: `env-row${open ? " open" : ""}`,
      // A click that ends a text selection is someone copying part of a value, not asking for the row to open or close.
      onclick: () => getSelection().toString() === "" && toggle(),
    },
    h("strong", { class: "env-name", text: variable.name }),
    h("div", { class: "env-cell" }, value),
    variable.value ? copy : h("span", { class: "env-gap" }),
  );
}

// The Variables tab: what the page's frame shows for it, and its rows for what is typed and which filters are on.
export function variablesTab({ variables, prefixes }, repaint) {
  const opened = new Set();
  const leftOut = variables.filter((variable) => variable.value === null).length;
  const lists = variables.filter((variable) => variable.parts).length;
  const command = `stackops ${TOOL_PATH}`;
  return {
    unit: "variable",
    total: variables.length,
    placeholder: "Search names and values",
    emptyText: "No variable matches",
    tiles: [
      { glyph: "sliders", hue: 252, label: "Variables", value: variables.length, note: "set for tasks started here" },
      { glyph: "folder", hue: 165, label: "Lists of folders", value: lists, note: "values such as PATH" },
      { glyph: "lock", hue: 20, label: "Values left out", value: leftOut, note: leftOut > 0 ? "they look like secrets" : "nothing looks like a secret" },
    ],
    chips: [
      ...prefixes.map(([prefix, count]) => ({ key: prefix, label: `${prefix}*`, count })),
      { key: ":lists", label: "Lists of folders", count: lists },
      { key: ":left-out", label: "Left out", count: leftOut },
    ].filter((chip) => chip.count > 0),
    note:
      leftOut > 0
        ? [h("span", { text: "A value is left out when the variable's name or the value itself looks like a secret. It is not sent to this page. To read one, run this in a terminal:" }), copyChip(command)]
        : [],
    rows(terms, active) {
      const prefixFilters = [...active].filter((key) => !key.startsWith(":"));
      return variables
        .filter(
          (variable) =>
            terms.every((term) => variable.text.includes(term)) &&
            (prefixFilters.length === 0 || prefixFilters.includes(variable.prefix)) &&
            (!active.has(":lists") || variable.parts !== null) &&
            (!active.has(":left-out") || variable.value === null),
        )
        .map((variable) =>
          variableRow(variable, opened.has(variable.name), () => {
            if (!opened.delete(variable.name)) opened.add(variable.name);
            repaint();
          }),
        );
    },
  };
}
