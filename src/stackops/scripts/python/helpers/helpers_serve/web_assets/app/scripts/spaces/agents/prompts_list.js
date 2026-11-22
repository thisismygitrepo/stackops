import { h, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { button, notice, pill } from "../../widgets.js";
import { canChange } from "./prompts_files.js";
import { promptFace } from "./prompts_reader.js";
import { markAll, snippetAround, sourceLabel, titleOfPrompt } from "./prompts_text.js";

export const EVERYTHING = "all";
export const keyOf = (prompt) => `${prompt.source}\n${prompt.name}`;
export const groupOf = (prompt) => prompt.group ?? "";

// One line of the list. When the search word is only found inside the prompt's text, the line shows where.
export function promptRow(prompt, { term, chosen, onPick }) {
  const title = titleOfPrompt(prompt.name);
  const named = !term || `${title} ${prompt.description ?? ""}`.toLowerCase().includes(term);
  const blurb = (named ? null : snippetAround(prompt.text, term)) ?? prompt.description ?? prompt.text.trim().split("\n")[0];
  return h(
    "button",
    // Only the chosen row is a tab stop: the arrow keys move between rows, and Tab goes on to the reader.
    { class: "prompt-row", type: "button", role: "option", "data-key": keyOf(prompt), "aria-selected": String(chosen), tabindex: chosen ? "0" : "-1", onclick: () => onPick(prompt) },
    promptFace(prompt, 38),
    h(
      "span",
      { class: "prompt-row-text" },
      h("strong", {}, markAll(title, term)),
      h("span", { class: "prompt-row-blurb" }, markAll(blurb, term)),
      h("span", { class: "prompt-row-meta" }, prompt.group && pill(prompt.group), h("span", { class: "dim", text: sourceLabel(prompt.source) })),
    ),
  );
}

// Group chips for the prompts of the place being looked at, biggest group first. Empty when there is nothing to choose between.
export function groupChips(prompts, group, onPick) {
  const counts = new Map();
  for (const prompt of prompts) counts.set(groupOf(prompt), (counts.get(groupOf(prompt)) ?? 0) + 1);
  if (counts.size < 2) return [];
  const options = [[EVERYTHING, "Every group", prompts.length], ...[...counts].sort((left, right) => right[1] - left[1]).map(([value, count]) => [value, value || "No group", count])];
  return options.map(([value, label, count]) =>
    h("button", { class: "chip-button", type: "button", "aria-pressed": String(value === group), onclick: () => onPick(value === group ? EVERYTHING : value) }, h("span", { text: label }), h("b", { text: String(count) })),
  );
}

export function emptyNotice({ catalog, source, term, onCreate, onShowAll }) {
  const record = catalog.sources.find((candidate) => candidate.source === (source === EVERYTHING ? "user" : source));
  const bare = source === EVERYTHING ? catalog.prompts.length === 0 : record.prompt_count === 0;
  if (!bare || term || !record) {
    return notice({ glyph: "search", title: "No prompt matches", body: "Try a different word, or look in every place and group.", action: button({ label: "Show everything", small: true, onclick: onShowAll }) });
  }
  const creatable = !record.exists && canChange(record);
  return notice({
    glyph: "sparkle", title: record.source === "user" ? "You have no prompts of your own yet" : `Nothing is saved under “${sourceLabel(record.source)}” yet`,
    body: creatable
      ? "A prompt is a set of instructions you write once and hand to an agent whenever you need it. Create the file and it starts with an example for you to rewrite."
      : `Add a prompt to ${tildify(record.path, state.boot.home)} and it shows up here.`,
    action: creatable && button({ label: "Create a prompts file", glyph: "plus", tone: "primary", onclick: () => onCreate(record) }),
  });
}
