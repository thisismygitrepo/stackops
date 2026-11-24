import { h } from "/assets/scripts/dom.js";
import { button, glyphTile, pill, searchInput, segmented } from "../../widgets.js";
import { plural } from "../../words.js";
import { countsLine, RUN_STATES, runTiming, scopeTitle } from "./words.js";

const SCOPE_GLYPHS = { all: "shield", apps: "apps", path: "report" };
const STATE_HUES = { good: 155, warn: 35, bad: 345, accent: 252, "": 220 };
const NEWEST = "newest";

// The saved scans as a list to choose one from, never an ID to type. The chosen scan stands on a line of its own with "Change" beside it; the
// list opens with a search over app names and dates, a filter, and a sort. `fit` is what the tool cares about in a scan:
// `{ label, accepts(run), note(run), sort: [label, compare] }`. It names the filter, puts a word on each row, and offers a second order.
export function createRunPicker({ runs, picked, fit, onPick }) {
  let chosen = picked;
  let open = picked === null;
  let only = false;
  let term = "";
  let order = NEWEST;
  const element = h("div", { class: "sec-runs" });
  const list = h("ul", { class: "sec-runs-list" });
  const search = searchInput({
    placeholder: "Find a scan by app or date",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paintList();
    },
  });
  const sorter = segmented([[NEWEST, "Newest first"], ["fit", fit.sort[0]]], (value) => {
    order = value;
    sorter.set(value);
    paintList();
  });
  sorter.set(order);
  const fitting = runs.filter(fit.accepts).length;
  const chips = [[false, "Every scan", runs.length], [true, fit.label, fitting]].map(([value, label, count]) =>
    h(
      "button",
      {
        class: "chip-button", type: "button", "aria-pressed": String(value === only), "data-only": String(value),
        onclick: () => {
          only = value;
          for (const chip of chips) chip.setAttribute("aria-pressed", String(chip.dataset.only === String(only)));
          paintList();
        },
      },
      h("span", { text: label }),
      h("b", { text: String(count) }),
    ),
  );

  const words = (run) => `${scopeTitle(run)} ${run.apps.join(" ")} ${new Date(run.started_at).toLocaleDateString()} ${new Date(run.started_at).toLocaleDateString([], { month: "long" })} ${RUN_STATES[run.status][0]}`.toLowerCase();

  function runLine(run) {
    const [label, tone] = RUN_STATES[run.status];
    return [
      glyphTile(SCOPE_GLYPHS[run.scope], STATE_HUES[tone], 36),
      h("span", { class: "sec-runs-text" }, h("strong", { text: scopeTitle(run) }), h("span", { title: new Date(run.started_at).toLocaleString(), text: `${runTiming(run)} · ${plural(run.targets, "file")} · ${countsLine(run.counts)}` })),
      fit.note(run) && h("span", { class: `sec-runs-note${fit.accepts(run) ? " fits" : ""}`, text: fit.note(run) }),
      pill(label, tone),
    ];
  }

  function paintList() {
    const found = runs.filter((run) => (!only || fit.accepts(run)) && words(run).includes(term));
    const sorted = order === NEWEST ? found : [...found].sort(fit.sort[1]);
    list.replaceChildren(
      ...(sorted.length
        ? sorted.map((run) => h("li", {}, h("button", { class: "sec-runs-row", type: "button", "aria-pressed": String(run.run_id === chosen), onclick: () => pick(run.run_id) }, h("i", { class: "sec-dot" }), runLine(run))))
        : [h("li", { class: "sec-runs-none", text: term ? "No scan matches that." : "No scan is in this group." })]),
    );
  }

  function paint() {
    const run = runs.find((candidate) => candidate.run_id === chosen);
    if (!open && run) {
      element.replaceChildren(h("div", { class: "sec-runs-chosen" }, runLine(run), runs.length > 1 && button({ label: "Change", small: true, onclick: () => ((open = true), paint()) })));
      return;
    }
    element.replaceChildren(h("div", { class: "sec-runs-bar" }, h("div", { class: "chip-row" }, chips), h("span", { class: "spacer" }), sorter.element, search.element), list);
    paintList();
  }

  function pick(id) {
    chosen = id;
    open = false;
    paint();
    onPick(id);
  }

  paint();
  return { element };
}
