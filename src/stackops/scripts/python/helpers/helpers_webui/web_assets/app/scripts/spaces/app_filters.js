import { h, icon } from "/assets/scripts/dom.js";
import { BUNDLE_TITLES } from "../catalog.js";
import { searchInput } from "../widgets.js";

const CHIP_EDGE = 26;

// The chips above the app grid, one pressed at a time: where an app stands, its category, or one of the installer's bundles.
export function createAppFilters({ onChange }) {
  const element = h("div", { class: "filter-row" });
  let options = [];
  let shown = [];
  let active = null;
  let term = "";

  // Painting replaces every chip, the one just pressed included. Focus goes to the chip that is pressed now, where the row has scrolled to;
  // left alone it fell back to the top of the page. Picking from the search box leaves the focus in the box.
  function pick(option) {
    const focused = element.contains(document.activeElement);
    active = option === active ? options[0] : option;
    paint();
    if (focused) element.querySelector(`[aria-pressed="true"]`).focus({ preventScroll: true });
    onChange();
  }

  const search = searchInput({
    placeholder: "Categories and bundles",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      if (active) paint();
    },
  });
  search.input.addEventListener("keydown", (event) => {
    const first = shown.find((option) => option !== active);
    if (event.key === "Enter" && term && first) pick(first);
  });

  function paint() {
    shown = options.filter((option) => option === active || option.label.toLowerCase().includes(term));
    element.replaceChildren(
      ...shown.map((option) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(option === active), onclick: () => pick(option),
            title: option === active && option !== options[0] ? "Click again to show everything" : option.bundle && "A bundle: apps that are installed together",
          },
          option.bundle && icon("cube", 13),
          h("span", { text: option.label }),
          h("b", { text: String(option.count) }),
        ),
      ),
      ...(shown.some((option) => option.label.toLowerCase().includes(term)) ? [] : [h("span", { class: "filter-none", text: "No category or bundle matches that." })]),
    );
    const row = element.getBoundingClientRect();
    const box = element.querySelector(`[aria-pressed="true"]`).getBoundingClientRect();
    if (box.left < row.left + CHIP_EDGE || box.right > row.right - CHIP_EDGE) element.scrollLeft += box.left - row.left - CHIP_EDGE;
  }

  function load(catalog) {
    const counts = new Map();
    for (const app of catalog.apps) for (const label of app.categories) counts.set(label, (counts.get(label) ?? 0) + 1);
    const installed = catalog.apps.filter((app) => app.installed).length;
    const mine = catalog.apps.filter((app) => app.mine).length;
    const previous = active?.value;
    options = [
      { value: "all", label: "Everything", count: catalog.apps.length, accepts: () => true },
      { value: "installed", label: "Installed", count: installed, accepts: (app) => app.installed },
      { value: "new", label: "Not installed", count: catalog.apps.length - installed, accepts: (app) => !app.installed },
      ...(mine > 0 ? [{ value: "mine", label: "My catalog", count: mine, accepts: (app) => app.mine }] : []),
      ...catalog.categories
        .map((category) => ({ value: category.label, label: category.title, count: counts.get(category.label) ?? 0, accepts: (app) => app.categories.includes(category.label) }))
        .sort((left, right) => right.count - left.count),
      ...catalog.bundles.map((bundle) => {
        const members = new Set(bundle.apps);
        return { value: `bundle:${bundle.name}`, label: BUNDLE_TITLES[bundle.name] ?? bundle.name, count: members.size, bundle: bundle.name, accepts: (app) => members.has(app.name) };
      }),
    ];
    active = options.find((option) => option.value === previous) ?? options[0];
    paint();
  }

  return { element, search: search.element, load, active: () => active };
}
