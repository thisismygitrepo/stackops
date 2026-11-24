import { formatClock, h, icon, toast } from "/assets/scripts/dom.js";
import { recall } from "../../../memory.js";
import { replay } from "../../../motion.js";
import { button } from "../../../widgets.js";
import { createActions } from "./actions.js";
import { windowsApi } from "./api.js";
import { createWindowsHero } from "./hero.js";
import { createWindowList } from "./list.js";
import { createScreenMap } from "./map.js";
import { buildModel, filterChoices, matches } from "./model.js";
import { stateView } from "./states.js";
import { createWindowsToolbar } from "./toolbar.js";
import { createWindowsTray } from "./tray.js";
import { createWatcher } from "./watch.js";
import { MEMORY_ID, WINDOWS_PATH } from "./words.js";

// Open windows: the summary and the map, the filters, the list, and the bar for what is ticked. `takePreset` hands over, once, what the page
// was opened with.
export function createWindowsPage({ tools }, takePreset) {
  let model = null;
  let signature = "";
  let state = { kind: "loading" };
  let shownState = "";
  let trouble = "";
  let checkedAt = 0;

  // What the parts of the page share: what is ticked, what an action is running on, what the filters leave in, and where the pointer is.
  const view = {
    picked: new Set(), busy: new Set(), shown: new Set(), hovered: null, filter: "all", app: "", term: "",
    order: recall(MEMORY_ID).get("order") === "size" ? "size" : "app",
    toggle: (id, on) => view.setMany([id], on),
    setMany(ids, on) {
      for (const id of ids) {
        if (on) view.picked.add(id);
        else view.picked.delete(id);
      }
      sync();
      replay(tray.element, "bump");
    },
    hover(id) {
      view.hovered = id;
      list.sync();
      map.sync();
    },
    act: (name, entries) => act(name, entries),
    changed() {
      toolbar.paint(model);
      paintList();
    },
    clearFilters() {
      Object.assign(view, { filter: "all", app: "", term: "" });
      toolbar.setTerm("");
      view.changed();
    },
  };
  const map = createScreenMap(view);
  const hero = createWindowsHero(map);
  const list = createWindowList(view);
  const toolbar = createWindowsToolbar(view);
  const chosen = () => (model ? model.windows.filter((entry) => view.picked.has(entry.id)) : []);
  const tray = createWindowsTray({
    onMinimize: () => act("minimize", chosen().filter((entry) => !entry.minimized)),
    onRestore: () => act("unminimize", chosen().filter((entry) => entry.minimized)),
    onClose: () => act("close", chosen()),
    onClear: () => view.setMany([...view.picked], false),
  });
  const openPlain = () => tools.open(WINDOWS_PATH, { plain: true });
  const openSettings = () => windowsApi.openPermissionSettings().catch((error) => toast(error.message));
  const stamp = h("span", { class: "windows-stamp", title: "The list is read again every few seconds while this page is open.", hidden: true });
  const troubleHolder = h("div");
  const stateHolder = h("div");
  const refreshButton = button({ label: "Refresh", glyph: "refresh", onclick: refresh });
  refreshButton.classList.add("windows-refresh");
  const element = h(
    "div",
    { class: "windows", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "windows-back", href: "#/machine" }, icon("back", 14), h("span", { text: "Machine" })), h("h1", { text: "Open windows" }), h("p", { text: "Every window on this computer, by app and by screen. Bring one forward, put it away, or close what you are done with." })),
      h("div", { class: "view-actions" }, stamp, button({ label: "All options", glyph: "sliders", title: "Open this tool's plain form, which has every option of the command", onclick: openPlain }), refreshButton),
    ),
    stateHolder, troubleHolder, hero.element, toolbar.element, list.element, tray.element,
  );
  // What reading again cannot change: a system the command does not work on, and a server that has to be restarted.
  const settled = () => (state.kind === "unavailable" && state.reason !== "permission") || (state.kind === "failed" && state.missing);
  const watcher = createWatcher({ element, read: () => windowsApi.list(), onAnswer: answer, idle: settled });
  const act = createActions({ view, watcher, windows: () => model?.windows ?? [], sync });

  function sync() {
    list.sync();
    map.sync();
    const ticked = chosen();
    tray.paint({ chosen: ticked, busy: ticked.some((entry) => view.busy.has(entry.id)), blocked: model?.blocked ?? {} });
  }

  function paintList() {
    const shown = model.windows.filter((entry) => matches(entry, view));
    view.shown = new Set(shown.map((entry) => entry.id));
    list.render(model, shown);
    sync();
  }

  // `changed` says the windows are not what they were at the last reading. Only then is anything rebuilt, so a reading that finds the desktop
  // as it was leaves the page, the pointer and the keyboard's focus alone.
  function paint(changed) {
    const ready = state.kind === "ready";
    for (const part of [hero.element, toolbar.element, list.element]) part.hidden = !ready;
    const stateKey = ready ? "" : JSON.stringify(state);
    if (stateKey !== shownState) {
      shownState = stateKey;
      stateHolder.replaceChildren(...(ready ? [] : [stateView(state, { onOpenSettings: openSettings, onCheck: refresh, onPlain: openPlain })]));
    }
    troubleHolder.replaceChildren(...(ready && trouble ? [h("p", { class: "windows-trouble" }, icon("alert", 15), h("span", { text: `This list has stopped updating. ${trouble}` }))] : []));
    stamp.hidden = checkedAt === 0;
    stamp.replaceChildren(h("i", { class: `windows-dot${trouble ? " stale" : ""}` }), h("span", { text: trouble ? "Not updating" : `Checked at ${formatClock(checkedAt / 1000)}` }));
    if (!ready || !changed) return sync();
    hero.paint(model);
    if (model.located) map.render(model);
    toolbar.paint(model);
    paintList();
  }

  // A tick, an app or a filter that names something no longer there is dropped, so it cannot go on narrowing the list out of sight.
  function prune() {
    const ids = new Set(model.windows.map((entry) => entry.id));
    for (const id of [...view.picked]) if (!ids.has(id)) view.picked.delete(id);
    if (!model.windows.some((entry) => entry.app === view.app)) view.app = "";
    if (!filterChoices(model).some((choice) => choice.id === view.filter)) view.filter = "all";
    if (!model.located) view.order = "app";
  }

  // A reading that fails keeps the list it had and says so above it. With no list yet, the failure takes the page.
  function answer(payload, failure) {
    let changed = false;
    if (failure) {
      if (model) trouble = failure.message;
      else state = { kind: "failed", message: failure.message, missing: failure.status === 404 };
    } else {
      trouble = "";
      checkedAt = Date.now();
      if (payload.available) {
        const next = JSON.stringify(payload);
        changed = next !== signature;
        if (changed) {
          signature = next;
          model = buildModel(payload);
          prune();
        }
        state = { kind: "ready" };
      } else {
        model = null;
        signature = "";
        view.picked.clear();
        state = { kind: "unavailable", reason: payload.reason, launcher: payload.launcher };
      }
    }
    paint(changed);
  }

  async function refresh() {
    refreshButton.classList.add("spinning");
    await watcher.resume();
    refreshButton.classList.remove("spinning");
  }

  function show() {
    const title = takePreset().title;
    if (typeof title === "string" && title.trim()) {
      view.term = title.trim().toLowerCase();
      toolbar.setTerm(title.trim());
      if (model) view.changed();
    }
    watcher.resume();
  }

  paint(false);
  return { element, show };
}
