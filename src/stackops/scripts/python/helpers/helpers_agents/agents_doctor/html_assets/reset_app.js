const ACTION_ORDER = ["delete", "disable", "read-only"];
const view = { filter: "", actions: new Set(), sort: { column: -1, direction: 1 }, changeSort: { column: -1, direction: 1 } };
const blocked = report.blockers.length > 0;
const planStatus = blocked
  ? { tone: "bad", title: "Blocked", detail: "This reset cannot proceed until the blockers below are resolved or left out of the selection." }
  : report.changes.length > 0
    ? { tone: "info", title: "Ready", detail: "Preview only: nothing has been changed. Add --apply to the same command to perform this reset permanently." }
    : { tone: "good", title: "Nothing to reset", detail: "No matching resources need changes." };
const agentCounts = new Map();
for (const entry of report.entries) agentCounts.set(entry.agent, (agentCounts.get(entry.agent) ?? 0) + 1);
const agentNames = [...agentCounts.keys()].sort((left, right) => left.localeCompare(right));
const routes = ["#summary", "#changes", "#resources", ...agentNames.map((name) => `#resources/${encodeURIComponent(name)}`)];

const rail = el("nav", "rail");
rail.setAttribute("aria-label", "Reset preview views");
const directory = report.selection.directory;
const brand = el("div", "brand");
brand.append(
  el("h1", "", "Agent reset preview"),
  el("p", "", directory.startsWith(report.home_directory) ? `~${directory.slice(report.home_directory.length)}` : directory),
);
const filter = el("input");
filter.type = "search";
filter.placeholder = "Filter resources and paths";
filter.setAttribute("aria-label", "Filter resources and paths");
const navList = el("ul", "nav-list");
const hint = el("p", "hint");
hint.append(el("kbd", "", "/"), " filter · ", el("kbd", "", "j"), " ", el("kbd", "", "k"), " next / previous view");
rail.append(brand, statusLabel(planStatus.tone, planStatus.title), filter, navList, hint);
const main = el("main");
document.getElementById("app").append(rail, main);

function currentRoute() {
  return routes.includes(location.hash) ? location.hash : "#summary";
}

function tile(label, value, tone) {
  const node = el("div", "tile");
  const valueLine = el("div", "tile-value");
  if (tone) valueLine.append(mark(tone));
  valueLine.append(value.toLocaleString());
  node.append(el("div", "tile-label", label), valueLine);
  return node;
}

function messagePanel(title, messages, className, tone) {
  const panel = el("section", `panel ${className}`);
  const heading = el("h3");
  if (tone) heading.append(mark(tone));
  heading.append(title);
  const list = el("ul");
  for (const message of messages) list.append(el("li", "", message));
  panel.append(heading, list);
  return panel;
}

function renderSummary() {
  const banner = el("section", blocked ? "banner bad" : "banner");
  const bannerTitle = el("div", "banner-title");
  bannerTitle.append(mark(planStatus.tone), el("h2", "", planStatus.title));
  banner.append(bannerTitle, el("p", "", planStatus.detail));
  const tiles = el("div", "tiles");
  tiles.append(
    tile("Resources in scope", report.entries.length, null),
    tile("Paths to delete", report.changes.filter((change) => change.action === "delete").length, null),
    tile("Files to edit", report.changes.filter((change) => change.action === "edit").length, null),
    tile("Blockers", report.blockers.length, blocked ? "bad" : "good"),
  );
  const facts = el("dl", "facts");
  const selection = report.selection;
  for (const [label, value] of [
    ["Agent", selection.agent], ["Scope", selection.scope], ["Resources", selection.resource], ["Match", selection.match ?? "—"],
    ["Workspace scan", selection.recursive ? "nested repositories" : "direct child repositories"], ["Workspace", report.project_root],
  ]) {
    const item = el("div");
    item.append(el("dt", "", label), el("dd", "", value));
    facts.append(item);
  }
  const nodes = [banner, tiles, facts];
  if (blocked) nodes.push(messagePanel("Blocked: reset cannot proceed", report.blockers, "bad", "bad"));
  if (report.notes.length > 0) nodes.push(messagePanel("Inspection notes", report.notes, "notes", null));
  return nodes;
}

function renderChanges(terms) {
  const changes = report.changes.filter((change) => terms.every((term) => `${change.action} ${change.path}`.toLowerCase().includes(term)));
  const columns = [
    { title: "Action", className: "nowrap", value: (change) => change.action, cell: (change) => statusLabel(ACTION_TONES[change.action], change.action) },
    { title: "Size", className: "nowrap", value: (change) => change.bytes, cell: (change) => formatSize(change) },
    { title: "Path", className: "source", value: (change) => change.path, cell: (change) => pathCell(change.path) },
  ];
  const head = el("div", "block-head");
  head.append(el("h2", "", "Planned changes"), el("span", "count", `${changes.length} of ${report.changes.length}`));
  return [
    head,
    el("p", "caption", "Deletes are permanent and nothing is backed up; edits rewrite the configuration in place."),
    dataTable({ columns, rows: changes, sort: view.changeSort, onSortChange: render, emptyText: "No planned changes match" }),
  ];
}

function renderResources(agent, terms) {
  const inAgent = report.entries.filter((entry) => agent === "" || entry.agent === agent);
  const entries = inAgent.filter((entry) => (view.actions.size === 0 || view.actions.has(entry.action)) && entryMatches(entry, terms));
  const chips = el("div", "chips");
  chips.append(el("span", "chips-label", "Action"));
  for (const action of ACTION_ORDER) {
    const total = inAgent.filter((entry) => entry.action === action).length;
    if (total === 0 && !view.actions.has(action)) continue;
    const chip = el("button", "chip");
    chip.type = "button";
    chip.setAttribute("aria-pressed", String(view.actions.has(action)));
    chip.append(el("span", "", action), el("span", "chip-count", String(total)));
    chip.addEventListener("click", () => {
      if (view.actions.has(action)) view.actions.delete(action);
      else view.actions.add(action);
      render();
    });
    chips.append(chip);
  }
  const columns = [
    { title: "Resource", className: "wide", value: (entry) => entry.name, cell: (entry) => stack(el("span", "name clamp", entry.name), el("span", "meta", entry.event)) },
    { title: "Agent", className: "nowrap", value: (entry) => entry.agent, cell: (entry) => entry.agent },
    { title: "Scope", className: "nowrap", value: (entry) => entry.scope, cell: (entry) => entry.scope },
    { title: "State", value: (entry) => entry.state, cell: (entry) => statusLabel(STATE_TONES[entry.state], entry.state) },
    { title: "Action", value: (entry) => entry.action, cell: (entry) => statusLabel(ACTION_TONES[entry.action], entry.action) },
    {
      title: "Source / command", className: "source", value: (entry) => entry.path,
      cell: (entry) => (entry.command ? stack(pathCell(entry.path), el("span", "meta clamp", entry.command)) : pathCell(entry.path)),
    },
  ];
  const head = el("div", "block-head");
  head.append(el("h2", "", agent === "" ? "Resources in scope" : `Resources in scope · ${agent}`), chips, el("span", "count", `${entries.length} of ${inAgent.length}`));
  return [head, dataTable({ columns, rows: entries, sort: view.sort, onSortChange: render, emptyText: "No resources match these filters" })];
}

function render() {
  const route = currentRoute();
  const labels = new Map([
    ["#summary", ["Summary", ""]], ["#changes", ["Planned changes", String(report.changes.length)]], ["#resources", ["All resources", String(report.entries.length)]],
    ...agentNames.map((name) => [`#resources/${encodeURIComponent(name)}`, [name, String(agentCounts.get(name))]]),
  ]);
  navList.replaceChildren();
  for (const [href, [title, count]] of labels) {
    if (href === "#resources") navList.append(el("li", "nav-group", "Resources by agent"));
    const link = el("a", "nav");
    link.href = href;
    link.setAttribute("aria-current", String(href === route));
    link.append(el("span", "nav-title", title), el("span", "nav-count", count));
    const item = el("li");
    item.append(link);
    navList.append(item);
  }
  const terms = searchTerms(view.filter);
  if (route === "#summary") main.replaceChildren(...renderSummary());
  else if (route === "#changes") main.replaceChildren(...renderChanges(terms));
  else main.replaceChildren(...renderResources(decodeURIComponent(route.slice("#resources/".length)), terms));
}

filter.addEventListener("input", () => {
  view.filter = filter.value;
  if (currentRoute() === "#summary" && view.filter.trim() !== "") history.replaceState(null, "", "#resources");
  render();
});
window.addEventListener("hashchange", () => {
  render();
  window.scrollTo(0, 0);
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && event.target === filter) {
    filter.value = "";
    filter.blur();
    filter.dispatchEvent(new Event("input"));
    return;
  }
  if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.key === "/") {
    event.preventDefault();
    filter.focus();
  } else if (event.key === "j" || event.key === "k") {
    location.hash = routes[(routes.indexOf(currentRoute()) + (event.key === "j" ? 1 : routes.length - 1)) % routes.length];
  }
});
render();
