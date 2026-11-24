import { h, icon, toast } from "/assets/scripts/dom.js";
import { staleKeeper } from "../../data.js";
import { button, notice, skeleton } from "../../widgets.js";
import { createFacts } from "./update/facts.js";
import { createHero } from "./update/hero.js";
import { createNews } from "./update/news.js";
import { createPlan } from "./update/plan.js";
import { confirmUpdate, runBanner, snapshot } from "./update/run.js";
import { blockerOf, cautionOf, verdictOf } from "./update/verdict.js";
import { UPDATE_HASH, UPDATE_PATH, UPDATE_TITLE, optionsFrom, readEffects, readLatest, readState, runArguments } from "./update/words.js";

let page = null;
let arrival = {};

// Update StackOps is a page of its own at #/machine/update, not a sheet: what matters most is shown after the run has ended (what changed, and
// that the web UI has to be restarted), and a sheet is gone by then. Opening it again, from a card or from Home, starts from the choices given.
export function open(_context, { preset }) {
  if (page) page.adopt(preset ?? {});
  else arrival = preset ?? {};
  location.hash = UPDATE_HASH;
}

export function createPart(context) {
  page ??= createUpdatePage(context, arrival);
  return page;
}

function createUpdatePage({ activity, tools }, preset) {
  const options = optionsFrom(preset);
  let state = null;
  let latest = null;
  let effects = null;
  let failure = "";
  let run = null;
  let starting = false;
  let ticket = 0;
  let bannerShown = "";

  const hero = createHero({ onUpdate: update });
  const news = createNews({ onRetry: () => load(true) });
  const facts = createFacts();
  const plan = createPlan({ options, onChange: paintChoices });
  const bannerHolder = h("div");
  const problem = h("div");
  const waiting = h("div", { class: "machine-update-waiting" }, skeleton(1, "card"), skeleton(3, "row"));
  // The cards lie in a grid whose rows depend on where the install comes from (machine_update.css): with a source folder, that folder stands
  // beside what is new and the install's own facts go to the bottom.
  const grid = h("div", { class: "machine-update-grid" }, news.element, facts.folder, plan.element, facts.install);
  const body = h("div", { class: "machine-update-body", hidden: true }, bannerHolder, hero.element, grid);
  const again = button({ label: "Check again", glyph: "refresh", title: "Reads this machine again and asks the network afresh", onclick: () => load(true) });
  const element = h(
    "div",
    { class: "machine-update", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "machine-update-back", href: "#/machine" }, icon("back", 14), h("span", { text: "Machine" })), h("h1", { text: UPDATE_TITLE }), h("p", { text: "What is installed here, what is newer, and one button to bring this machine up to date." })),
      h("div", { class: "view-actions" }, again, button({ label: "All options", glyph: "sliders", title: "The update command's own form, with every option it has", onclick: () => tools.open(UPDATE_PATH, { plain: true }) })),
    ),
    problem,
    waiting,
    body,
  );

  // The part that follows the switches. The options go first: one that does not apply on this machine switches itself off there.
  function paintChoices() {
    if (state === null) return;
    plan.paint({ state, effects });
    hero.paint({ state, verdict: verdictOf(state, latest), blocker: blockerOf(state, latest, options), caution: cautionOf(state, latest, options), options, busy: starting || run?.phase === "running" });
  }

  function paint() {
    waiting.hidden = state !== null || failure !== "";
    body.hidden = state === null;
    problem.replaceChildren(
      ...(failure
        ? [notice({ glyph: "alert", tone: "bad", title: "This machine's install could not be read", body: `${failure.replace(/[.\s]*$/, "")}. If StackOps was just updated, restart the web UI and open this page again.`, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load(false) }) })]
        : []),
    );
    if (state === null) return;
    grid.dataset.route = state.route;
    paintChoices();
    news.paint({ state, latest });
    facts.paint({ state, latest });
    // The banner is only drawn again when what it says changed, so it does not replay its entrance each time a lookup arrives.
    const bannerNow = JSON.stringify([run, state.restart_needed, state.restart_command]);
    if (bannerNow === bannerShown) return;
    bannerShown = bannerNow;
    const banner = runBanner({
      run, state,
      onReveal: () => activity.reveal(run.id),
      onDismiss() {
        run = null;
        paint();
      },
    });
    bannerHolder.replaceChildren(...(banner ? [banner] : []));
  }

  // In steps: this machine first, which is quick, and then the two slower lookups, each shown as it arrives. A newest-version lookup that
  // cannot even be asked is shown the way a network that is down is, with what the server said.
  async function load(fresh) {
    const mine = (ticket += 1);
    let next;
    element.classList.add("loading");
    try {
      next = await readState();
      if (mine !== ticket) return;
      state = next;
      failure = "";
    } catch (error) {
      if (mine !== ticket) return;
      state = null;
      failure = error.message;
      keeper.spoil();
      element.classList.remove("loading");
      paint();
      return;
    }
    paint();
    if (effects === null || fresh) {
      readEffects().then((answer) => {
        if (mine !== ticket) return;
        effects = answer;
        paintChoices();
      }, () => {});
    }
    const answer = await readLatest(fresh).catch((error) => ({ source: next.route === "index" ? "index" : "github", trouble: "server", problem: error.message, version: "", released_at: "", page: "", standing: "unknown", releases: [], commits: [], more: false }));
    if (mine !== ticket) return;
    latest = answer;
    element.classList.remove("loading");
    paint();
  }

  async function update() {
    if (starting || run?.phase === "running" || state === null) return;
    starting = true;
    paintChoices();
    try {
      // What the person agrees to is read at this moment, not when the page was drawn: files change while it is open.
      state = await readState();
      paint();
      if (blockerOf(state, latest, options)) return;
      if ((options.settings || options.developer) && !(await confirmUpdate({ state, effects, options }))) return;
      const before = snapshot(state);
      const task = await activity.start({ title: UPDATE_TITLE, emoji: "🔄", arguments: runArguments(options), interactive: true, reveal: true });
      run = { phase: "running", id: task.id, before };
      starting = false;
      paint();
      const outcome = await task.done;
      // The banner says what changed, so this machine is read again first; a read that fails leaves the comparison out.
      const after = await readState().catch(() => null);
      if (after) state = after;
      run = { ...run, phase: "done", after: after && snapshot(after), exitCode: outcome.exit_code, stopped: Boolean(outcome.stopped), finishedAt: outcome.finished_at ?? Date.now() / 1000 };
      paint();
      if (!element.closest("[hidden]")) element.closest(".stage")?.scrollTo({ top: 0, behavior: "smooth" });
      // What is new is asked again as well, without waiting for it: the answer from before the update no longer holds.
      load(false);
    } catch (error) {
      toast(error.message);
    } finally {
      starting = false;
      paintChoices();
    }
  }

  const keeper = staleKeeper(element, () => load(false));
  return {
    element,
    // Every visit reads this machine again: the source folder changes outside this app, and the read is quick.
    show: () => keeper.load(),
    adopt(given) {
      Object.assign(options, optionsFrom(given));
      paintChoices();
    },
  };
}
