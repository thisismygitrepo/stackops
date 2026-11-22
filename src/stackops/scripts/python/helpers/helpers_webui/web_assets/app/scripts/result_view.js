import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { rise } from "./motion.js";
import { copyChip, keyValue, notice, pill, searchInput } from "./widgets.js";
import { humanize, plural, relativeTime } from "./words.js";

const COLUMN_LIMIT = 6;
const ROW_STEP = 60;
const FILTER_THRESHOLD = 8;
const STATUS_KEYS = new Set(["status", "state", "level", "verdict", "kind", "scope", "mode", "method", "category", "source", "harness", "backend"]);
const GOOD = /\b(ok|ready|clean|synced|in sync|configured|linked|up to date|running|active|recorded|installed|healthy|pass|passed|valid|yes|done|attached|completed)\b/i;
const BAD = /\b(error|failed|broken|conflict|invalid|missing|denied|dead|no)\b/i;
const WARN = /\b(not|attention|changed|differs?|behind|ahead|outdated|unknown|warning|stale|dirty|pending|detached)\b/i;
// Numbers that name something are written as they are; every other number gets thousands separators. Not exhaustive by choice: it goes by the key's last word.
const NAMING_KEYS = /(^|_)(port|pid|id|year)$/;

export const toneOf = (text) => (BAD.test(text) ? "bad" : WARN.test(text) ? "warn" : GOOD.test(text) ? "good" : "");
const isRecord = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const isScalar = (value) => value === null || typeof value !== "object";
const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });
const compareCells = (left, right) => (typeof left === "number" && typeof right === "number" ? left - right : collator.compare(String(left ?? ""), String(right ?? "")));

function formatCell(key, value) {
  if (value === null || value === undefined || value === "") return h("span", { class: "dim", text: "—" });
  if (typeof value === "boolean") return pill(value ? "Yes" : "No", value ? "good" : "");
  if (typeof value === "number") return h("span", { class: "num", text: NAMING_KEYS.test(key) ? String(value) : value.toLocaleString() });
  if (Array.isArray(value)) return value.length <= 4 && value.every(isScalar) ? h("span", { text: value.join(", ") || "—" }) : h("span", { class: "dim", text: plural(value.length, "item") });
  if (typeof value === "object") return h("span", { class: "dim", text: plural(Object.keys(value).length, "field") });
  if (STATUS_KEYS.has(key) && value.length < 40) return pill(value, toneOf(value));
  if (/^https?:\/\//.test(value)) return h("a", { class: "link", href: value, target: "_blank", rel: "noopener noreferrer", text: value.replace(/^https?:\/\/(www\.)?/, "") });
  if (/^\d{4}-\d{2}-\d{2}T/.test(value)) return h("span", { title: value, text: relativeTime(value) });
  // A path copies on click. Without a clipboard (plain HTTP from another machine) it stays plain text, which can still be selected by hand.
  if (/^(\/|~\/|[A-Za-z]:\\)/.test(value)) return navigator.clipboard ? copyChip(value, tildify(value, state.boot.home)) : h("code", { class: "path", title: value, text: tildify(value, state.boot.home) });
  return h("span", { title: value.length > 60 ? value : undefined, text: value });
}

export function dataTable(rows) {
  const keys = [...new Set(rows.slice(0, 40).flatMap((row) => Object.keys(row)))];
  const scalarKeys = keys.filter((key) => rows.slice(0, 40).some((row) => isScalar(row[key]) && row[key] !== null && row[key] !== ""));
  const columns = (scalarKeys.length ? scalarKeys : keys).slice(0, COLUMN_LIMIT);
  const body = h("tbody");
  const more = h("button", { class: "btn small ghost", type: "button" });
  let term = "";
  // What the filter looks through: each row's values without its column names, made once, at the first filter, because a large result may never be filtered.
  let searchTexts = null;
  let limit = ROW_STEP;
  let sortKey = null;
  let descending = false;
  // One click sorts by a column, a second flips it, a third goes back to the order the command gave.
  const heads = columns.map((key) =>
    h(
      "th", {},
      h(
        "button",
        {
          type: "button", title: "Sort by this column",
          onclick: () => {
            if (sortKey !== key) [sortKey, descending] = [key, false];
            else if (descending) sortKey = null;
            else descending = true;
            paint();
          },
        },
        h("span", { text: humanize(key) }), icon("down", 12),
      ),
    ),
  );

  function paint() {
    if (term) searchTexts ??= rows.map((row) => JSON.stringify(Object.values(row)).toLowerCase());
    const found = term ? rows.filter((_, index) => searchTexts[index].includes(term)) : rows;
    const matches = sortKey === null ? found : [...found].sort((left, right) => compareCells(left[sortKey], right[sortKey]) * (descending ? -1 : 1));
    heads.forEach((head, index) => head.setAttribute("aria-sort", columns[index] !== sortKey ? "none" : descending ? "descending" : "ascending"));
    body.replaceChildren(
      ...matches.slice(0, limit).map((row) => {
        // The arrow is a real button, so a row also opens from the keyboard; a click anywhere else on the row does the same.
        const toggle = () => {
          const open = !line.classList.contains("open");
          line.classList.toggle("open", open);
          expander.setAttribute("aria-expanded", String(open));
          if (open) line.after(h("tr", { class: "detail-row" }, h("td", { colspan: String(columns.length + 1) }, renderValue(row, 1))));
          else line.nextElementSibling.remove();
        };
        const expander = h("button", { type: "button", "aria-label": "Show this row's details", "aria-expanded": "false", onclick: toggle }, icon("down", 14));
        const line = h("tr", { class: "data-row" }, columns.map((key) => h("td", {}, formatCell(key, row[key]))), h("td", { class: "expander" }, expander));
        line.addEventListener("click", (event) => {
          if (!(event.target instanceof Element && event.target.closest("a, button"))) toggle();
        });
        return line;
      }),
    );
    more.hidden = matches.length <= limit;
    more.textContent = `Show ${Math.min(ROW_STEP, matches.length - limit)} more of ${matches.length}`;
    if (matches.length === 0) body.append(h("tr", {}, h("td", { class: "dim", colspan: String(columns.length + 1), text: "Nothing matches that filter." })));
  }

  more.addEventListener("click", () => {
    limit += ROW_STEP;
    paint();
  });
  const filter = searchInput({
    placeholder: `Filter ${plural(rows.length, "row")}`,
    oninput: (value) => {
      term = value.trim().toLowerCase();
      limit = ROW_STEP;
      paint();
    },
  });
  paint();
  return h(
    "div",
    { class: "table-block" },
    rows.length > FILTER_THRESHOLD && h("div", { class: "table-tools" }, filter.element),
    h("div", { class: "table-scroll" }, h("table", { class: "data-table" }, h("thead", {}, h("tr", {}, heads, h("th"))), body)),
    more,
  );
}

function renderValue(value, depth = 0) {
  if (Array.isArray(value)) {
    if (value.length === 0) return h("p", { class: "dim", text: "Nothing here." });
    if (value.every(isRecord)) return dataTable(value);
    return h("div", { class: "chip-row" }, value.map((item) => (isScalar(item) ? pill(String(item)) : h("code", { class: "path", text: JSON.stringify(item) }))));
  }
  if (!isRecord(value)) return h("p", { class: "plain-value" }, formatCell("", value));
  const entries = Object.entries(value);
  if (entries.length > 2 && entries.every(([, item]) => isRecord(item))) return dataTable(entries.map(([name, item]) => ({ name, ...item })));
  const scalars = entries.filter(([, item]) => isScalar(item));
  const nested = entries.filter(([, item]) => !isScalar(item) && (Array.isArray(item) ? item.length > 0 : Object.keys(item).length > 0));
  if (scalars.length === 0 && nested.length === 0) return h("p", { class: "dim", text: "Nothing here." });
  if (depth === 0 && scalars.length === 0 && nested.length === 1) return renderValue(nested[0][1], 0);
  return h(
    "div",
    { class: "value-block" },
    scalars.length > 0 && keyValue(scalars.map(([key, item]) => [humanize(key), formatCell(key, item)])),
    nested.map(([key, item]) => {
      const size = Array.isArray(item) ? item.length : Object.keys(item).length;
      return h("details", { class: "fold", open: depth === 0 && nested.length <= 3 && size <= 80 }, h("summary", {}, icon("chevron", 13), h("span", { text: humanize(key) }), h("b", { text: String(size) })), renderValue(item, depth + 1));
    }),
  );
}

export function renderResult(result) {
  if (result.json !== undefined) return rise(h("div", { class: "result" }, renderValue(result.json, 0)));
  if (result.text) return h("pre", { class: "output", text: result.text });
  return notice({ glyph: "check", tone: "good", title: "All done", body: result.notes || "There was nothing to show." });
}
