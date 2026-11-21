"use strict";

const report = JSON.parse(document.getElementById("report-data").textContent);
const TONE_GLYPHS = { good: "✓", warn: "!", muted: "–" };

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

function homePath(path) {
  const home = report.home_directory;
  return path.startsWith(home) && (path.length === home.length || "/\\".includes(path[home.length])) ? `~${path.slice(home.length)}` : path;
}

function searchTerms(text) {
  return text.toLowerCase().split(/\s+/).filter(Boolean);
}

function tile(label, value) {
  const node = el("div", "tile");
  node.append(el("div", "tile-label", label), el("div", "tile-value", value.toLocaleString()));
  return node;
}

function toggleChip(label, count, pressed, onToggle) {
  const chip = el("button", "chip");
  chip.type = "button";
  chip.setAttribute("aria-pressed", String(pressed));
  chip.append(el("span", "", label), el("span", "chip-count", String(count)));
  chip.addEventListener("click", onToggle);
  return chip;
}

function copyButton(text) {
  const copy = el("button", "copy", "copy");
  copy.type = "button";
  copy.addEventListener("click", async () => {
    await navigator.clipboard.writeText(text);
    copy.textContent = "copied";
    setTimeout(() => { copy.textContent = "copy"; }, 1200);
  });
  return copy;
}

function listTable(headers, rows, emptyText) {
  const table = el("table");
  const headRow = el("tr");
  for (const header of headers) headRow.append(el("th", "", header));
  const thead = el("thead");
  thead.append(headRow);
  const tbody = el("tbody");
  tbody.append(...rows);
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
