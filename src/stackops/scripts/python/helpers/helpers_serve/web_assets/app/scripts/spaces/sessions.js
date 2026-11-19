import { h, toast } from "/assets/scripts/dom.js";
import { query } from "../data.js";
import { openLayoutView, tabMap } from "../layout_view.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createView, editButton, editFile, toolButton, toolGrid } from "../space_kit.js";
import { button, notice, pill, sectionHead } from "../widgets.js";
import { plural } from "../words.js";
import { createRunningPanel } from "./sessions_running.js";

const PREVIEW_TABS = 8;
const MY_LAYOUTS = { title: "your layouts", kind: "layouts" };
const TERMINAL_TOOLS = ["devops config setup multiplexer", "devops config terminal config-shell", "devops config terminal starship-theme", "devops config terminal wezterm-theme", "devops config terminal ghostty-theme"];

export function createSessionsSpace({ activity, tools }) {
  let selectors = [];
  // The selector, not the name: a name can be in your layouts and in a project's at once, and only the selector tells them apart.
  const launch = (layout) =>
    activity.start({ title: `Launch ${layout.name}`, emoji: "🏃", arguments: ["terminal", "run", "--choose-layouts", layout.selector], interactive: true, reveal: true }).catch((error) => toast(error.message));

  function layoutCard(layout) {
    let cells = 0;
    const maps = layout.tabs.slice(0, PREVIEW_TABS).map((tab) => {
      const map = tabMap(tab, cells);
      cells += tab.panes.length;
      return map;
    });
    const launchButton = button({ label: "Launch", glyph: "play", small: true, tone: "primary", onclick: () => launch(layout) });
    const view = () =>
      openLayoutView({
        layout, onLaunch: () => launch(layout), onTune: () => tools.open("terminal run", { preset: { choose_layouts: layout.selector } }),
        onEdit: layout.source_file && (() => editFile(activity, { title: layout.selector.startsWith("user:") ? MY_LAYOUTS.title : "this project's layouts", kind: "layouts", path: layout.source_file })),
      });
    const card = h(
      "article",
      { class: "layout-card lit", tabindex: "0", title: "See what this layout opens" },
      h("div", { class: "layout-preview", "aria-hidden": "true" }, maps, layout.tabs.length > PREVIEW_TABS && h("b", { text: `+${layout.tabs.length - PREVIEW_TABS}` })),
      h("h3", { text: layout.name }),
      h("p", { class: "dim", text: `${plural(layout.tab_count, "tab")} · ${plural(layout.pane_count, "pane")}` }),
      h("footer", {}, pill(layout.selector.split(":")[0], ""), launchButton),
    );
    card.addEventListener("click", (event) => !launchButton.contains(event.target) && view());
    card.addEventListener("keydown", (event) => event.key === "Enter" && event.target === card && view());
    return card;
  }

  const layouts = createLivePanel({
    title: "Saved layouts", path: "terminal list", extra: ["--json", "--tabs"], locked: ["show_tabs", "show_stats"], skeletonShape: "card",
    actions: [editButton(activity, MY_LAYOUTS, { label: "Edit my layouts", small: true })],
    render: (data, { setCount }) => {
      const items = data?.layouts ?? [];
      selectors = items.map((layout) => layout.selector);
      setCount(items.length ? plural(items.length, "layout") : "");
      // The CLI's template command writes into the working folder, which this panel does not read; editing your layouts file is what puts one here.
      if (items.length === 0) return notice({ glyph: "layers", title: "No saved layouts", body: "A layout is a set of tabs and panes you can start in one click. Your layouts file starts from an example the first time you edit it.", action: editButton(activity, MY_LAYOUTS, { label: "Edit my layouts" }) });
      return rise(h("div", { class: "card-grid" }, items.map(layoutCard)));
    },
  });

  const running = createRunningPanel({ activity, savedLayouts: () => selectors });

  // Filled in to land in your layouts file, which "Saved layouts" reads; left alone, the command writes a file into the working folder.
  const saveAll = async () => tools.open("terminal export", { preset: { all_sessions: "on", output_path: (await query(["terminal", "path"])).json.user.path, merge: "on" } });

  const element = createView(
    {
      title: "Sessions", lede: "Start a saved workspace, or see what is already running.",
      actions: [button({ label: "Save current as layout", glyph: "plus", title: "Save every running session as a layout of the same name", onclick: saveAll }), toolButton(tools, "terminal run", { label: "Launch with options", glyph: "sliders" })],
    },
    layouts.element,
    running.element,
    h("section", { class: "block" }, sectionHead("Terminal setup"), toolGrid(tools, TERMINAL_TOOLS)),
  );
  return {
    element,
    show() {
      layouts.ensure();
      running.ensure();
    },
  };
}
