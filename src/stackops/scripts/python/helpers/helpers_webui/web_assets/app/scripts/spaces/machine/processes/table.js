import { h, icon } from "/assets/scripts/dom.js";
import { createRow } from "./row.js";

// `biggestFirst` is the way a column sorts on its first click: the most CPU, the most memory, the newest.
export const COLUMNS = [
  { id: "name", label: "Name" },
  { id: "pid", label: "ID" },
  { id: "user", label: "User" },
  { id: "cpu", label: "CPU", biggestFirst: true },
  { id: "memory", label: "Memory", biggestFirst: true },
  { id: "status", label: "Status" },
  { id: "started", label: "Started", biggestFirst: true },
  { id: "ports", label: "Ports" },
  { id: "command", label: "Command" },
];
const WIDTH = COLUMNS.length + 2;

function noteRow(key, record) {
  return h(
    "tr",
    { class: "procs-note-row", "data-key": `${key}/note` },
    h(
      "td",
      { colspan: String(WIDTH) },
      h(
        "div",
        { class: `procs-note ${record.tone}` },
        icon(record.tone === "good" ? "check" : "alert", 14),
        h("span", { text: record.text }),
        record.action && h("button", { class: "btn small", type: "button", "data-part": "act", onclick: record.action.run }, h("span", { text: record.action.label })),
      ),
    ),
  );
}

// The list itself. A line is kept for as long as its process is shown and only moved when the order changes, so reading the machine again
// every few seconds never rebuilds what the pointer or the keyboard is on. `view` is the page's: its state and what to do on each action.
export function createTable(view) {
  const lines = new Map();
  const notes = new Map();
  const body = h("tbody");
  const pickAll = h("input", { class: "procs-check", type: "checkbox", "aria-label": "Select every process shown", title: "Select every process shown" });
  const heads = COLUMNS.map((column) =>
    h("th", { class: `procs-col-${column.id}` }, h("button", { type: "button", title: "Sort by this column", onclick: () => view.onSort(column.id, Boolean(column.biggestFirst)) }, h("span", { text: column.label }), icon("down", 12))),
  );
  const more = h("button", { class: "btn small ghost procs-more", type: "button", onclick: () => view.onMore() });
  const element = h(
    "div",
    { class: "procs-list" },
    h("div", { class: "procs-scroll" }, h("table", { class: "procs-table" }, h("thead", {}, h("tr", {}, h("th", { class: "procs-tick" }, h("label", {}, pickAll)), heads, h("th", { class: "procs-act" }))), body)),
    more,
  );
  let shown = [];
  const pickable = () => shown.filter((item) => item.process.lock === "").map((item) => item.process);
  pickAll.addEventListener("change", () => view.onPickMany(pickable(), pickAll.checked));

  function place(wanted) {
    let cursor = body.firstChild;
    for (const node of wanted) {
      if (node === cursor) cursor = cursor.nextSibling;
      else body.insertBefore(node, cursor);
    }
    while (cursor) {
      const next = cursor.nextSibling;
      cursor.remove();
      cursor = next;
    }
  }

  function syncPicks() {
    for (const [key, line] of lines) line.setPicked(view.picked.has(key));
    const candidates = pickable();
    const chosen = candidates.filter((process) => view.picked.has(process.key)).length;
    pickAll.disabled = candidates.length === 0;
    pickAll.checked = chosen > 0 && chosen === candidates.length;
    pickAll.indeterminate = chosen > 0 && chosen < candidates.length;
  }

  function render(rows, total, step) {
    const focused = document.activeElement instanceof HTMLElement && body.contains(document.activeElement) ? document.activeElement : null;
    const focus = focused && { key: focused.closest("tr").dataset.key, part: focused.dataset.part };
    shown = rows;
    element.classList.toggle("tree", view.tree());
    const wanted = [];
    for (const item of rows) {
      const { key } = item.process;
      if (!lines.has(key)) lines.set(key, createRow(view));
      lines.get(key).update(item);
      wanted.push(lines.get(key).element);
      const record = view.noteOf(key);
      if (!record) continue;
      if (notes.get(key)?.record !== record) notes.set(key, { record, element: noteRow(key, record) });
      wanted.push(notes.get(key).element);
    }
    const kept = new Set(rows.map((item) => item.process.key));
    for (const store of [lines, notes]) for (const key of store.keys()) if (!kept.has(key) || (store === notes && !view.noteOf(key))) store.delete(key);
    place(wanted);
    // Moving a line takes the focus off it. It goes back to the same control of the same process.
    if (focus?.key && focus.part && !body.contains(document.activeElement)) body.querySelector(`tr[data-key="${CSS.escape(focus.key)}"] [data-part="${focus.part}"]`)?.focus({ preventScroll: true });
    heads.forEach((head, index) => head.setAttribute("aria-sort", COLUMNS[index].id !== view.sort.column ? "none" : view.sort.descending ? "descending" : "ascending"));
    more.hidden = total <= rows.length;
    more.textContent = `Show ${Math.min(step, total - rows.length).toLocaleString()} more of ${total.toLocaleString()}`;
    syncPicks();
  }

  const lineOf = (key) => lines.get(key)?.element ?? null;
  return { element, render, syncPicks, lineOf };
}
