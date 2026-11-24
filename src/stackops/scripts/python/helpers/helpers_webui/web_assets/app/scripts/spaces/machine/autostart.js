import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../../live_panel.js";
import { dataTable } from "../../result_view.js";
import { notice } from "../../widgets.js";
import { plural, titleOf } from "../../words.js";

const PATH = "utils machine autostart";
const HASH = "#/machine/autostart";

// What starts on its own, in place of the form made from the options of `utils machine autostart`: the list on arrival, a box to filter it,
// and the command's choices in the panel's head. A page of its own at #/machine/autostart behind a card on Machine, like the tools beside
// it, because the list runs to dozens of rows and on Machine itself it filled the page under the cards.
// Nothing is taken from a preset: the panel comes back with the choices it was left with.
export function open() {
  location.hash = HASH;
}

export function createPart() {
  const panel = createLivePanel({
    // Matching by name or source is left to the table's own filter box, which is already on the page.
    title: "Starts automatically", path: PATH, extra: ["--json"], locked: ["name", "source"], surface: { show_all: "Include system services" },
    render: (data, { setCount }) => {
      const items = Array.isArray(data) ? data : [];
      setCount(items.length ? plural(items.length, "program") : "");
      if (items.length === 0) return notice({ glyph: "bolt", title: "Nothing starts on its own", body: "No services or programs are set to start automatically." });
      return dataTable(items.map((item) => ({ name: item.name, what_it_does: item.description, category: item.category, scope: item.scope, source: item.source, built_in: item.stock })));
    },
  });
  const element = h(
    "div",
    {},
    h(
      "header",
      { class: "view-head" },
      h(
        "div",
        { class: "view-title" },
        h("a", { class: "part-back", href: "#/machine" }, icon("back", 14), h("span", { text: "Machine" })),
        h("h1", { text: titleOf(state.nodes.get(PATH)) }),
        h("p", { text: "The services and programs that start on their own, when this computer starts or when you sign in." }),
      ),
    ),
    panel.element,
  );
  return { element, show: () => panel.ensure() };
}
