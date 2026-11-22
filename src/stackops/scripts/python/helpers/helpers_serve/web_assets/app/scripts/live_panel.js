import { debounce, h, icon } from "/assets/scripts/dom.js";
import { on } from "/assets/scripts/state.js";
import { commandDetail, query } from "./data.js";
import { createFriendlyForm } from "./friendly_form.js";
import { recall, remember } from "./memory.js";
import { openPopover } from "./overlays.js";
import { button, iconButton, notice, skeleton } from "./widgets.js";

const RELOAD_DELAY_MILLISECONDS = 350;

// A panel bound to one read-only command: it runs on arrival with defaults, shows the result, and lets the user change that command's choices.
export function createLivePanel({ title, path, extra = [], locked = [], render, actions = [], skeletonShape = "row", tunable = true }) {
  const body = h("div", { class: "panel-body" }, skeleton(3, skeletonShape));
  const count = h("span", { class: "count" });
  const badge = h("b", { hidden: true });
  // The panel comes back the way it was left; the badge on Options shows that something is set.
  const memoryId = `${path}|${title}`;
  const values = recall(memoryId);
  let form = null;
  let tokens = [];
  let ticket = 0;
  let loaded = false;
  let stale = false;

  const refreshButton = iconButton("refresh", `Refresh ${title.toLowerCase()}`, () => load(true));
  const tuneButton = h("button", { class: "btn small ghost tune", type: "button", title: "Change what this shows" }, icon("sliders", 14), h("span", { text: "Options" }), badge);
  const element = h("section", { class: "panel" }, h("header", { class: "panel-head" }, h("h2", { text: title }), count, h("span", { class: "spacer" }), actions, tunable && tuneButton, refreshButton), body);

  function applyOptions() {
    tokens = form.collect().tokens;
    const changed = form.filled().size;
    badge.hidden = changed === 0;
    badge.textContent = String(changed);
  }

  async function buildForm() {
    const { parameters } = await commandDetail(path);
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

  async function load(fresh = false) {
    const mine = (ticket += 1);
    stale = false;
    element.classList.add("loading");
    try {
      // Remembered options only become arguments once the command's parameters are known, so a panel with some asks for those first.
      if (!form && values.size > 0) await buildForm();
      // `extra` goes first: after an argument that starts with a dash the form writes `--`, and anything behind that is read as one more argument.
      const result = await query([...path.split(" "), ...extra, ...tokens], fresh);
      if (mine !== ticket) return;
      body.replaceChildren(render(result.json ?? result.text, { result, setCount: (text) => (count.textContent = text), reload: () => load(true) }));
      loaded = true;
    } catch (error) {
      if (mine !== ticket) return;
      count.textContent = "";
      body.replaceChildren(
        notice({ glyph: "alert", tone: "bad", title: "This didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load(true) }) }),
      );
    }
    element.classList.remove("loading");
  }

  const reloadSoon = debounce(() => load(), RELOAD_DELAY_MILLISECONDS);

  tuneButton.addEventListener("click", async () => {
    if (tuneButton.classList.contains("open")) return;
    if (!form) await buildForm();
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

  // No `fresh` after a stale mark: the cache was emptied by it, so a plain load already runs the command, and panels that show the same one share that run.
  on("data-stale", () => {
    stale = true;
    if (element.isConnected && !element.closest("[hidden]")) load();
  });

  return {
    element,
    load,
    ensure() {
      if (!loaded || stale) load();
    },
  };
}
