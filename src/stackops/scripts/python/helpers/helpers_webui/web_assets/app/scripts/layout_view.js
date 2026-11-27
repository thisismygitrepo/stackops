import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { openDialog } from "./overlays.js";
import { avatar, button, copyChip, pill } from "./widgets.js";
import { plural } from "./words.js";

const DEFAULT_ARRANGEMENT = "grid";
const LAYOUT_HINT = "Off means this layout is skipped when a whole file of layouts is launched at once. It still starts when it is launched by name, as it is from here.";
const TAB_HINT = "Off means the layout opens without this tab. The tab still opens when it is named with --choose-tabs.";
const PANE_HINT = "Off means the tab opens without this pane.";

// A layout, a tab or a pane is on unless its `enabled` says false.
export const isOn = (entry) => entry.enabled !== false;

// What a launch opens: the tabs that are on, each with its panes that are on. A tab left with no pane is not opened.
export const launchTabs = (layout) => layout.tabs.map((tab) => ({ ...tab, panes: tab.panes.filter(isOn) })).filter((tab) => isOn(tab) && tab.panes.length > 0);

// "3 tabs · 5 panes", or "2 of 3 tabs · 3 of 5 panes" when some of them are switched off.
export function layoutSize(layout) {
  const open = launchTabs(layout);
  const part = (count, total, word) => (count === total ? plural(total, word) : `${count} of ${plural(total, word)}`);
  return `${part(open.length, layout.tab_count, "tab")} · ${part(open.reduce((sum, tab) => sum + tab.panes.length, 0), layout.pane_count, "pane")}`;
}

// Splits panes the way the terminal does when it launches: columns share one row, rows get one each, a grid uses rows of ⌈√n⌉.
function paneRows(panes, arrangement = DEFAULT_ARRANGEMENT) {
  const count = panes.length;
  const perRow = arrangement === "columns" ? count : arrangement === "rows" ? 1 : Math.ceil(Math.sqrt(count));
  return Array.from({ length: Math.ceil(count / perRow) }, (_, row) => panes.slice(row * perRow, (row + 1) * perRow));
}

// The panes of a tab that are on, drawn small.
export function tabMap(tab, firstIndex = 0) {
  let index = firstIndex;
  return h("span", { class: "tab-map", "aria-hidden": "true" }, paneRows(tab.panes.filter(isOn), tab.arrangement).map((row) => h("span", {}, row.map(() => h("i", { style: `--i:${index++}` })))));
}

// The switch of a layout, of one of its tabs (named by its place) or of one pane of that tab. It writes to the file the list read the layout
// from, and the entry changes here once the file has. `onChange` then redraws whatever shows the entry, also after a refusal, which may
// mean the file is no longer what is on screen.
export function entrySwitch({ layout, tabIndex = null, pane = null, label, onChange }) {
  const entry = pane ?? (tabIndex === null ? layout : layout.tabs[tabIndex]);
  const control = h("button", { class: "entry-switch", type: "button", role: "switch", "aria-checked": String(isOn(entry)), "aria-label": label, title: pane ? PANE_HINT : tabIndex === null ? LAYOUT_HINT : TAB_HINT }, h("i", { class: "switch" }));
  control.addEventListener("click", async (event) => {
    event.stopPropagation();
    // Not `disabled`, which would take the keyboard's place away from the switch while the file is written.
    if (control.getAttribute("aria-busy")) return;
    control.setAttribute("aria-busy", "true");
    const enabled = !isOn(entry);
    try {
      await request("POST", "/api/terminal/layouts/enabled", { file: layout.source_file, layout: layout.name, tab_index: tabIndex, tab_name: tabIndex === null ? null : layout.tabs[tabIndex].tabName, pane: pane?.paneName ?? null, enabled });
      entry.enabled = enabled;
    } catch (error) {
      toast(error.message);
    }
    onChange();
  });
  return control;
}

// `ask` is the "Ask an agent" button for this layout, from the page that knows which file holds it. `onChange` hears of every switch
// flipped in here, so the page can read the list again.
export function openLayoutView({ layout, onLaunch, onTune, onEdit, onChange, ask }) {
  const dialog = openDialog({ label: `Layout ${layout.name}`, size: "layout-view" });
  const switchable = Boolean(layout.source_file);
  const size = h("span");
  const layoutState = h("div", { class: "layout-state" });
  const tabs = h("div", { class: "term-tabs", role: "tablist" });
  const tabState = h("div", { class: "term-state" });
  const screen = h("div", { class: "term-screen", role: "tabpanel" });
  const caption = h("p", { class: "dim" });
  let current = 0;

  // Drawing again makes every switch anew, so the one that was pressed is found again by its label and keeps the keyboard's place.
  const changed = () => {
    const held = document.activeElement?.getAttribute("aria-label");
    draw();
    [...dialog.panel.querySelectorAll(".entry-switch")].find((item) => item.getAttribute("aria-label") === held)?.focus();
    onChange();
  };

  const paneCell = (pane, index) =>
    h(
      "article",
      { class: `term-pane${isOn(pane) ? "" : " off"}`, style: `--i:${index}` },
      h(
        "header",
        {},
        h("strong", { text: pane.paneName }),
        h("code", { title: "Starts in this folder", text: tildify(pane.startDir, state.boot.home) }),
        switchable && entrySwitch({ layout, tabIndex: current, pane, label: `Pane ${pane.paneName} opens with its tab`, onChange: changed }),
      ),
      pane.command.trim() ? copyChip(pane.command) : h("span", { class: "term-idle", text: "Opens an empty shell" }),
    );

  // The panes that are on fill the screen the way a launch lays them out; the ones that are off wait in a row of their own under them.
  function draw() {
    const tab = layout.tabs[current];
    const open = tab.panes.filter(isOn);
    const parked = tab.panes.filter((pane) => !isOn(pane));
    const rows = paneRows(open, tab.arrangement);
    const opens = isOn(tab) && open.length > 0;
    let seen = 0;
    size.textContent = layoutSize(layout);
    layoutState.replaceChildren(h("span", { text: isOn(layout) ? "On" : "Off" }), entrySwitch({ layout, label: `Layout ${layout.name} is on`, onChange: changed }));
    tabs.replaceChildren(
      ...layout.tabs.map((item, index) =>
        h(
          "button",
          { class: `term-tab${isOn(item) && item.panes.some(isOn) ? "" : " off"}`, type: "button", role: "tab", "aria-selected": String(index === current), onclick: () => select(index) },
          tabMap(item),
          h("span", { text: item.tabName }),
          item.panes.filter(isOn).length > 1 && h("b", { text: String(item.panes.filter(isOn).length) }),
        ),
      ),
    );
    tabs.children[current].scrollIntoView({ block: "nearest", inline: "nearest" });
    tabState.replaceChildren(
      entrySwitch({ layout, tabIndex: current, label: `Tab ${tab.tabName} opens with the layout`, onChange: changed }),
      h("span", { text: !isOn(tab) ? "Off. The layout opens without this tab." : open.length > 0 ? "Opens with the layout" : "All of its panes are off, so the layout opens without this tab." }),
    );
    screen.className = `term-screen${opens ? "" : " off"}`;
    screen.replaceChildren(...[...rows, parked].filter((row) => row.length > 0).map((row) => h("div", { class: `term-row${row === parked ? " parked" : ""}` }, row.map((pane) => paneCell(pane, seen++)))));
    const shape = open.length <= 1 ? "" : rows.length === 1 ? " side by side" : rows.length === open.length ? " stacked" : " in a grid";
    caption.textContent = `Tab ${current + 1} of ${layout.tabs.length} · ${plural(open.length, "pane")}${shape}${parked.length > 0 ? ` · ${parked.length} off` : ""}`;
  }

  function select(index) {
    current = index;
    draw();
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
        h("p", {}, size, pill(layout.selector.split(":")[0], ""), layout.source_file && copyChip(layout.source_file, tildify(layout.source_file, state.boot.home))),
      ),
      switchable && layoutState,
      h("button", { class: "icon-btn", type: "button", "aria-label": "Close", onclick: () => dialog.close() }, icon("close", 16)),
    ),
    h("div", { class: "term" }, h("div", { class: "term-bar" }, h("span", { class: "term-dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")), tabs), switchable && tabState, screen),
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
