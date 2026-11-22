import { collectTokens, LONG_TEXT_NAMES, longOf } from "/assets/scripts/command_tokens.js";
import { h, icon } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { HIDDEN_FLAGS } from "./catalog.js";
import { createCombo } from "./combo.js";
import { segmented } from "./widgets.js";
import { friendlyText, humanize } from "./words.js";

const SEGMENT_LIMIT = 4;

const labelOf = (spec) => humanize(spec.kind === "option" ? longOf(spec.flags) : spec.name);
const isHidden = (spec) => spec.flags.some((flag) => HIDDEN_FLAGS.has(flag));

function createField(spec, values, changed, fromHome) {
  const read = () => values.get(spec.name) ?? "";
  const label = labelOf(spec);
  const help = spec.help ? friendlyText(spec.help) : "";
  // A listed field (see `formDetail`) is picked from, not typed into, so the sentences that say how to type a list are left out of its hint.
  const hint = spec.listed ? help.split(/(?<=[.;])\s+/).filter((sentence) => !/comma/i.test(sentence)).join(" ") : help;
  // A listed choice is a name on this machine and comes with the text to show for it. The CLI's own choices are keywords, put into words here.
  const wordOf = (choice) => spec.labels?.[choice] ?? humanize(choice);
  const placeholder = spec.default ? `Default: ${spec.default}` : LONG_TEXT_NAMES.has(spec.name) ? "Type here…" : spec.multiple ? "Separate several with spaces" : "";
  let paint = () => {};
  const write = (value) => {
    if (value) values.set(spec.name, value);
    else values.delete(spec.name);
    sync();
    changed();
  };
  const caption = h("div", { class: "field-label" }, h("span", { text: label }), spec.required && h("em", { text: "needed" }));
  const note = hint && h("p", { class: "field-hint", text: hint });
  let field;
  if (spec.control === "switch" && spec.off_flags.length === 0) {
    field = h("button", { class: "field toggle-row", type: "button", role: "switch", onclick: () => write(read() ? "" : "on") }, h("div", {}, caption, note), h("i", { class: "switch" }));
    paint = () => field.setAttribute("aria-checked", String(Boolean(read())));
  } else if (spec.control === "switch" || (spec.control === "choice" && !spec.multiple && !spec.listed && spec.choices.length <= SEGMENT_LIMIT)) {
    const options = spec.control === "switch" ? [["on", "On"], ["off", "Off"]] : spec.choices.map((choice) => [choice, humanize(choice)]);
    const control = segmented(options, (value) => write(read() === value ? "" : value));
    field = h("div", { class: "field" }, caption, control.element, note);
    paint = () => control.set(read() || (spec.control === "choice" ? spec.default : ""));
  } else if (spec.control === "choice" && (spec.multiple || spec.separator)) {
    // Several picks, written as one value per repeat of the parameter or, with a separator, as the one list the CLI splits at it. A list with a
    // separator shows what the command will use, so an untouched one has its default pressed, and going back to the default empties the field.
    // `whole` is the choice that stands for all of them: it is only ever picked alone.
    const joiner = spec.separator || "\n";
    const usual = spec.separator && spec.default ? spec.default.split(joiner) : [];
    const picked = () => new Set(read() ? read().split(joiner) : usual);
    const chips = spec.choices.map((choice) =>
      h("button", {
        class: "chip-button", type: "button", text: wordOf(choice),
        onclick: () => {
          const now = picked();
          const next = choice === spec.whole ? new Set(now.has(choice) ? [] : [choice]) : new Set([...now].filter((item) => item !== spec.whole));
          if (choice !== spec.whole && !next.delete(choice)) next.add(choice);
          const kept = spec.choices.filter((item) => next.has(item));
          write(kept.length === usual.length && usual.every((item) => next.has(item)) ? "" : kept.join(joiner));
        },
      }),
    );
    field = h("div", { class: "field" }, caption, h("div", { class: "chip-row" }, chips), note);
    paint = () => chips.forEach((chip, index) => chip.setAttribute("aria-pressed", String(picked().has(spec.choices[index]))));
  } else if (spec.control === "choice") {
    const combo = createCombo({
      label, placeholder: spec.default ? `Default: ${wordOf(spec.default)}` : "Choose…", readOnly: true,
      suggest: () => [
        ...(read() ? [{ value: "", label: spec.default ? `Default: ${wordOf(spec.default)}` : "Use the default", fill: true }] : []),
        ...spec.choices.map((choice) => ({ value: choice, label: wordOf(choice), hint: choice === spec.default && "Default" })),
      ],
      onPick: (option) => write(option.value),
    });
    field = h("div", { class: "field" }, caption, combo.element, note);
    paint = () => combo.setValue(read() ? wordOf(read()) : "");
  } else if (spec.control === "path") {
    const combo = createCombo({
      label, placeholder: placeholder || "Type a path", glyph: "folder", emptyText: "Nothing to suggest",
      // An empty box lists the working folder, or the home folder for a field that starts there. Typed text is read the same way in both.
      suggest: async (text) => (await api.paths(text || (fromHome ? "~/" : ""), state.settings.workingDirectory)).entries.map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
      onInput: (text) => write(text.trim() ? text : ""),
      onPick: (option) => write(option.value),
    });
    field = h("div", { class: "field" }, caption, combo.element, note);
    paint = () => combo.input.value !== read() && combo.setValue(read());
  } else {
    const long = spec.control === "text" && LONG_TEXT_NAMES.has(spec.name);
    const control = h(long ? "textarea" : "input", {
      class: "text-input", type: !long && (spec.control === "number" ? "number" : "text"), step: spec.control === "number" && "any", rows: long && "3",
      spellcheck: long ? "true" : "false", autocomplete: "off", "aria-label": label, placeholder,
      oninput: () => write(control.value.trim() ? control.value : ""),
    });
    field = h("div", { class: "field" }, caption, control, note);
    paint = () => {
      if (control.value !== read()) control.value = read();
    };
  }
  const sync = () => {
    field.classList.toggle("filled", Boolean(read()));
    paint();
  };
  sync();
  return { spec, field, sync };
}

// `essentials` is the list of option flags to keep in view; everything else folds under "More options". Pass null to show every field.
// `homePaths` names the path fields whose suggestions start in the home folder.
export function createFriendlyForm({ parameters, values, essentials, locked = [], homePaths = [], onChange }) {
  const visible = parameters.filter((spec) => !isHidden(spec) && !locked.includes(spec.name));
  const fields = visible.map((spec) => createField(spec, values, onChange, homePaths.includes(spec.name)));
  const isPrimary = ({ spec }) => essentials === null || spec.kind === "argument" || spec.required || spec.flags.some((flag) => essentials.includes(flag));
  const primary = fields.filter(isPrimary);
  const rest = fields.filter((item) => !isPrimary(item));
  const drawer = h("div", { class: "more-body" }, h("div", { class: "fields" }, rest.map((item) => item.field)));
  const toggle = h("button", { class: "more-toggle", type: "button", "aria-expanded": "false" }, icon("sliders", 15), h("span", { text: `More options` }), h("b", { text: String(rest.length) }), icon("down", 14));
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    drawer.classList.toggle("open", open);
  });
  const element = h("div", { class: "form" }, primary.length > 0 && h("div", { class: "fields" }, primary.map((item) => item.field)), rest.length > 0 && h("div", { class: "more" }, toggle, drawer));

  function collect() {
    const { tokens, problems } = collectTokens(parameters, values, []);
    return { tokens, problems: problems.map(({ spec, gap }) => (gap ? `Fill in ${labelOf(gap)} before ${labelOf(spec)}` : `${labelOf(spec)} is needed`)) };
  }

  // `start` is what the form goes back to: what its owner opened it with, or an empty map.
  function reset(start) {
    values.clear();
    for (const [name, value] of start) values.set(name, value);
    for (const item of fields) item.sync();
    onChange();
  }

  // What the fields on show are set to. Values the owner passed for parameters the form hides are left out, so they are never remembered.
  const filled = () => new Map(fields.filter(({ spec }) => values.has(spec.name)).map(({ spec }) => [spec.name, values.get(spec.name)]));
  return { element, collect, reset, count: fields.length, filled };
}
