import { attachPathCompletion } from "./chrome.js";
import { h, splitArguments } from "./dom.js";

const EXTRA = "__extra__";
const FILTER_THRESHOLD = 9;

const longOf = (flags) => flags.find((flag) => flag.startsWith("--")) ?? flags[0];
const labelOf = (spec) => (spec.kind === "option" ? longOf(spec.flags) : spec.name.toUpperCase());

function tokensOf(spec, value) {
  if (!value) return [];
  if (spec.control === "switch") return [value === "off" ? longOf(spec.off_flags) : longOf(spec.flags)];
  const items = !spec.multiple ? [value] : spec.control === "choice" ? value.split("\n") : splitArguments(value);
  return spec.kind === "option" ? items.flatMap((item) => [longOf(spec.flags), item]) : items;
}

function createField(spec, draft, changed) {
  const read = () => draft.get(spec.name) ?? "";
  const field = h("div", { class: "field" });
  const head = h(
    "span",
    { class: "field-head" },
    h("code", { text: labelOf(spec) }),
    spec.flags.filter((flag) => flag !== longOf(spec.flags)).map((flag) => h("code", { class: "alt", text: flag })),
    spec.required && h("span", { class: "badge required", text: "required" }),
    spec.multiple && h("span", { class: "badge", text: "multiple" }),
  );
  const help = spec.help ? h("span", { class: "field-help", text: spec.help }) : "";
  const write = (value) => {
    if (value) draft.set(spec.name, value);
    else draft.delete(spec.name);
    sync();
    changed();
  };
  let paint;
  if (spec.control === "switch" && spec.off_flags.length) {
    const options = [["", `Default (${spec.default ? "on" : "off"})`], ["on", "On"], ["off", "Off"]];
    const buttons = options.map(([value, label]) => h("button", { type: "button", text: label, onclick: () => write(value) }));
    field.classList.add("toggle", "tri");
    field.append(head, h("div", { class: "segmented" }, buttons), help);
    paint = () => buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(options[index][0] === read())));
  } else if (spec.control === "switch") {
    const control = h("button", { class: "switch", type: "button", role: "switch", "aria-label": labelOf(spec) });
    field.classList.add("toggle");
    field.append(control, head, help);
    field.addEventListener("click", () => write(read() ? "" : "on"));
    paint = () => control.setAttribute("aria-checked", String(Boolean(read())));
  } else if (spec.control === "choice" && spec.multiple) {
    const picked = () => new Set(read() ? read().split("\n") : []);
    const buttons = spec.choices.map((choice) =>
      h("button", {
        type: "button", text: choice,
        onclick: () => {
          const next = picked();
          if (!next.delete(choice)) next.add(choice);
          write(spec.choices.filter((item) => next.has(item)).join("\n"));
        },
      }),
    );
    field.append(head, h("div", { class: "choice-chips" }, buttons), help);
    paint = () => buttons.forEach((button, index) => button.setAttribute("aria-pressed", String(picked().has(spec.choices[index]))));
  } else if (spec.control === "choice") {
    const control = h(
      "select",
      { class: "select", "aria-label": labelOf(spec), onchange: () => write(control.value) },
      h("option", { value: "", text: spec.default ? `default · ${spec.default}` : spec.required ? "Choose…" : "not set" }),
      spec.choices.map((choice) => h("option", { value: choice, text: choice })),
    );
    field.append(head, control, help);
    paint = () => (control.value = read());
  } else {
    const control = h("input", {
      class: `input${spec.control === "text" ? "" : " mono"}`, type: spec.control === "number" ? "number" : "text", step: spec.control === "number" && "any",
      spellcheck: "false", autocomplete: "off", "aria-label": labelOf(spec),
      placeholder: spec.default ? `default · ${spec.default}` : spec.multiple ? "space-separated values" : spec.control === "path" ? "path" : "",
      oninput: () => write(control.value.trim() ? control.value : ""),
    });
    field.append(head, control, spec.control === "path" ? attachPathCompletion(control) : "", help);
    paint = () => {
      if (control.value !== read()) control.value = read();
    };
  }
  const sync = () => {
    field.classList.toggle("set", Boolean(read()));
    paint();
  };
  field.dataset.search = `${spec.flags.join(" ")} ${spec.name} ${spec.help}`.toLowerCase();
  sync();
  return { spec, field, sync };
}

export function createCommandForm(parameters, draft, changed) {
  const fields = (parameters ?? []).map((spec) => createField(spec, draft, changed));
  const options = fields.filter((item) => item.spec.kind === "option");
  const extra = h("input", {
    class: "input mono", spellcheck: "false", autocomplete: "off", "aria-label": "Extra arguments", value: draft.get(EXTRA) ?? "",
    placeholder: "appended as typed — quote values that contain spaces",
    oninput: () => {
      draft.set(EXTRA, extra.value);
      changed();
    },
  });
  const filter = h("input", {
    class: "input", type: "search", placeholder: "Filter options", "aria-label": "Filter options",
    oninput: () => {
      const terms = filter.value.toLowerCase().split(/\s+/).filter(Boolean);
      for (const item of options) item.field.hidden = !terms.every((term) => item.field.dataset.search.includes(term));
    },
  });
  const section = (title, items, gridClass, tail) =>
    items.length > 0 &&
    h(
      "section",
      { class: "section" },
      h("div", { class: "section-head" }, h("h2", { text: title }), h("span", { class: "count", text: String(items.length) }), tail),
      h("div", { class: gridClass }, items.map((item) => item.field)),
    );
  const values = options.filter((item) => item.spec.control !== "switch");
  const flags = options.filter((item) => item.spec.control === "switch");
  const useFilter = options.length >= FILTER_THRESHOLD && filter;
  const element = h(
    "div",
    {},
    parameters === null &&
      h("p", { class: "form-note", text: "This command builds its options at runtime, so there is no form for it. Type its arguments below; adding --help prints what it accepts." }),
    section("Arguments", fields.filter((item) => item.spec.kind === "argument"), "fields"),
    section("Options", values, "fields", useFilter),
    section("Flags", flags, "fields toggles", values.length === 0 && useFilter),
    h("section", { class: "section" }, h("div", { class: "section-head" }, h("h2", { text: "Extra arguments" })), extra),
  );

  function collect() {
    const optionTokens = [];
    const argumentTokens = [];
    const problems = [];
    let gap = null;
    for (const { spec } of fields) {
      const tokens = tokensOf(spec, draft.get(spec.name) ?? "");
      if (spec.required && tokens.length === 0) problems.push(`${labelOf(spec)} is required`);
      if (spec.kind === "option") optionTokens.push(...tokens);
      else if (tokens.length === 0) gap ??= spec;
      else if (gap) problems.push(`Fill ${labelOf(gap)} before ${labelOf(spec)}`);
      else argumentTokens.push(...tokens);
    }
    const separator = argumentTokens.some((token) => token.startsWith("-")) ? ["--"] : [];
    return { tokens: [...optionTokens, ...separator, ...argumentTokens, ...splitArguments(draft.get(EXTRA) ?? "")], problems };
  }

  function reset() {
    draft.clear();
    extra.value = "";
    for (const item of fields) item.sync();
    changed();
  }

  return { element, collect, reset, hasFlag: (flag) => fields.some((item) => item.spec.flags.includes(flag)) };
}
