const active = new Set();
const search = el("input");
const count = el("span", "count");
const tableHost = el("div");

function render() {
  const rows = view.rows(searchTerms(search.value), active);
  count.textContent = `${rows.length} of ${view.total}`;
  tableHost.replaceChildren(listTable(view.headers, rows, view.emptyText));
}

const view = report.mode === "path" ? pathView(render) : variablesView();
const masthead = el("header", "masthead");
const hint = el("span", "hint");
hint.append(el("kbd", "", "/"), " filter");
masthead.append(el("h1", "", view.title), el("span", "meta", `Generated ${report.generated_at}`), hint);
const tiles = el("div", "tiles");
for (const [label, value] of view.tiles) tiles.append(tile(label, value));
search.type = "search";
search.placeholder = view.placeholder;
search.setAttribute("aria-label", view.placeholder);
search.addEventListener("input", render);
const chips = el("div", "chips");
for (const chip of view.chips) {
  const button = toggleChip(chip.label, chip.count, false, () => {
    if (active.has(chip.key)) active.delete(chip.key);
    else active.add(chip.key);
    button.setAttribute("aria-pressed", String(active.has(chip.key)));
    render();
  });
  chips.append(button);
}
const controls = el("div", "controls");
controls.append(search, chips, count);
const main = el("main");
if (view.note) main.append(el("p", "note", view.note));
main.append(tableHost);
document.getElementById("app").append(masthead, tiles, controls, main);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && event.target === search) {
    search.value = "";
    search.blur();
    render();
  } else if (event.key === "/" && !(event.target instanceof HTMLInputElement) && !event.metaKey && !event.ctrlKey && !event.altKey) {
    event.preventDefault();
    search.focus();
  }
});
render();
