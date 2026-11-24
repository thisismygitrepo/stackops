import { h, icon } from "/assets/scripts/dom.js";
import { searchInput, segmented } from "../../../widgets.js";
import { isNarrowed } from "./model.js";
import { GROUPINGS, KINDS, MANNERS, ORDERS, SCOPES, STATES, systemName, whoseWords } from "./words.js";

const amount = (count) => count.toLocaleString();

// Search, the switch for the standard parts of the system, how the list is laid out, and what it is narrowed to right now. The picture above
// is where a filter is put on; here each one is named and can be taken off. `view` is the page's own: a control changes it and calls `onChange`.
export function createToolbar({ view, onChange, setSystem, clear }) {
  const search = searchInput({
    placeholder: "Find by name, what it runs, who it belongs to",
    oninput: (value) => {
      view.term = value;
      onChange();
    },
  });
  const systemSwitch = h("button", { class: "mini-toggle", type: "button", role: "switch", "aria-checked": "false", onclick: () => setSystem(!view.system) }, h("i", { class: "switch" }), h("span"));
  const groupPick = segmented(GROUPINGS, (group) => {
    view.group = group;
    onChange(true);
  });
  const orderPick = segmented(ORDERS, (order) => {
    view.order = order;
    onChange(true);
  });
  const chips = h("div", { class: "chip-row" });
  const found = h("span", { class: "dim" });
  const narrowed = h("div", { class: "autostart-narrowed" }, chips, found, h("button", { class: "link", type: "button", text: "Clear filters", onclick: clear }));
  const element = h(
    "div",
    { class: "autostart-tools" },
    h("div", { class: "autostart-tools-row" }, search.element, h("span", { class: "spacer" }), systemSwitch),
    h("div", { class: "autostart-tools-row" }, h("label", { class: "autostart-pick" }, h("span", { text: "Group by" }), groupPick.element), h("span", { class: "spacer" }), h("label", { class: "autostart-pick" }, h("span", { text: "Sort by" }), orderPick.element)),
    narrowed,
  );

  function paint(model, matched) {
    const standard = model.entries.filter((entry) => entry.stock).length;
    const labels = { scopes: (id) => SCOPES[id].label, manners: (id) => MANNERS[id].label, whose: (id) => whoseWords(model.platform)[id].label, kinds: (id) => KINDS[id].long, states: (id) => STATES[id].label };
    if (search.input.value !== view.term) search.input.value = view.term;
    systemSwitch.hidden = standard === 0;
    systemSwitch.setAttribute("aria-checked", String(view.system));
    systemSwitch.title = `Also list the ${amount(standard)} services that come with ${systemName(model.platform)}`;
    systemSwitch.lastChild.textContent = `Standard parts of ${systemName(model.platform)}`;
    groupPick.set(view.group);
    orderPick.set(view.order);
    narrowed.hidden = !isNarrowed(view);
    found.textContent = `${amount(matched)} ${matched === 1 ? "fits" : "fit"}`;
    chips.replaceChildren(
      ...Object.entries(view.picks).flatMap(([facet, picked]) =>
        [...picked].map((id) =>
          h(
            "button",
            {
              class: "chip-button autostart-chip", type: "button", "aria-pressed": "true", title: "Take this filter off",
              onclick: () => {
                picked.delete(id);
                onChange();
              },
            },
            h("span", { text: labels[facet](id) }),
            icon("close", 12),
          ),
        ),
      ),
    );
  }

  return { element, paint };
}
