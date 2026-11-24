import { h } from "/assets/scripts/dom.js";
import { avatar, button, glyphTile, notice } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { arrange } from "./model.js";
import { windowRow } from "./rows.js";

// The open windows, one section per app or, when `view.order` is "size", in one list. `render` rebuilds the rows; `sync` only updates what a
// tick, a running action or the pointer changes, so none of those rebuilds anything.
export function createWindowList(view) {
  const element = h("div", { class: "windows-list" });
  const rows = new Map();
  const groups = [];

  function group(app, members, model) {
    const flat = app === "";
    const box = h("input", { class: "windows-check", type: "checkbox", "data-part": "group", "aria-label": flat ? "Tick every window shown" : `Tick every ${app} window shown` });
    box.addEventListener("change", () => view.setMany(members.map((entry) => entry.id), box.checked));
    const open = members.filter((entry) => !entry.minimized);
    const put = members.length - open.length;
    const all = button({ label: "Minimize all", glyph: "down", small: true, tone: "ghost", title: model.blocked.minimize ?? `Put every ${app} window shown here away`, onclick: () => view.act("minimize", open) });
    all.dataset.part = "minimize-all";
    const items = members.map((entry) => {
      const built = windowRow(entry, { model, view, flat });
      rows.set(entry.id, built);
      return built.row;
    });
    groups.push({ members, open, box, all, blocked: Boolean(model.blocked.minimize) });
    return h(
      "section",
      { class: "windows-group", "data-key": `group ${app}` },
      h(
        "header",
        { class: "windows-group-head" },
        box,
        flat ? glyphTile("chart", 252, 38) : avatar(app, 38),
        h("div", { class: "windows-group-text" }, h("h2", { text: flat ? "Every window, biggest first" : app }), h("p", { text: `${plural(members.length, "window")}${put ? ` · ${put} minimized` : ""}` })),
        !flat && members.length > 1 && all,
      ),
      h("ul", { class: "windows-rows" }, items),
    );
  }

  function sync() {
    for (const [id, { row, box, buttons }] of rows) {
      const working = view.busy.has(id);
      box.checked = view.picked.has(id);
      box.disabled = working;
      row.classList.toggle("picked", box.checked);
      row.classList.toggle("working", working);
      row.classList.toggle("lit-up", view.hovered === id);
      for (const node of buttons) node.disabled = working || node.dataset.blocked === "yes";
    }
    for (const { members, open, box, all, blocked } of groups) {
      const ticked = members.filter((entry) => view.picked.has(entry.id)).length;
      box.checked = ticked === members.length;
      box.indeterminate = ticked > 0 && ticked < members.length;
      all.disabled = blocked || open.length === 0 || open.some((entry) => view.busy.has(entry.id));
    }
  }

  // `shown` is the windows the search and the filters leave in.
  function render(model, shown) {
    const focused = document.activeElement instanceof HTMLElement && element.contains(document.activeElement) ? document.activeElement : null;
    const focusKey = focused?.closest("[data-key]")?.dataset.key;
    rows.clear();
    groups.length = 0;
    const sections = arrange(shown, view.order).map(({ app, members }) => group(app, members, model));
    let empty = null;
    if (model.windows.length === 0) empty = notice({ glyph: "browser", title: "No open windows", body: "Nothing is open on this desktop right now. A window that opens shows up here on its own." });
    else if (shown.length === 0) empty = notice({ glyph: "search", title: "Nothing matches", body: "No window fits that search or filter.", action: button({ label: "Show everything", small: true, onclick: view.clearFilters }) });
    element.replaceChildren(...sections, ...(empty ? [empty] : []));
    sync();
    if (focusKey) element.querySelector(`[data-key="${CSS.escape(focusKey)}"] [data-part="${focused.dataset.part}"]`)?.focus({ preventScroll: true });
  }

  return { element, render, sync };
}
