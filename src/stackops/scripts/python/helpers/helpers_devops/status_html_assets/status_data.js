"use strict";

const report = JSON.parse(document.getElementById("report-data").textContent);
const LEVEL_TONES = { ready: "good", attention: "warn", error: "bad" };
const TONE_GLYPHS = { good: "✓", warn: "!", bad: "✕", muted: "–", info: "•" };

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

function pathCode(path) {
  const home = report.home_directory;
  const inHome = path.startsWith(home) && "/\\".includes(path[home.length]);
  const code = el("code", "", inHome ? `~${path.slice(home.length)}` : path);
  code.title = path;
  return code;
}

function stack(...children) {
  const node = el("span", "stack");
  node.append(...children);
  return node;
}

function searchTerms(text) {
  return text.toLowerCase().split(/\s+/).filter(Boolean);
}

function searchInput(placeholder) {
  const input = el("input");
  input.type = "search";
  input.placeholder = placeholder;
  input.setAttribute("aria-label", placeholder);
  return input;
}

function factGrid(facts) {
  const list = el("dl", "facts");
  for (const [label, value] of facts) {
    const item = el("div");
    const description = el("dd");
    description.append(value);
    item.append(el("dt", "", label), description);
    list.append(item);
  }
  return list;
}

function checklist(items) {
  const list = el("ul", "checklist");
  for (const item of items) {
    const row = el("li", "check");
    const text = stack(el("span", "name", `${item.label} · ${item.ok ? item.present : item.absent}`));
    if (item.detail) text.append(item.detail);
    row.append(mark(item.ok ? "good" : item.absentTone), text);
    list.append(row);
  }
  return list;
}

function simpleTable(headers, rows, emptyText) {
  const table = el("table");
  const headRow = el("tr");
  for (const header of headers) headRow.append(el("th", "", header));
  const thead = el("thead");
  thead.append(headRow);
  const tbody = el("tbody");
  for (const cells of rows) {
    const tr = el("tr");
    for (const cell of cells) {
      const td = el("td");
      td.append(cell);
      tr.append(td);
    }
    tbody.append(tr);
  }
  if (rows.length === 0) {
    const td = el("td", "empty", emptyText);
    td.colSpan = headers.length;
    const tr = el("tr");
    tr.append(td);
    tbody.append(tr);
  }
  table.append(thead, tbody);
  const wrap = el("div", "table-wrap");
  wrap.append(table);
  return wrap;
}

function progress(done, total, label) {
  const node = el("div", "progress");
  const meter = el("div", "meter");
  const fill = el("span");
  fill.style.width = `${total > 0 ? (done / total) * 100 : 0}%`;
  meter.append(fill);
  node.append(meter, el("span", "", label));
  return node;
}

function chipGroup(options, selected, onChange) {
  const group = el("div", "chips");
  for (const [value, label, count] of options) {
    const chip = el("button", "chip");
    chip.type = "button";
    chip.setAttribute("aria-pressed", String(selected.has(value)));
    chip.append(el("span", "", label), el("span", "chip-count", String(count)));
    chip.addEventListener("click", () => {
      if (selected.has(value)) selected.delete(value);
      else selected.add(value);
      chip.setAttribute("aria-pressed", String(selected.has(value)));
      onChange();
    });
    group.append(chip);
  }
  return group;
}
