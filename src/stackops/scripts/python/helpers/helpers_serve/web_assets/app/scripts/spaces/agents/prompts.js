import { h, toast } from "/assets/scripts/dom.js";
import { markStale } from "../../data.js";
import { createLivePanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { editFile } from "../../space_kit.js";
import { button, searchInput, segmented } from "../../widgets.js";
import { plural } from "../../words.js";
import { canChange, createPromptFile, editTarget, openPromptFiles } from "./prompts_files.js";
import { EVERYTHING, emptyNotice, groupChips, groupOf, keyOf, promptRow } from "./prompts_list.js";
import { createPromptReader } from "./prompts_reader.js";
import { sourceLabel, titleOfPrompt } from "./prompts_text.js";

const ADDRESS = "#/agents/prompts";
const STEP_KEYS = { ArrowDown: 1, ArrowUp: -1, Enter: 0 };

// Browse and read the saved prompts: a filterable list on one side, the chosen prompt in full on the other. The address is #/agents/prompts/<name>[/<place>].
export function createPromptsSection({ activity, tools }) {
  let catalog = null;
  let stamp = "";
  let term = "";
  let source = EVERYTHING;
  let group = EVERYTHING;
  let selected = null;
  let wanted = null;
  let sourcePicker = null;

  const list = h("div", { class: "prompt-list", role: "listbox", "aria-label": "Saved prompts" });
  const chips = h("div", { class: "prompt-groups" });
  const places = h("div", { class: "prompt-places" });
  const blank = h("div", { class: "prompt-blank" });
  const reader = createPromptReader({
    activity, tools,
    onBack: () => {
      panes.dataset.pane = "list";
      history.replaceState(null, "", ADDRESS);
      list.querySelector(`[aria-selected="true"]`)?.scrollIntoView({ block: "center" });
    },
  });
  const panes = h("div", { class: "prompt-panes", "data-pane": "list" }, list, reader.element, blank);
  const search = searchInput({
    placeholder: "Search prompts",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const filesButton = button({
    label: "Where they're kept", glyph: "folder", small: true, tone: "ghost",
    onclick: () => catalog && !filesButton.classList.contains("open") && openPromptFiles(filesButton, { activity, sources: catalog.sources, onCreate: create }),
  });
  // The CLI has no command that adds one prompt: a new one is typed into the file of the place being looked at, or into your own when that place is built in.
  const newButton = button({
    label: "New prompt", glyph: "plus", small: true, tone: "ghost", title: "Opens the prompts file in a text editor. Add a named entry and it shows up here.",
    onclick: () => {
      const record = catalog?.sources.find((candidate) => candidate.source === source && canChange(candidate)) ?? catalog?.sources.find((candidate) => candidate.source === "user");
      if (record) editFile(activity, editTarget(record));
    },
  });

  const inPlace = () => catalog.prompts.filter((prompt) => source === EVERYTHING || prompt.source === source);
  const shownPrompts = () => inPlace().filter((prompt) => (group === EVERYTHING || groupOf(prompt) === group) && (!term || prompt.haystack.includes(term)));

  async function create(record) {
    try {
      if (!(await createPromptFile(activity, record))) return;
      source = record.source;
      markStale();
    } catch (error) {
      toast(error.message);
    }
  }

  // A deliberate pick (a click, Enter, or a link) also moves a narrow window over to the reader and puts the prompt in the address.
  function select(prompt, deliberate) {
    selected = keyOf(prompt);
    for (const item of list.children) item.setAttribute("aria-selected", String(item.dataset.key === selected));
    reader.show(prompt, term);
    if (!deliberate) return;
    panes.dataset.pane = "reader";
    // In a narrow window the reader takes the list's place in a page that may be scrolled far down that list.
    if (list.offsetParent === null && reader.element.getBoundingClientRect().top < panes.closest(".stage").getBoundingClientRect().top) reader.element.scrollIntoView({ block: "start" });
    const twin = catalog.prompts.some((other) => other.name === prompt.name && other.source !== prompt.source);
    history.replaceState(null, "", `${ADDRESS}/${encodeURIComponent(prompt.name)}${twin ? `/${encodeURIComponent(prompt.source)}` : ""}`);
  }

  function paint() {
    const within = inPlace();
    if (group !== EVERYTHING && !within.some((prompt) => groupOf(prompt) === group)) group = EVERYTHING;
    const groups = groupChips(within, group, (value) => {
      group = value;
      paint();
    });
    chips.hidden = groups.length === 0;
    chips.replaceChildren(...groups);
    const shown = shownPrompts();
    list.replaceChildren(...shown.map((prompt) => promptRow(prompt, { term, chosen: keyOf(prompt) === selected, onPick: (picked) => select(picked, true) })));
    panes.classList.toggle("empty", shown.length === 0);
    if (shown.length === 0) blank.replaceChildren(emptyNotice({ catalog, source, term, onCreate: create, onShowAll: showAll }));
    else select(shown.find((prompt) => keyOf(prompt) === selected) ?? shown[0], false);
  }

  function showAll() {
    term = "";
    search.input.value = "";
    source = EVERYTHING;
    group = EVERYTHING;
    sourcePicker.set(source);
    paint();
  }

  function openWanted() {
    if (!catalog || !wanted) return;
    const [name, place] = wanted;
    wanted = null;
    const prompt = catalog.prompts.find((candidate) => candidate.name === name && (!place || candidate.source === place));
    if (!prompt) return toast(`There is no saved prompt called “${name}”.`);
    selected = keyOf(prompt);
    if (shownPrompts().includes(prompt)) paint();
    else showAll();
    select(prompt, true);
    const chosen = list.querySelector(`[aria-selected="true"]`);
    list.scrollTop = Math.max(0, chosen.offsetTop - list.clientHeight / 3);
  }

  function step(event) {
    const move = STEP_KEYS[event.key];
    if (!catalog || move === undefined || (move === 0 && event.currentTarget === list)) return;
    const shown = shownPrompts();
    const from = (event.currentTarget === list && event.target.dataset.key) || selected;
    const next = shown[Math.max(0, Math.min(shown.length - 1, shown.findIndex((prompt) => keyOf(prompt) === from) + move))];
    if (!next) return;
    event.preventDefault();
    select(next, move === 0);
    const chosen = list.querySelector(`[aria-selected="true"]`);
    chosen.scrollIntoView({ block: "nearest" });
    if (event.currentTarget === list) chosen.focus();
  }
  search.input.addEventListener("keydown", step);
  list.addEventListener("keydown", step);

  const panel = createLivePanel({
    title: "Saved prompts", path: "agents run-prompt", extra: ["--list", "--json"], tunable: false, actions: [places, newButton, filesButton],
    render: (data, { setCount }) => {
      // A refresh that brings back the same prompts keeps everyone's place instead of starting the page over.
      const fresh = JSON.stringify(data ?? null);
      const kept = fresh === stamp ? [list.scrollTop, reader.scroll.scrollTop] : null;
      stamp = fresh;
      catalog = {
        sources: data?.sources ?? [],
        prompts: (data?.prompts ?? []).map((prompt) => ({ ...prompt, haystack: `${prompt.name} ${titleOfPrompt(prompt.name)} ${prompt.group ?? ""} ${prompt.description ?? ""} ${sourceLabel(prompt.source)} ${prompt.text}`.toLowerCase() })),
      };
      setCount(`${plural(catalog.prompts.length, "prompt")} from ${plural(catalog.sources.filter((record) => record.exists).length, "place")}`);
      if (!catalog.sources.some((record) => record.source === source)) source = EVERYTHING;
      sourcePicker = segmented([[EVERYTHING, `All · ${catalog.prompts.length}`], ...catalog.sources.map((record) => [record.source, `${sourceLabel(record.source)} · ${record.prompt_count}`])], (value) => {
        source = value;
        sourcePicker.set(source);
        paint();
      });
      places.replaceChildren(sourcePicker.element);
      sourcePicker.set(source);
      paint();
      if (!kept) rise(list);
      requestAnimationFrame(() => {
        if (kept) [list.scrollTop, reader.scroll.scrollTop] = kept;
        openWanted();
      });
      return h("div", { class: "prompts" }, h("div", { class: "prompt-tools" }, search.element, chips), panes);
    },
  });
  panel.element.classList.add("prompts-panel");

  return {
    element: h("div", { class: "agents-section" }, panel.element),
    show(route) {
      wanted = route.length ? route : null;
      if (!wanted) panes.dataset.pane = "list";
      panel.ensure();
      sourcePicker?.set(source);
      reader.refit();
      openWanted();
    },
  };
}
