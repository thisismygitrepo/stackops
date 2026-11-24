import { h, icon, toast } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { markStale, staleKeeper } from "../../data.js";
import { rise } from "../../motion.js";
import { editButton } from "../../space_kit.js";
import { button, notice, sectionHead, skeleton } from "../../widgets.js";
import { plural, titleOf } from "../../words.js";
import { multiplexerCard } from "./multiplexer/card.js";
import { defaultTile } from "./multiplexer/defaults.js";
import { ADDRESS, API, LEDE, PATH, ROLES, ROLE_IDS, isReady, standingOf, wordsOf } from "./multiplexer/words.js";

const RANKS = { ready: 0, problem: 1, missing: 2, unsupported: 3 };
const SETTINGS = { title: "the StackOps settings", kind: "config" };
// What whoever opened the tool filled in, by the command's parameter names (`session`, `agent`), until the page shows it.
let proposed = {};

// The page stands in for the command's form. A choice handed over is marked on its card, with the keyboard on its button, and is never saved unasked.
export function open(_context, { preset }) {
  proposed = preset ?? {};
  // Already there: the address does not change, so the page is told to show itself again.
  if (location.hash === ADDRESS) window.dispatchEvent(new HashChangeEvent("hashchange"));
  else location.hash = ADDRESS;
}

// Sessions › Multiplexer, at #/sessions/multiplexer: the two defaults as they stand, and every multiplexer as a card that one click picks.
// The overview arrives first; what is running in each multiplexer is asked for one at a time and fills in as it comes.
export function createPart({ activity, tools }) {
  const { platform } = state.boot;
  // What is running in each multiplexer, by name. An answer stays on show while the next one is on its way.
  const running = new Map();
  const cards = new Map();
  let overview = null;
  let tiles = [];
  let marked = {};
  let ticket = 0;
  let saving = false;
  let risen = false;

  const defaults = h("div", { class: "mux-defaults" }, skeleton(2, "card"));
  const grid = h("div", { class: "mux-grid" }, skeleton(5, "card"));
  const count = h("span", { class: "count" });
  const lead = h("div");
  const failure = h("div");
  const listing = h("section", { class: "block" }, sectionHead("On this machine", count), lead, grid);
  const again = button({ label: "Check again", glyph: "refresh", title: "Read the settings and what is running once more", onclick: () => keeper.load() });
  again.classList.add("mux-again");

  function paintRunning(name) {
    cards.get(name)?.setRunning(running.get(name));
    if (overview.session.name === name) tiles[0].setRunning(running.get(name));
  }

  function paint() {
    const { multiplexers, capabilities } = overview;
    const rank = (item) => RANKS[standingOf(item, platform).id];
    tiles = ROLE_IDS.map((role) => defaultTile({ role, chosen: overview[role], item: multiplexers.find((item) => item.name === overview[role].name), platform, onKeep: pick }));
    defaults.replaceChildren(...tiles.map((tile) => tile.element));
    cards.clear();
    for (const item of [...multiplexers].sort((left, right) => rank(left) - rank(right))) {
      cards.set(item.name, multiplexerCard({ item, capabilities, holds: ROLE_IDS.filter((role) => overview[role].name === item.name), marked, platform, onPick: pick }));
    }
    grid.replaceChildren(...[...cards.values()].map((card) => card.element));
    for (const name of running.keys()) paintRunning(name);
    count.textContent = `${multiplexers.filter(isReady).length} of ${multiplexers.length} ready to use`;
    const first = multiplexers.find((item) => item.name === overview.session.fallback && item.supported && item.in_catalog) ?? multiplexers.find((item) => item.supported && item.in_catalog);
    const install = first && h("a", { class: "btn primary", href: standingOf(first, platform).href }, icon("download", 16), h("span", { text: `Install ${wordsOf(first.name).title}` }));
    lead.replaceChildren(...(multiplexers.some((item) => item.installed) ? [] : [notice({ glyph: "layers", title: "No multiplexer is installed", body: "Nothing on this machine can hold a session yet. Install one of these and it can be picked here.", action: install })]));
    if (!risen) rise(grid);
    risen = true;
  }

  function fail(error) {
    // The server answers 422 when the settings file is there and does not pass the check every StackOps command gives it.
    const unreadable = error.status === 422;
    const actions = h("div", { class: "dialog-actions" }, button({ label: "Try again", glyph: "refresh", small: true, onclick: () => keeper.load() }), unreadable && editButton(activity, SETTINGS, { label: "Edit the settings file", small: true }));
    failure.replaceChildren(notice({ glyph: "alert", tone: "bad", title: unreadable ? "The StackOps settings file cannot be read" : "This didn't load", body: error.message, action: actions }));
    defaults.hidden = listing.hidden = true;
  }

  async function load() {
    const mine = (ticket += 1);
    element.classList.add("loading");
    let answer;
    try {
      answer = await request("GET", API);
    } catch (error) {
      if (mine !== ticket) return;
      element.classList.remove("loading");
      keeper.spoil();
      return fail(error);
    }
    if (mine !== ticket) return;
    element.classList.remove("loading");
    overview = answer;
    failure.replaceChildren();
    defaults.hidden = listing.hidden = false;
    for (const item of overview.multiplexers) if (!isReady(item)) running.delete(item.name);
    paint();
    for (const { name } of overview.multiplexers.filter(isReady)) {
      request("GET", `${API}/sessions?name=${encodeURIComponent(name)}`)
        .catch((error) => ({ name, count: null, names: [], problem: error.message }))
        .then((info) => {
          if (mine !== ticket) return;
          running.set(name, info);
          paintRunning(name);
        });
    }
  }

  // One default at a time, saved at once: a pick is undone by picking another. Every page is then told its data is stale, because the Sessions
  // and Agents pages list what runs in the defaults. `control` is the button that asked, which shows the wait.
  async function pick(role, name, control) {
    if (saving) return;
    saving = true;
    for (const other of element.querySelectorAll(".mux-pick")) other.disabled = true;
    control.classList.add("working");
    const before = overview[role].name;
    try {
      await request("PUT", `${API}/default`, { role, name });
    } catch (error) {
      toast(error.message);
      return paint();
    } finally {
      saving = false;
    }
    overview[role] = { ...overview[role], name, chosen: true };
    marked = {};
    paint();
    cards.get(name).element.focus({ preventScroll: true });
    // Sessions already running in the multiplexer that was the default stay there, out of the Sessions page's sight, so the message says so.
    const left = role === "session" && before !== name ? (running.get(before)?.count ?? 0) : 0;
    const kept = left > 0 ? ` The ${plural(left, "session")} in ${wordsOf(before).title} ${left === 1 ? "keeps" : "keep"} running there.` : "";
    toast(`${ROLES[role].saved(wordsOf(name).title)}${kept}`, "info");
    markStale();
  }

  const element = h(
    "div",
    { class: "mux", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "mux-back", href: "#/sessions" }, icon("back", 14), h("span", { text: "Sessions" })), h("h1", { text: titleOf(state.nodes.get(PATH)) }), h("p", { text: LEDE })),
      h("div", { class: "view-actions" }, button({ label: "All options", glyph: "sliders", title: "The same two choices as a plain form, run as a task you can watch", onclick: () => tools.open(PATH, { plain: true }) }), again),
    ),
    failure,
    defaults,
    listing,
  );
  const keeper = staleKeeper(element, load);
  return {
    element,
    show() {
      const changed = Object.keys(marked).length + Object.keys(proposed).length > 0;
      marked = proposed;
      proposed = {};
      if (overview && changed) paint();
      // Not strictly once: a page that is still loading marks the button when its cards arrive, without moving the keyboard there.
      element.querySelector(".mux-pick.suggested")?.focus();
      keeper.ensure();
    },
  };
}
