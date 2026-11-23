import { h, icon } from "/assets/scripts/dom.js";
import { button, iconButton } from "../../widgets.js";
import { telling } from "./words.js";

const box = (properties) => h("input", { class: "text-input", type: "text", spellcheck: "false", autocomplete: "off", autocapitalize: "off", ...properties });
// A box that is as tall as what it holds, up to the limit its style sets.
const fit = (area) => {
  area.style.height = "auto";
  area.style.height = `${area.scrollHeight + 2}px`;
};

// Rows with a button under them that adds one more. `make` builds a row from what it is given, null for an empty one, and from the function that takes the row away again.
export function rowList({ addLabel, make }) {
  const rows = [];
  const holder = h("div", { class: "vault-pairs" });
  // The form hears of a row that was added or taken away the same way it hears of typing.
  const changed = () => holder.dispatchEvent(new Event("input", { bubbles: true }));
  function add(given) {
    const row = make(given, () => {
      rows.splice(rows.indexOf(row), 1);
      row.element.remove();
      changed();
    });
    rows.push(row);
    holder.append(row.element);
    return row;
  }
  const more = button({
    label: addLabel, glyph: "plus", small: true, tone: "ghost",
    onclick: () => {
      add(null).name.focus();
      changed();
    },
  });
  return { element: h("div", { class: "vault-pair-list" }, holder, more), rows, add };
}

// A name and a line of text: one of the extra details a login or a secret keeps beside its fields.
export function detailRow(given, remove) {
  const name = box({ value: given?.[0] ?? "", placeholder: "Name", "aria-label": "Name of the detail" });
  const value = box({ value: given?.[1] ?? "", placeholder: "What it is", "aria-label": "The detail" });
  return { element: h("div", { class: "vault-pair" }, name, value, iconButton("close", "Remove this detail", remove)), name, read: () => [name.value.trim(), value.value.trim()] };
}

// One named value of a secret. `given` is null for a new row, or `{ key, json, kept }`. `kept` says where the value is in the saved login: it is
// not in the page, so the box starts empty and the value stays as it is until something is typed. Show fetches it into the box through `fetchKept`.
// `covered` hides what the box holds until Show is pressed. JSON keeps the value as a number, a list or the like instead of text.
export function valueRow(given, remove, { covered, fetchKept }) {
  const kept = given?.kept ?? null;
  // What Show put in the box, so that leaving it alone still counts as unchanged.
  let fetched = null;
  let asJson = given?.json ?? false;
  let open = !covered;
  const name = box({ class: "text-input vault-key-input", value: given?.key ?? "", placeholder: "NAME", "aria-label": "Name of the value" });
  const area = h("textarea", {
    class: "text-input vault-value-input", rows: "1", placeholder: kept ? "Unchanged · type a new value to replace it" : "Value", spellcheck: "false", autocomplete: "off", autocapitalize: "off", "aria-label": "Value",
    oninput: () => fit(area),
  });
  const json = h("button", { class: "chip-button vault-json", type: "button", title: "Keep this value as JSON, such as a number, true or false, a list or an object, instead of as text", text: "JSON" });
  const eye = iconButton("eye", "Show this value", telling(async () => {
    if (!open && kept && fetched === null && area.value === "") {
      const value = await fetchKept(kept);
      asJson = typeof value !== "string";
      fetched = asJson ? JSON.stringify(value, null, 2) : value;
      area.value = fetched;
    }
    open = !open;
    paint();
  }));
  function paint() {
    area.classList.toggle("covered", !open);
    json.setAttribute("aria-pressed", String(asJson));
    eye.replaceChildren(icon(open ? "eyeOff" : "eye", 16));
    eye.title = open ? "Hide this value" : "Show this value";
    eye.setAttribute("aria-label", eye.title);
    fit(area);
  }
  json.addEventListener("click", () => {
    asJson = !asJson;
    paint();
    json.dispatchEvent(new Event("input", { bubbles: true }));
  });
  paint();
  return {
    element: h("div", { class: "vault-pair secret" }, name, area, json, covered && eye, iconButton("close", "Remove this value", remove)),
    name,
    // What the server is sent for this row, and whether a value the secret already had was given a new one. Throws when the box does not hold the JSON it is marked as.
    read() {
      const key = name.value.trim();
      if (kept && (fetched === null ? area.value === "" : area.value === fetched && asJson === given.json)) return { row: { key, kept }, replaced: false };
      if (!asJson) return { row: { key, value: area.value }, replaced: kept !== null };
      try {
        return { row: { key, value: JSON.parse(area.value) }, replaced: kept !== null };
      } catch {
        throw new Error(`${key || "A value"} is marked as JSON, but what it holds is not valid JSON. Turn JSON off to keep it as text.`);
      }
    },
  };
}
