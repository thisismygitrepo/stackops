import { h, icon, splitArguments } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { HIDDEN_FLAGS, PATH_FIELDS } from "./catalog.js";
import { createCombo } from "./combo.js";
import { segmented } from "./widgets.js";
import { friendlyText, humanize } from "./words.js";

const SEGMENT_LIMIT = 4;
const LONG_TEXT_NAMES = new Set(["prompt", "message", "command", "context", "note"]);

const longOf = (flags) => flags.find((flag) => flag.startsWith("--")) ?? flags[0];
const labelOf = (spec) => humanize(spec.kind === "option" ? longOf(spec.flags) : spec.name);
const isHidden = (spec) => spec.flags.some((flag) => HIDDEN_FLAGS.has(flag));

function tokensOf(spec, value) {
  if (!value) return [];
  if (spec.control === "switch") return [value === "off" ? longOf(spec.off_flags) : longOf(spec.flags)];
  const items = !spec.multiple || LONG_TEXT_NAMES.has(spec.name) ? [value] : spec.control === "choice" ? value.split("\n") : splitArguments(value);
  return spec.kind === "option" ? items.flatMap((item) => [longOf(spec.flags), item]) : items;
}

function createField(spec, values, changed) {
  const read = () => values.get(spec.name) ?? "";
  const label = labelOf(spec);
  const hint = spec.help ? friendlyText(spec.help) : "";
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
  } else if (spec.control === "switch" || (spec.control === "choice" && !spec.multiple && spec.choices.length <= SEGMENT_LIMIT)) {
    const options = spec.control === "switch" ? [["on", "On"], ["off", "Off"]] : spec.choices.map((choice) => [choice, humanize(choice)]);
    const control = segmented(options, (value) => write(read() === value ? "" : value));
    field = h("div", { class: "field" }, caption, control.element, note);
    paint = () => control.set(read() || (spec.control === "choice" ? spec.default : ""));
  } else if (spec.control === "choice" && spec.multiple) {
    const picked = () => new Set(read() ? read().split("\n") : []);
    const chips = spec.choices.map((choice) =>
      h("button", {
        class: "chip-button", type: "button", text: humanize(choice),
        onclick: () => {
          const next = picked();
          if (!next.delete(choice)) next.add(choice);
          write(spec.choices.filter((item) => next.has(item)).join("\n"));
        },
      }),
    );
    field = h("div", { class: "field" }, caption, h("div", { class: "chip-row" }, chips), note);
    paint = () => chips.forEach((chip, index) => chip.setAttribute("aria-pressed", String(picked().has(spec.choices[index]))));
  } else if (spec.control === "choice") {
    const combo = createCombo({
      label, placeholder: spec.default ? `Default: ${humanize(spec.default)}` : "Choose…", readOnly: true,
      suggest: () => [...(read() ? [{ value: "", label: "Use the default", fill: true }] : []), ...spec.choices.map((choice) => ({ value: choice, label: humanize(choice) }))],
      onPick: (option) => write(option.value),
    });
    field = h("div", { class: "field" }, caption, combo.element, note);
    paint = () => combo.setValue(read() ? humanize(read()) : "");
  } else if (spec.control === "path" || (spec.control === "text" && !spec.multiple && PATH_FIELDS.has(spec.name))) {
    const combo = createCombo({
      label, placeholder: placeholder || "Type a path", glyph: "folder", emptyText: "No such file or folder",
      suggest: async (text) => (await api.paths(text, state.settings.workingDirectory)).entries.map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
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
export function createFriendlyForm({ parameters, values, essentials, locked = [], onChange }) {
  const visible = parameters.filter((spec) => !isHidden(spec) && !locked.includes(spec.name));
  const fields = visible.map((spec) => createField(spec, values, onChange));
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
    const optionTokens = [];
    const argumentTokens = [];
    const problems = [];
    let gap = null;
    for (const spec of parameters) {
      const tokens = tokensOf(spec, values.get(spec.name) ?? "");
      if (spec.required && tokens.length === 0) problems.push(`${labelOf(spec)} is needed`);
      if (spec.kind === "option") optionTokens.push(...tokens);
      else if (tokens.length === 0) gap ??= spec;
      else if (gap) problems.push(`Fill in ${labelOf(gap)} before ${labelOf(spec)}`);
      else argumentTokens.push(...tokens);
    }
    return { tokens: [...optionTokens, ...(argumentTokens.some((token) => token.startsWith("-")) ? ["--"] : []), ...argumentTokens], problems };
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
