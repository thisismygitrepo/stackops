import { h, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../agent_ask.js";
import { PLACES } from "../agent_places.js";
import { markStale } from "../data.js";
import { createPanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createView, editFile } from "../space_kit.js";
import { button, notice, searchInput, segmented } from "../widgets.js";
import { plural } from "../words.js";
import { addScript } from "./scripts/new_script.js";
import { scriptRow } from "./scripts/script_row.js";
import { createScriptView } from "./scripts/script_view.js";
import { EVERYWHERE, ONLINE, canChange, fileOf, haystackOf, keyOf, placeLabel, runsHere } from "./scripts/words.js";

const STEP_KEYS = { ArrowDown: 1, ArrowUp: -1 };

// The scripts the CLI can run: a list on one side, the chosen one's text and a bar to run it from on the other. The layout and its class names
// are the saved prompts' (agents_prompts.css); what is the page's own is in scripts.css.
// The list and a script's text come from the server's /api/scripts, since no command prints a script and the user's own are kept where the
// app's file reader does not go. Running and editing go through the CLI, in the activity panel.
export function createScriptsSpace({ activity }) {
  let term = "";
  let place = EVERYWHERE;
  let selected = null;
  // Scripts written for another system are left out until they are asked for.
  let everySystem = false;
  let local = [];
  // The scripts kept online, which arrive after the ones on this machine, and why they did not when they could not be listed.
  let online = [];
  let offline = "";
  let placePicker = null;
  let setCount = () => {};

  const list = h("div", { class: "prompt-list", role: "listbox", "aria-label": "Scripts" });
  const blank = h("div", { class: "prompt-blank" });
  const places = h("div", { class: "prompt-places" });
  const panes = h("div", { class: "prompt-panes", "data-pane": "list" });
  const view = createScriptView({ activity, onBack: () => (panes.dataset.pane = "list") });
  panes.append(list, view.element, blank);
  const search = searchInput({
    placeholder: "Search scripts",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const systemSwitch = h(
    "button",
    {
      class: "mini-toggle", type: "button", role: "switch", title: "Also list scripts written for another operating system",
      onclick: () => {
        everySystem = !everySystem;
        arrange();
      },
    },
    h("i", { class: "switch" }),
    h("span"),
  );
  const unreached = h("span", { class: "dim script-unreached", text: "The scripts kept online are out of reach" });

  const offered = () => [...local, ...online].filter((script) => everySystem || runsHere(script));
  const shownScripts = () => offered().filter((script) => (place === EVERYWHERE || script.source === place) && (!term || script.haystack.includes(term)));

  // A deliberate pick, a click or Enter, also moves a narrow window over to the script.
  function select(script, deliberate) {
    selected = keyOf(script);
    for (const item of list.children) {
      item.setAttribute("aria-selected", String(item.dataset.key === selected));
      item.tabIndex = item.dataset.key === selected ? 0 : -1;
    }
    view.show(script);
    if (deliberate) panes.dataset.pane = "reader";
  }

  function showAll() {
    term = "";
    search.input.value = "";
    place = EVERYWHERE;
    paint();
  }

  function paint() {
    placePicker?.set(place);
    const shown = shownScripts();
    const several = new Set(offered().map((script) => script.source)).size > 1 && place === EVERYWHERE;
    list.replaceChildren(...shown.map((script) => scriptRow(script, { term, several, chosen: keyOf(script) === selected, onPick: (picked) => select(picked, true) })));
    panes.classList.toggle("empty", shown.length === 0);
    if (shown.length > 0) return select(shown.find((script) => keyOf(script) === selected) ?? shown[0], false);
    blank.replaceChildren(notice({ glyph: "search", title: "No script matches", body: "Try a different word, or look in every place.", action: button({ label: "Show everything", small: true, onclick: showAll }) }));
  }

  // The parts that depend on which scripts there are: the count, the choice of place and the switch for other systems. Run again when the
  // scripts kept online arrive, and when the switch is turned.
  function arrange() {
    const everything = [...local, ...online];
    const foreign = everything.filter((script) => !runsHere(script)).length;
    const scripts = offered();
    const filled = [...new Set(scripts.map((script) => script.source))];
    setCount(`${plural(scripts.length, "script")} from ${plural(filled.length, "place")}`);
    if (!filled.includes(place)) place = EVERYWHERE;
    // A choice of place is only offered when the scripts come from more than one.
    placePicker =
      filled.length > 1
        ? segmented([[EVERYWHERE, `All · ${scripts.length}`], ...filled.map((source) => [source, `${placeLabel(source)} · ${scripts.filter((script) => script.source === source).length}`])], (value) => {
            place = value;
            paint();
          })
        : null;
    places.replaceChildren(...(placePicker ? [placePicker.element] : []));
    systemSwitch.hidden = foreign === 0;
    systemSwitch.setAttribute("aria-checked", String(everySystem));
    systemSwitch.lastChild.textContent = `Other systems · ${foreign}`;
    unreached.hidden = !offline;
    unreached.title = offline;
    paint();
  }

  // Asked for beside the scripts on this machine and added when they arrive, so the page never waits for the network.
  function readOnline() {
    api.onlineScripts().then(
      (answer) => {
        online = answer.scripts.map((script) => ({ ...script, source: ONLINE, summary: "" })).map((script) => ({ ...script, haystack: haystackOf(script) }));
        offline = "";
      },
      (error) => {
        online = [];
        offline = error.message;
      },
    ).then(arrange);
  }

  // The script a form just made is the one to look at once the list is back, and it is opened to be written.
  const add = () =>
    addScript({
      activity, place: canChange(place) ? place : "user",
      onCreated: (made) => {
        term = "";
        search.input.value = "";
        if (place !== made.source) place = EVERYWHERE;
        selected = keyOf(made);
        markStale();
        editFile(activity, { title: fileOf(made), kind: "script", path: made.path });
      },
    }).catch((error) => toast(error.message));

  function step(event) {
    const move = STEP_KEYS[event.key];
    if (move === undefined) return;
    const shown = shownScripts();
    const next = shown[Math.max(0, Math.min(shown.length - 1, shown.findIndex((script) => keyOf(script) === selected) + move))];
    if (!next) return;
    event.preventDefault();
    select(next, false);
    const chosen = list.querySelector(`[aria-selected="true"]`);
    chosen.scrollIntoView({ block: "nearest" });
    if (event.currentTarget === list) chosen.focus();
  }
  search.input.addEventListener("keydown", step);
  list.addEventListener("keydown", step);

  const panel = createPanel({
    title: "Scripts",
    actions: [h("div", { class: "panel-quick" }, unreached, systemSwitch)],
    load: async () => {
      const data = await api.scripts(state.settings.workingDirectory);
      readOnline();
      return data;
    },
    render: (data, hooks) => {
      const first = local.length === 0;
      // The panes are moved into what this returns, which sends their scrolling back to the top.
      const kept = [list.scrollTop, view.scroll.scrollTop];
      setCount = hooks.setCount;
      local = data.places.flatMap((found) => found.scripts.map((script) => ({ ...script, source: found.name }))).map((script) => ({ ...script, haystack: haystackOf(script) }));
      arrange();
      if (first) rise(list);
      requestAnimationFrame(() => ([list.scrollTop, view.scroll.scrollTop] = kept));
      return h("div", { class: "prompts scripts" }, h("div", { class: "prompt-tools" }, search.element, places), panes);
    },
  });
  panel.element.classList.add("prompts-panel");

  const element = createView(
    {
      title: "Scripts", lede: "Small programs kept to hand: your own, this project's, and the ones StackOps comes with. Pick one to read it, then run it.",
      actions: [agentButton(activity, PLACES.scripts), button({ label: "New script", glyph: "plus", tone: "primary", onclick: add })],
    },
    panel.element,
  );

  return {
    element,
    show() {
      panes.dataset.pane = "list";
      panel.ensure();
      placePicker?.set(place);
    },
  };
}
