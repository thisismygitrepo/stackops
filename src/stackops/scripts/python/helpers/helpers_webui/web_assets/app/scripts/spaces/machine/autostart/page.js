import { formatClock, h } from "/assets/scripts/dom.js";
import { agentButton } from "../../../agent_ask.js";
import { staleKeeper } from "../../../data.js";
import { recall, remember } from "../../../memory.js";
import { rise } from "../../../motion.js";
import { backLink } from "../../../space_kit.js";
import { button, callout, notice, skeleton } from "../../../widgets.js";
import { createActions, createOutcome } from "./actions.js";
import { readStartup } from "./api.js";
import { openDetail } from "./detail.js";
import { buildModel, emptyPicks, groupsOf, inUniverse, matching } from "./model.js";
import { createList } from "./rows.js";
import { createSummary } from "./summary.js";
import { createToolbar } from "./toolbar.js";
import { COMMAND, GROUPINGS, KINDS, ORDERS, SCOPES, systemName } from "./words.js";

const MEMORY_ID = "machine autostart";
// How old the list may be when the page is come back to before it is read again without being asked.
const FRESH_MILLISECONDS = 30000;

// Startup programs: everything that starts on its own, read on arrival, drawn by when it starts, whose it is and what kind of thing it is,
// narrowed by clicking those, and turned off or removed where it belongs to the person. `takeArrival` hands over what the page was opened with.
export function createStartupPage({ activity, tools }, takeArrival) {
  const kept = recall(MEMORY_ID);
  const oneOf = (choices, value, fallback) => (choices.some(([id]) => id === value) ? value : fallback);
  const view = { system: kept.get("system") === "on", term: "", picks: emptyPicks(), group: oneOf(GROUPINGS, kept.get("group"), "when"), order: oneOf(ORDERS, kept.get("order"), "name"), shown: new Map(), busy: new Set() };
  let model = null;
  let problem = null;
  let ticket = 0;
  let entered = false;

  const keep = () => remember(MEMORY_ID, new Map([["group", view.group], ["order", view.order], ...(view.system ? [["system", "on"]] : [])]));

  function changed() {
    view.shown.clear();
    keep();
    paint();
  }

  function toggle(facet, value) {
    if (!view.picks[facet].delete(value)) view.picks[facet].add(value);
    changed();
  }

  // One stretch of the picture stands for a moment and a way of starting together. A second click on it takes both off again.
  function pickCell(scope, manner) {
    const { scopes, manners } = view.picks;
    const alone = scopes.size === 1 && scopes.has(scope) && manners.size === 1 && manners.has(manner);
    scopes.clear();
    manners.clear();
    if (!alone) {
      scopes.add(scope);
      manners.add(manner);
    }
    changed();
  }

  function setSystem(on, whose) {
    view.system = on;
    if (!on) view.picks.whose.delete("system");
    if (whose) view.picks.whose = new Set([whose]);
    changed();
  }

  function clear() {
    view.term = "";
    view.picks = emptyPicks();
    changed();
  }

  // What another view opened the page with, by the command's parameter names. It replaces what the list was narrowed to.
  function applyPreset(preset) {
    const kinds = [preset.category ?? []].flat().map((option) => Object.keys(KINDS).find((id) => KINDS[id].option === String(option).toLowerCase())).filter(Boolean);
    const term = String(preset.name ?? preset.source ?? "").trim();
    const everything = preset.show_all === true || preset.show_all === "true";
    if (!everything && kinds.length === 0 && !SCOPES[preset.scope] && !term) return;
    view.term = term;
    view.picks = emptyPicks();
    for (const id of kinds) view.picks.kinds.add(id);
    if (SCOPES[preset.scope]) view.picks.scopes.add(preset.scope);
    view.system = view.system || everything || kinds.some((id) => id === "system-os");
    if (model) changed();
  }

  const stamp = h("span", { class: "autostart-stamp" });
  const refresh = button({ label: "Refresh", glyph: "refresh", onclick: () => keeper.load() });
  const outcome = createOutcome();
  const summary = createSummary({ view, toggle, pickCell, setSystem });
  const toolbar = createToolbar({ view, onChange: changed, setSystem, clear });
  const actions = createActions({ view, repaint: () => paint(), reload: () => keeper.load(true), outcome });
  const handlers = {
    ...actions,
    open: (entry) => openDetail({ activity, entry, platform: model.platform, tools, handlers }),
    more(group, limit) {
      view.shown.set(group, limit);
      paint();
    },
  };
  const list = createList({ view, handlers });
  const waiting = h("div", { class: "autostart-waiting" }, h("div", { class: "autostart-cards" }, skeleton(4, "card")), skeleton(6, "row"));
  const problemHolder = h("div");
  const notes = h("div", { class: "autostart-notes" });
  const empty = h("div");

  function problemNotice() {
    const again = button({ label: "Try again", glyph: "refresh", small: true, onclick: () => keeper.load() });
    const plain = button({ label: "Open the plain list", glyph: "terminal", small: true, onclick: () => tools.open(COMMAND, { plain: true }) });
    if (problem.kind === "unavailable") return notice({ glyph: "power", title: "What starts on its own cannot be read on this system", body: problem.message, action: again });
    // The running server is older than this page: it has no such address yet.
    if (problem.status === 404) return notice({ glyph: "refresh", title: "StackOps needs a restart to show this page", body: "This page is newer than the StackOps server that is running. Restart StackOps, then open the page again. Until then the plain list still works.", action: h("div", { class: "dialog-actions" }, plain, again) });
    return notice({ glyph: "alert", tone: "bad", title: "The startup programs could not be read", body: problem.message, action: h("div", { class: "dialog-actions" }, plain, again) });
  }

  function emptyNotice(universe) {
    const standard = model.entries.filter((entry) => entry.stock).length;
    const system = systemName(model.platform);
    if (universe.length === 0) {
      const hidden = !view.system && standard > 0;
      return notice({
        glyph: "power", title: hidden ? "Nothing was added to what starts on its own" : "Nothing starts on its own",
        body: hidden ? `Only the ${standard.toLocaleString()} standard parts of ${system} start with this computer.` : "No services or programs are set to start by themselves.",
        action: hidden && button({ label: "Show them", small: true, onclick: () => setSystem(true) }),
      });
    }
    const beyond = view.system ? 0 : matching(model, { ...view, system: true }).length;
    return notice({
      glyph: "search", title: "Nothing matches", body: beyond > 0 ? `Nothing in the list fits. ${beyond.toLocaleString()} of the standard parts of ${system} ${beyond === 1 ? "does" : "do"}.` : "No startup program fits these filters.",
      action: h("div", { class: "dialog-actions" }, beyond > 0 && button({ label: "Include them", small: true, onclick: () => setSystem(true) }), button({ label: "Clear filters", small: true, onclick: clear })),
    });
  }

  function paint(entering = false) {
    const ready = model !== null;
    stamp.textContent = ready ? `Read at ${formatClock(model.readAt / 1000)}` : "";
    problemHolder.replaceChildren(...(problem ? [problemNotice()] : []));
    waiting.hidden = ready || problem !== null;
    for (const part of [summary.element, toolbar.element, notes, list.element, empty]) part.hidden = !ready;
    if (!ready) return;
    const universe = inUniverse(model, view);
    const found = matching(model, view);
    summary.paint(model);
    if (entering) rise(summary.element);
    toolbar.paint(model, found.length);
    // With nothing to draw or to narrow, the picture and the toolbar make way for the one thing there is to say.
    summary.element.hidden = toolbar.element.hidden = universe.length === 0;
    notes.replaceChildren(...model.notes.map((note) => callout({ tone: "warn", title: "Login items are not in this list", text: note })));
    list.render(groupsOf(found, view, model.platform), { platform: model.platform, entering });
    empty.replaceChildren(...(found.length === 0 ? [emptyNotice(universe)] : []));
  }

  // `quiet` is for a read nobody asked for: when it fails the list stays as it was.
  async function load(quiet = false) {
    const mine = (ticket += 1);
    refresh.disabled = true;
    try {
      const answer = await readStartup();
      if (mine !== ticket) return;
      model = answer.unavailable ? null : buildModel(answer);
      problem = answer.unavailable ? { kind: "unavailable", ...answer.unavailable } : null;
    } catch (error) {
      if (mine !== ticket) return;
      if (!quiet || model === null) {
        model = null;
        problem = { kind: "failed", message: error.message, status: error.status };
        keeper.spoil();
      }
    }
    refresh.disabled = false;
    paint(!entered && model !== null);
    entered = entered || model !== null;
  }

  const element = h(
    "div",
    { class: "autostart", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, backLink("#/machine", "Machine"), h("h1", { text: "Startup programs" }), h("p", { text: "The services and programs that start on their own, when this computer starts or when you sign in." })),
      h("div", { class: "view-actions" }, stamp, agentButton(activity, { commands: [COMMAND] }), button({ label: "All options", glyph: "sliders", title: "The command's own form, with every option it has", onclick: () => tools.open(COMMAND, { plain: true }) }), refresh),
    ),
    problemHolder,
    waiting,
    summary.element,
    outcome.element,
    toolbar.element,
    notes,
    list.element,
    empty,
  );
  const keeper = staleKeeper(element, load);
  paint();
  return {
    element,
    show() {
      applyPreset(takeArrival());
      if (model && Date.now() - model.readAt > FRESH_MILLISECONDS) keeper.load(true);
      else keeper.ensure();
    },
  };
}
