import { debounce, h, icon } from "/assets/scripts/dom.js";
import { formDetail, query, staleKeeper } from "./data.js";
import { createFriendlyForm } from "./friendly_form.js";
import { recall, remember } from "./memory.js";
import { openPopover } from "./overlays.js";
import { button, iconButton, notice, searchInput, segmented, skeleton } from "./widgets.js";
import { humanize } from "./words.js";

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

// One of a command's choices as a control small enough for a panel's head: a switch, a pick between a few, or a box to type in.
function quickControl(spec, caption, values, changed) {
  let paint = () => {};
  const write = (value) => {
    if (value) values.set(spec.name, value);
    else values.delete(spec.name);
    paint();
    changed();
  };
  if (spec.control === "switch") {
    const toggle = h("button", { class: "mini-toggle", type: "button", role: "switch", title: caption, onclick: () => write(values.has(spec.name) ? "" : "on") }, h("i", { class: "switch" }), h("span", { text: caption }));
    paint = () => toggle.setAttribute("aria-checked", String(values.has(spec.name)));
    paint();
    return toggle;
  }
  if (spec.control === "choice") {
    const picker = segmented(spec.choices.map((choice) => [choice, humanize(choice)]), (choice) => write(choice === spec.default ? "" : choice));
    picker.element.title = caption;
    paint = () => picker.set(values.get(spec.name) ?? spec.default);
    paint();
    return picker.element;
  }
  const box = searchInput({ placeholder: caption, oninput: (typed) => write(typed.trim()) });
  box.input.value = values.get(spec.name) ?? "";
  return box.element;
}

// A panel bound to one read-only command: it runs on arrival with defaults, shows the result, and lets the user change that command's choices.
// `render` is also handed `options`, the choices that are set by parameter name, for a view whose wording depends on one.
// `surface` names the choices that matter enough to sit in the panel's head, each with the words to show for it; Options holds the rest, and
// is left out when nothing is left for it.
export function createLivePanel({ title, path, extra = [], locked = [], surface = {}, render, onFail, actions = [], skeletonShape = "row", tunable = true, lasting = false }) {
  const badge = h("b", { hidden: true });
  // The panel comes back the way it was left; the badge on Options shows that something is set.
  const memoryId = `${path}|${title}`;
  // A panel without Options starts clean: what was set while it still had them could not be seen or undone.
  const values = tunable ? recall(memoryId) : new Map();
  const surfaced = Object.keys(surface);
  const quick = h("div", { class: "panel-quick", hidden: true });
  let form = null;
  let building = null;
  let tokens = [];

  const tuneButton = h("button", { class: "btn small ghost tune", type: "button", title: "Change what this shows" }, icon("sliders", 14), h("span", { text: "Options" }), badge);
  const inHead = () => new Map(surfaced.filter((name) => values.has(name)).map((name) => [name, values.get(name)]));

  function applyOptions() {
    tokens = form.collect().tokens;
    const changed = form.filled().size;
    badge.hidden = changed === 0;
    badge.textContent = String(changed);
  }

  function changed() {
    applyOptions();
    remember(memoryId, new Map([...form.filled(), ...inHead()]));
    reloadSoon();
  }

  // Asked for once: by the first load of a panel with something remembered or something in its head, or by the first press of Options.
  function buildForm() {
    building ??= formDetail(path).then(({ parameters }) => {
      const specs = parameters ?? [];
      form = createFriendlyForm({ parameters: specs, values, essentials: null, locked: [...locked, ...surfaced], onChange: changed });
      // What was remembered for a choice this panel no longer offers is dropped, or it would go on narrowing the answer out of sight.
      const offered = new Map([...form.filled(), ...inHead()]);
      for (const name of [...values.keys()]) if (!offered.has(name)) values.delete(name);
      quick.replaceChildren(...specs.filter((spec) => surfaced.includes(spec.name)).map((spec) => quickControl(spec, surface[spec.name], values, changed)));
      quick.hidden = quick.childElementCount === 0;
      tuneButton.hidden = surfaced.length > 0 && form.count === 0;
      applyOptions();
    });
    building.catch(() => (building = null));
    return building;
  }

  const panel = createPanel({
    title, onFail, skeletonShape, lasting, actions: [quick, ...actions, tunable && tuneButton],
    load: async (fresh) => {
      // Remembered options only become arguments once the command's parameters are known, so a panel with some asks for those first. One with
      // a choice in its head asks too, without keeping the first answer waiting for it.
      if (!form && (values.size > 0 || surfaced.length > 0)) {
        const ready = buildForm();
        if (values.size > 0) await ready;
      }
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
        // Reset empties what Options holds; a choice in the head is in plain view and stays as it is.
        h("div", { class: "tune-head" }, h("h3", { text: `${title} options` }), form.count > 0 && button({ label: "Reset", small: true, tone: "ghost", onclick: () => form.reset(inHead()) })),
        form.count > 0 ? form.element : h("p", { class: "dim", text: "There is nothing to adjust for this view." }),
      ),
    );
  });

  return panel;
}
