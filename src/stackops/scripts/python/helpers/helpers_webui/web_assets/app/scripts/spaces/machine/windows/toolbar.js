import { h } from "/assets/scripts/dom.js";
import { createCombo } from "../../../combo.js";
import { remember } from "../../../memory.js";
import { avatar, searchInput, segmented } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { appCounts, filterChoices } from "./model.js";
import { EVERY_APP, MEMORY_ID } from "./words.js";

// What narrows and orders the list: a row of filters with their counts, a pick of one app, the order, and a search over titles and app names.
// Each control writes its choice into `view` and calls `view.changed()`. The page calls `paint` when the windows or a choice changed.
export function createWindowsToolbar(view) {
  const chips = new Map();
  const chipRow = h("div", { class: "chip-row" });
  let apps = [];
  let total = 0;

  const search = searchInput({
    placeholder: "Find a window or app",
    oninput: (value) => {
      view.term = value.trim().toLowerCase();
      view.changed();
    },
  });
  const orderPick = segmented([["app", "By app"], ["size", "Biggest first"]], (order) => {
    view.order = order;
    remember(MEMORY_ID, new Map([["order", order]]));
    view.changed();
  });
  const appPick = createCombo({
    value: EVERY_APP, label: "Show the windows of one app", glyph: "apps", readOnly: true,
    suggest: async () => [
      { value: "", label: EVERY_APP, hint: plural(total, "window"), fill: false },
      ...apps.map(([name, count]) => ({ value: name, label: name, hint: plural(count, "window"), lead: avatar(name, 26), fill: false })),
    ],
    onPick: (option) => {
      view.app = option.value;
      view.changed();
    },
  });
  const element = h("div", { class: "windows-tools" }, chipRow, h("div", { class: "windows-tools-side" }, appPick.element, orderPick.element, search.element));

  function paint(model) {
    const choices = filterChoices(model);
    // The chips are only made again when the choices themselves change, so the one just pressed keeps the keyboard's focus.
    if (choices.map((choice) => choice.id).join("\n") !== [...chips.keys()].join("\n")) {
      chips.clear();
      for (const choice of choices) {
        const count = h("b");
        const label = h("span");
        const chip = h("button", { class: "chip-button", type: "button", onclick: () => { view.filter = choice.id; view.changed(); } }, label, count);
        chips.set(choice.id, { chip, label, count });
      }
      chipRow.replaceChildren(...[...chips.values()].map(({ chip }) => chip));
    }
    for (const choice of choices) {
      const { chip, label, count } = chips.get(choice.id);
      chip.setAttribute("aria-pressed", String(view.filter === choice.id));
      label.textContent = choice.label;
      count.textContent = String(choice.count);
    }
    apps = appCounts(model);
    total = model.windows.length;
    appPick.setValue(view.app || EVERY_APP);
    appPick.element.hidden = apps.length < 2;
    orderPick.element.hidden = !model.located;
    orderPick.set(view.order);
  }

  return { element, paint, setTerm: (text) => (search.input.value = text) };
}
