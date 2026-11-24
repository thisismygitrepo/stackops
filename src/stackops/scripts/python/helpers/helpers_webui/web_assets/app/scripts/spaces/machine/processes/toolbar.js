import { h, icon } from "/assets/scripts/dom.js";
import { searchInput, segmented } from "../../../widgets.js";
import { isNarrowed } from "./model.js";
import { statusOf } from "./words.js";

const FLAG_CHIPS = [
  ["cpu", "Heavy on CPU", "Using a quarter of a processor core or more"],
  ["memory", "Heavy on memory", "Using 1 GB of memory or more"],
  ["ports", "Listening on a port", "Waiting for connections on a network port"],
  ["apps", "Apps and tools", "Leaves out the parts of the operating system"],
];

function chip(label, title, onclick) {
  const count = h("b");
  const element = h("button", { class: "chip-button", type: "button", title, "aria-pressed": "false", onclick }, h("span", { text: label }), count);
  return { element, count };
}

// Whose processes, which ones, and how they are laid out. `filters` and `view` are the page's own; a control changes them and calls `onChange`.
// The chips are made once and their counts filled in at every reading, so a chip is never replaced while it is being pressed.
export function createToolbar({ filters, view, onChange }) {
  const scopePick = segmented([["mine", "Mine"], ["all", "Everyone's"]], (scope) => {
    filters.scope = scope;
    onChange();
  });
  const modePick = segmented([["list", "List"], ["tree", "Tree"]], (mode) => {
    view.mode = mode;
    onChange();
  });
  modePick.element.title = "List shows every process in one list. Tree puts each process under the one that started it.";
  const search = searchInput({
    placeholder: "Find by name, command, ID, port or user",
    oninput: (value) => {
      filters.term = value.trim();
      onChange();
    },
  });
  const flagChips = FLAG_CHIPS.map(([flag, label, title]) => ({
    flag,
    ...chip(label, title, () => {
      if (filters.flags.has(flag)) filters.flags.delete(flag);
      else filters.flags.add(flag);
      onChange();
    }),
  }));
  const statusChips = new Map();
  const statusRow = h("div", { class: "chip-row" });
  const givenRow = h("div", { class: "procs-given", hidden: true });
  const clear = h("button", { class: "link procs-clear", type: "button", text: "Clear filters", onclick: () => reset() });
  const element = h(
    "div",
    { class: "procs-tools" },
    h("div", { class: "procs-tools-row" }, scopePick.element, modePick.element, h("span", { class: "spacer" }), search.element),
    givenRow,
    h("div", { class: "procs-tools-row" }, h("div", { class: "chip-row" }, flagChips.map((item) => item.element)), h("i", { class: "procs-divider" }), statusRow, clear),
  );
  let givenShown = null;

  function reset() {
    Object.assign(filters, { term: "", status: "", given: [] });
    filters.flags.clear();
    search.input.value = "";
    onChange();
  }

  function paintGiven() {
    if (givenShown === filters.given) return;
    givenShown = filters.given;
    givenRow.hidden = filters.given.length === 0;
    givenRow.replaceChildren(
      h("span", { class: "dim", text: "Opened for" }),
      ...filters.given.map((condition) =>
        h(
          "button",
          {
            class: "chip-button procs-given-chip", type: "button", "aria-pressed": "true", title: "Take this filter off",
            onclick: () => {
              filters.given = filters.given.filter((other) => other !== condition);
              onChange();
            },
          },
          h("span", { text: condition.label }),
          icon("close", 12),
        ),
      ),
    );
  }

  function paint(counts) {
    scopePick.set(filters.scope);
    scopePick.label([`Mine · ${counts.mine.toLocaleString()}`, `Everyone's · ${counts.all.toLocaleString()}`]);
    modePick.set(view.mode);
    if (search.input.value.trim() !== filters.term) search.input.value = filters.term;
    for (const { flag, element: button, count } of flagChips) {
      button.setAttribute("aria-pressed", String(filters.flags.has(flag)));
      count.textContent = counts.flags[flag].toLocaleString();
    }
    // A state that no process is in any more keeps its chip while it is the chosen one, so it can still be taken off.
    const listed = new Map(counts.statuses);
    if (filters.status && !listed.has(filters.status)) listed.set(filters.status, 0);
    let changed = false;
    for (const [status, item] of statusChips) {
      if (listed.has(status)) continue;
      item.element.remove();
      statusChips.delete(status);
    }
    for (const [status, total] of listed) {
      if (!statusChips.has(status)) {
        changed = true;
        statusChips.set(
          status,
          chip(statusOf(status).label, statusOf(status).hint, () => {
            filters.status = filters.status === status ? "" : status;
            onChange();
          }),
        );
      }
      const item = statusChips.get(status);
      item.element.setAttribute("aria-pressed", String(filters.status === status));
      item.count.textContent = total.toLocaleString();
    }
    // Only when a state came into the list: putting the chips in order moves them, and a chip must not move while it is being pressed.
    if (changed) statusRow.append(...[...listed.keys()].map((status) => statusChips.get(status).element));
    clear.hidden = !isNarrowed(filters);
    paintGiven();
  }

  return { element, paint, reset };
}
