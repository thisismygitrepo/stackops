function textCell(text, className) {
  return el("span", className ? `clamp ${className}` : "clamp", text);
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

function compareValues(left, right) {
  if (typeof left === "number" && typeof right === "number") return left - right;
  return String(left).localeCompare(String(right), undefined, { numeric: true, sensitivity: "base" });
}

function dataTable({ columns, rows, sort, onSortChange, emptyText, onRowClick }) {
  const wrap = el("div", "table-wrap");
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
    : [...rows].sort((left, right) => compareValues(columns[sort.column].value(left), columns[sort.column].value(right)) * sort.direction);
  for (const row of ordered) {
    const tr = el("tr", onRowClick ? "clickable" : "");
    for (const column of columns) {
      const td = el("td", column.className);
      td.append(column.cell(row));
      tr.append(td);
    }
    tr.addEventListener("click", (event) => {
      if (event.target.closest("a, button") || getSelection().toString() !== "") return;
      if (onRowClick) onRowClick(row);
      else tr.classList.toggle("expanded");
    });
    tbody.append(tr);
  }
  if (ordered.length === 0) {
    const tr = el("tr");
    const td = el("td", "empty", emptyText);
    td.colSpan = columns.length;
    tr.append(td);
    tbody.append(tr);
  }
  table.append(thead, tbody);
  wrap.append(table);
  return wrap;
}

function chipGroup({ label, counts, modes, labelFor, onChange }) {
  const group = el("div", "chips");
  group.append(el("span", "chips-label", label));
  for (const [value, count] of counts) {
    const chip = el("span", "chip");
    const only = el("button", "chip-only");
    only.type = "button";
    only.title = `Show only ${labelFor(value)}`;
    only.append(el("span", "chip-name", labelFor(value)), el("span", "chip-count", String(count)));
    const hide = el("button", "chip-hide");
    hide.type = "button";
    const sync = () => {
      const mode = modes.get(value) ?? "";
      chip.dataset.mode = mode;
      only.setAttribute("aria-pressed", String(mode === "only"));
      hide.textContent = mode === "hidden" ? "show" : "hide";
      hide.title = `${mode === "hidden" ? "Show" : "Hide"} ${labelFor(value)}`;
      hide.setAttribute("aria-label", hide.title);
    };
    for (const [button, mode] of [[only, "only"], [hide, "hidden"]]) {
      button.addEventListener("click", () => {
        if (modes.get(value) === mode) modes.delete(value);
        else modes.set(value, mode);
        sync();
        onChange();
      });
    }
    sync();
    chip.append(only, hide);
    group.append(chip);
  }
  return group;
}

function countBy(items, keyOf) {
  const counts = new Map();
  for (const item of items) counts.set(keyOf(item), (counts.get(keyOf(item)) ?? 0) + 1);
  return counts;
}

function messagePanel(title, messages, tone) {
  const panel = el("section", tone === "bad" ? "panel errors" : "panel");
  const heading = el("h3");
  if (tone === "bad") {
    const mark = el("span", "mark bad", TONE_GLYPHS.bad);
    mark.setAttribute("aria-hidden", "true");
    heading.append(mark);
  }
  heading.append(title);
  const list = el("ul", tone === "bad" ? "" : "notes");
  for (const message of messages) list.append(el("li", "", message));
  panel.append(heading, list);
  return panel;
}

function factList(facts) {
  const list = el("dl", "facts");
  for (const [label, value, title] of facts) {
    const item = el("div");
    const description = el("dd", "", value);
    if (title) description.title = title;
    item.append(el("dt", "", label), description);
    list.append(item);
  }
  return list;
}
