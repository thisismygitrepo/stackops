import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { openDialog } from "./overlays.js";
import { avatar, button, copyChip, pill } from "./widgets.js";
import { plural } from "./words.js";

const DEFAULT_ARRANGEMENT = "grid";

// Splits a tab's panes the way the terminal does when it launches: columns share one row, rows get one each, a grid uses rows of ⌈√n⌉.
function paneRows(tab) {
  const count = tab.panes.length;
  const arrangement = tab.arrangement ?? DEFAULT_ARRANGEMENT;
  const perRow = arrangement === "columns" ? count : arrangement === "rows" ? 1 : Math.ceil(Math.sqrt(count));
  return Array.from({ length: Math.ceil(count / perRow) }, (_, row) => tab.panes.slice(row * perRow, (row + 1) * perRow));
}

export function tabMap(tab, firstIndex = 0) {
  let index = firstIndex;
  return h("span", { class: "tab-map", "aria-hidden": "true" }, paneRows(tab).map((row) => h("span", {}, row.map(() => h("i", { style: `--i:${index++}` })))));
}

// `ask` is the "Ask an agent" button for this layout, from the page that knows which file holds it.
export function openLayoutView({ layout, onLaunch, onTune, onEdit, ask }) {
  const dialog = openDialog({ label: `Layout ${layout.name}`, size: "layout-view" });
  const tabButtons = layout.tabs.map((tab, index) =>
    h("button", { class: "term-tab", type: "button", role: "tab", onclick: () => select(index) }, tabMap(tab), h("span", { text: tab.tabName }), tab.panes.length > 1 && h("b", { text: String(tab.panes.length) })),
  );
  const screen = h("div", { class: "term-screen", role: "tabpanel" });
  const caption = h("p", { class: "dim" });
  let current = 0;

  const paneCell = (pane, index) =>
    h(
      "article",
      { class: "term-pane", style: `--i:${index}` },
      h("header", {}, h("strong", { text: pane.paneName }), h("code", { title: "Starts in this folder", text: tildify(pane.startDir, state.boot.home) })),
      pane.command.trim() ? copyChip(pane.command) : h("span", { class: "term-idle", text: "Opens an empty shell" }),
    );

  function select(index) {
    current = index;
    const tab = layout.tabs[index];
    const rows = paneRows(tab);
    let seen = 0;
    tabButtons.forEach((item, position) => item.setAttribute("aria-selected", String(position === index)));
    tabButtons[index].scrollIntoView({ block: "nearest", inline: "nearest" });
    screen.replaceChildren(...rows.map((row) => h("div", { class: "term-row" }, row.map((pane) => paneCell(pane, seen++)))));
    const shape = tab.panes.length === 1 ? "" : rows.length === 1 ? " side by side" : rows.length === tab.panes.length ? " stacked" : " in a grid";
    caption.textContent = `Tab ${index + 1} of ${layout.tabs.length} · ${plural(tab.panes.length, "pane")}${shape}`;
  }

  const act = (action) => () => {
    dialog.close();
    action();
  };
  dialog.body.append(
    h(
      "header",
      { class: "layout-head" },
      avatar(layout.name, 52),
      h(
        "div",
        { class: "layout-title" },
        h("h1", { text: layout.name }),
        h("p", {}, h("span", { text: `${plural(layout.tab_count, "tab")} · ${plural(layout.pane_count, "pane")}` }), pill(layout.selector.split(":")[0], ""), layout.source_file && copyChip(layout.source_file, tildify(layout.source_file, state.boot.home))),
      ),
      h("button", { class: "icon-btn", type: "button", "aria-label": "Close", onclick: () => dialog.close() }, icon("close", 16)),
    ),
    h("div", { class: "term" }, h("div", { class: "term-bar" }, h("span", { class: "term-dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")), h("div", { class: "term-tabs", role: "tablist" }, tabButtons)), screen),
    h(
      "footer",
      { class: "layout-foot" },
      caption,
      layout.tabs.length > 1 && h("span", { class: "dim layout-keys" }, h("kbd", { text: "←" }), h("kbd", { text: "→" }), "switch tabs"),
      h("span", { class: "spacer" }),
      ask,
      onEdit && button({ label: "Edit", glyph: "terminal", title: "Opens the file that holds this layout in a text editor inside the activity panel. It is checked when you close the editor.", onclick: act(onEdit) }),
      button({ label: "Launch with options", glyph: "sliders", onclick: act(onTune) }),
      button({ label: "Launch", glyph: "play", tone: "primary", onclick: act(onLaunch) }),
    ),
  );
  dialog.panel.addEventListener("keydown", (event) => {
    const step = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (step === 0) return;
    event.preventDefault();
    select((current + step + layout.tabs.length) % layout.tabs.length);
  });
  select(0);
}
