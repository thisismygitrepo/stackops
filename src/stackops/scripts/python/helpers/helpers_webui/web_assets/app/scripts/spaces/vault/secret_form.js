import { h, icon } from "/assets/scripts/dom.js";
import { button, field, textBox } from "../../widgets.js";
import { detailRow, rowList, valueRow } from "./pair_rows.js";
import { listOf, today } from "./words.js";

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;


// A part of the form that stays folded until it is asked for. `count` is how many things inside it are filled in.
export function folded(label, count, ...content) {
  const drawer = h("div", { class: "more-body" }, h("div", { class: "fields" }, content));
  const toggle = h("button", { class: "more-toggle", type: "button", "aria-expanded": "false" }, icon("sliders", 15), h("span", { text: label }), count > 0 && h("b", { text: String(count) }), icon("down", 14));
  toggle.addEventListener("click", () => {
    const open = toggle.getAttribute("aria-expanded") !== "true";
    toggle.setAttribute("aria-expanded", String(open));
    drawer.classList.toggle("open", open);
  });
  return h("div", { class: "more" }, toggle, drawer);
}

// The first thing wrong with a list of details, as [what to say, the box to go to], or null.
export function detailProblem(details) {
  const seen = new Set();
  for (const row of details.rows) {
    const [name, value] = row.read();
    if (!name || !value) return ["A detail needs both a name and what it is. Fill it in or remove it.", row.name];
    if (seen.has(name)) return [`The detail ${name} is listed twice.`, row.name];
    seen.add(name);
  }
  return null;
}

// One secret of the login being edited. `origin` is its place in the login as it is saved, or null for a secret that is new: a value that is
// left alone is sent as that place and its name, since the value itself is not in the page.
export function secretForm(secret, origin, { covered, fetchKept, onRemove }) {
  const rotation = secret?.rotation ?? {};
  const name = textBox(secret?.name ?? "", { placeholder: "Such as api-key or credentials" });
  const tags = textBox((secret?.tags ?? []).join(", "), { placeholder: "Separated by commas" });
  const scopes = textBox((secret?.scopes ?? []).join(", "), { placeholder: "Such as production, read-only" });
  const description = textBox(secret?.description ?? "");
  // A date the file wrote some other way stays as text, so it is kept as it is instead of being read as no date at all.
  const rotated = textBox(rotation.lastRotated ?? "", { type: !rotation.lastRotated || ISO_DATE.test(rotation.lastRotated) ? "date" : "text" });
  const every = textBox(rotation.rotateEveryDays ?? "", { type: "number", min: "1", step: "1", placeholder: "Such as 90" });
  const owner = textBox(rotation.owner ?? "");
  const values = rowList({ addLabel: "Add a value", make: (given, remove) => valueRow(given, remove, { covered, fetchKept }) });
  for (const row of secret?.values ?? []) values.add({ key: row.key, json: row.json, kept: origin === null ? null : [origin, row.key] });
  if (!secret) values.add(null);
  const details = rowList({ addLabel: "Add a detail", make: detailRow });
  for (const pair of Object.entries(secret?.metadata ?? {})) details.add(pair);
  const remove = button({ label: "Remove", glyph: "trash", small: true, tone: "ghost", title: "Take this secret and its values out of the login", onclick: onRemove });

  const element = h(
    "section",
    { class: "vault-secret-form" },
    h("div", { class: "vault-form-row" }, field("Secret name", name), remove),
    h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Values" })), values.element, h("span", { class: "field-hint", text: "Each value has a name, which is the environment variable it becomes when the secret is loaded." })),
    h("div", { class: "vault-form-grid" }, field("Tags", tags), field("Scopes", scopes)),
    field("What it is for", description),
    folded(
      "Rotation and other details", Object.keys(rotation).length + details.rows.length,
      h("div", { class: "vault-form-grid three" }, field("Last rotated", rotated, "Set to today when a value is replaced."), field("Rotate every (days)", every), field("Who rotates it", owner)),
      h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Other details" })), details.element),
    ),
  );

  // The first thing wrong, as [what to say, the box to go to], or null when the secret can be saved.
  function problem() {
    if (!name.value.trim()) return ["Give every secret a name.", name];
    const seen = new Set();
    for (const row of values.rows) {
      const key = row.name.value.trim();
      if (!key) return ["Give every value a name, or remove the row.", row.name];
      if (seen.has(key)) return [`${key} is listed twice in ${name.value.trim()}.`, row.name];
      seen.add(key);
      try {
        row.read();
      } catch (error) {
        return [error.message, row.name];
      }
    }
    if (every.value && !(Number.isInteger(Number(every.value)) && Number(every.value) >= 1)) return ["Rotate every takes a whole number of days, 1 or more.", every];
    return detailProblem(details);
  }

  // The secret as the server takes it. Replacing a value the secret already had is a rotation, so it is dated today unless a date was typed.
  function read() {
    const rows = values.rows.map((row) => row.read());
    const dated = rows.some((row) => row.replaced) && rotated.value === (rotation.lastRotated ?? "") ? today() : rotated.value.trim();
    const record = { ...(dated && { lastRotated: dated }), ...(every.value && { rotateEveryDays: Number(every.value) }), ...(owner.value.trim() && { owner: owner.value.trim() }) };
    return {
      name: name.value.trim(), tags: listOf(tags.value), scopes: listOf(scopes.value), values: rows.map((row) => row.row),
      ...(description.value.trim() && { description: description.value.trim() }),
      ...(Object.keys(record).length > 0 && { rotation: record }),
      ...(details.rows.length > 0 && { metadata: Object.fromEntries(details.rows.map((row) => row.read())) }),
    };
  }

  return { element, name, remove, problem, read };
}
