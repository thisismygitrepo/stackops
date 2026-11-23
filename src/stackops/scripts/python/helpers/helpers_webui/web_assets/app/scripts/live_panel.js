import { debounce, h, icon } from "/assets/scripts/dom.js";
import { formDetail, query, staleKeeper } from "./data.js";
import { createFriendlyForm } from "./friendly_form.js";
import { recall, remember } from "./memory.js";
import { openPopover } from "./overlays.js";
import { button, iconButton, notice, skeleton } from "./widgets.js";

const RELOAD_DELAY_MILLISECONDS = 350;

// The shell every panel sits in: a head with a title, a count, actions and Refresh, over a body that shows what `load(fresh)` brings, drawn by `render`.
// Used as it is by views that join several read-only commands. It offers no Options, so nothing a person toggles there can change what the commands do.
// A failed load shows "This didn't load" and is asked for again on the next visit. `explain` may turn the error into a view of its own first, such
// as a tool that is not set up yet; `onFail` hears of the failures it left alone.
// `lasting` is for an answer that nothing done on this machine changes: the panel then sits out the refresh signal that follows every finished run.
export function createPanel({ title, load, render, explain = () => null, onFail = () => {}, actions = [], skeletonShape = "row", lasting = false }) {
  const body = h("div", { class: "panel-body" }, skeleton(3, skeletonShape));
  const count = h("span", { class: "count" });
  const hooks = { setCount: (text) => (count.textContent = text), reload: () => keeper.load(true) };
  const element = h("section", { class: "panel" }, h("header", { class: "panel-head" }, h("h2", { text: title }), count, h("span", { class: "spacer" }), actions, iconButton("refresh", `Refresh ${title.toLowerCase()}`, hooks.reload)), body);
  let ticket = 0;

  async function run(fresh = false) {
    const mine = (ticket += 1);
    element.classList.add("loading");
    try {
      const data = await load(fresh);
      if (mine !== ticket) return;
      body.replaceChildren(render(data, hooks));
    } catch (error) {
      if (mine !== ticket) return;
      const explained = explain(error, hooks);
      count.textContent = "";
      if (!explained) {
        keeper.spoil();
        onFail();
      }
      body.replaceChildren(explained ?? notice({ glyph: "alert", tone: "bad", title: "This didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: hooks.reload }) }));
    }
    element.classList.remove("loading");
  }

  // No `fresh` after a stale mark: the cache was emptied by it, so a plain load already runs the command, and panels that show the same one share that run.
  const keeper = staleKeeper(element, run, !lasting);
  return { element, load: keeper.load, ensure: keeper.ensure };
}

// A panel bound to one read-only command: it runs on arrival with defaults, shows the result, and lets the user change that command's choices.
// `render` is also handed `options`, the choices that are set by parameter name, for a view whose wording depends on one.
export function createLivePanel({ title, path, extra = [], locked = [], render, onFail, actions = [], skeletonShape = "row", tunable = true, lasting = false }) {
  const badge = h("b", { hidden: true });
  // The panel comes back the way it was left; the badge on Options shows that something is set.
  const memoryId = `${path}|${title}`;
  const values = recall(memoryId);
  let form = null;
  let tokens = [];

  const tuneButton = h("button", { class: "btn small ghost tune", type: "button", title: "Change what this shows" }, icon("sliders", 14), h("span", { text: "Options" }), badge);

  function applyOptions() {
    tokens = form.collect().tokens;
    const changed = form.filled().size;
    badge.hidden = changed === 0;
    badge.textContent = String(changed);
  }

  async function buildForm() {
    const { parameters } = await formDetail(path);
    form ??= createFriendlyForm({
      parameters: parameters ?? [], values, essentials: null, locked,
      onChange: () => {
        applyOptions();
        remember(memoryId, form.filled());
        reloadSoon();
      },
    });
    applyOptions();
  }

  const panel = createPanel({
    title, onFail, skeletonShape, lasting, actions: [...actions, tunable && tuneButton],
    load: async (fresh) => {
      // Remembered options only become arguments once the command's parameters are known, so a panel with some asks for those first.
      if (!form && values.size > 0) await buildForm();
      // `extra` goes first: after an argument that starts with a dash the form writes `--`, and anything behind that is read as one more argument.
      return query([...path.split(" "), ...extra, ...tokens], fresh);
    },
    render: (result, hooks) => render(result.json ?? result.text, { ...hooks, options: values }),
  });

  const reloadSoon = debounce(() => panel.load(), RELOAD_DELAY_MILLISECONDS);

  tuneButton.addEventListener("click", async () => {
    if (!form) await buildForm();
    // Asked after the wait, not before it: a second click that landed while the form was being built finds the first one's popover open and stops here.
    if (tuneButton.classList.contains("open")) return;
    openPopover(
      tuneButton,
      h(
        "div",
        { class: "tune-panel" },
        h("div", { class: "tune-head" }, h("h3", { text: `${title} options` }), form.count > 0 && button({ label: "Reset", small: true, tone: "ghost", onclick: () => form.reset(new Map()) })),
        form.count > 0 ? form.element : h("p", { class: "dim", text: "There is nothing to adjust for this view." }),
      ),
    );
  });

  return panel;
}
