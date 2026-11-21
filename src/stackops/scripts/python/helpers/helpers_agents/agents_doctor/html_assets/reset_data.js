"use strict";

const report = JSON.parse(document.getElementById("report-data").textContent);
const TONE_GLYPHS = { good: "✓", warn: "!", bad: "✕", muted: "–", info: "•" };
const STATE_TONES = { active: "good", available: "info", configured: "info", referenced: "info", disabled: "warn", missing: "muted", shadowed: "muted" };
const ACTION_TONES = { delete: "warn", disable: "warn", edit: "info", "read-only": "bad" };
const entryTexts = new WeakMap();

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function mark(tone) {
  const node = el("span", `mark ${tone}`, TONE_GLYPHS[tone]);
  node.setAttribute("aria-hidden", "true");
  return node;
}

function statusLabel(tone, text) {
  const label = el("span", "status");
  label.append(mark(tone), el("span", "", text));
  return label;
}

function displayPath(path) {
  for (const [root, prefix] of [[report.project_root, "."], [report.home_directory, "~"]]) {
    if (path === root) return prefix;
    if (path.startsWith(root) && "/\\".includes(path[root.length])) return `${prefix}${path.slice(root.length)}`;
  }
  return path;
}

function pathCell(path) {
  const line = el("span", "path-line");
  const code = el("code", "clamp", displayPath(path));
  code.title = path;
  line.append(code);
  if (navigator.clipboard) {
    const copy = el("button", "copy", "copy");
    copy.type = "button";
    copy.title = "Copy the full path";
    copy.addEventListener("click", async () => {
      await navigator.clipboard.writeText(path);
      copy.textContent = "copied";
      setTimeout(() => { copy.textContent = "copy"; }, 1200);
    });
    line.append(copy);
  }
  return line;
}

function formatSize(change) {
  let size = `${change.bytes} bytes`;
  if (change.bytes >= 1000) {
    const units = ["kB", "MB", "GB", "TB"];
    let value = change.bytes / 1000;
    let unit = 0;
    while (value >= 1000 && unit < units.length - 1) {
      value /= 1000;
      unit += 1;
    }
    size = `${value.toFixed(1)} ${units[unit]}`;
  }
  return change.files === null ? size : `${size} · ${change.files.toLocaleString()} ${change.files === 1 ? "file" : "files"}`;
}

function stack(...children) {
  const node = el("span", "stack");
  node.append(...children);
  return node;
}

function searchTerms(text) {
  return text.toLowerCase().split(/\s+/).filter(Boolean);
}

function entryMatches(entry, terms) {
  if (!entryTexts.has(entry)) {
    entryTexts.set(entry, [entry.agent, entry.scope, entry.name, entry.event, entry.command, entry.state, entry.action, entry.path].join(" ").toLowerCase());
  }
  const text = entryTexts.get(entry);
  return terms.every((term) => text.includes(term));
}

function dataTable({ columns, rows, sort, onSortChange, emptyText }) {
  const table = el("table");
  const headRow = el("tr");
  columns.forEach((column, index) => {
    const th = el("th", column.className);
    const button = el("button", "sort", column.title);
    button.type = "button";
    if (sort.column === index) {
      th.setAttribute("aria-sort", sort.direction === 1 ? "ascending" : "descending");
      button.append(el("span", "arrow", sort.direction === 1 ? "▲" : "▼"));
    }
    button.addEventListener("click", () => {
      if (sort.column !== index) {
        sort.column = index;
        sort.direction = 1;
      } else if (sort.direction === 1) {
        sort.direction = -1;
      } else {
        sort.column = -1;
      }
      onSortChange();
    });
    th.append(button);
    headRow.append(th);
  });
  const thead = el("thead");
  thead.append(headRow);
  const tbody = el("tbody");
  const ordered = sort.column < 0
    ? rows
    : [...rows].sort((left, right) => {
        const [first, second] = [columns[sort.column].value(left), columns[sort.column].value(right)];
        const order = typeof first === "number" ? first - second : first.localeCompare(second, undefined, { numeric: true, sensitivity: "base" });
        return order * sort.direction;
      });
  for (const row of ordered) {
    const tr = el("tr");
    for (const column of columns) {
      const td = el("td", column.className);
      td.append(column.cell(row));
      tr.append(td);
    }
    tr.addEventListener("click", (event) => {
      if (!event.target.closest("a, button") && getSelection().toString() === "") tr.classList.toggle("expanded");
    });
    tbody.append(tr);
  }
  if (ordered.length === 0) {
    const td = el("td", "empty", emptyText);
    td.colSpan = columns.length;
    const tr = el("tr");
    tr.append(td);
    tbody.append(tr);
  }
  table.append(thead, tbody);
  const wrap = el("div", "table-wrap");
  wrap.append(table);
  return wrap;
}
