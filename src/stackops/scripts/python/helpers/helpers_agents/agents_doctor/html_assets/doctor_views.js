const ORIGIN_ORDER = ["local", "global", "admin", "system"];
const STATE_ORDER = ["active", "configured", "available", "referenced", "disabled", "shadowed", "missing"];
const RESOURCE_COLUMNS = [
  { title: "Name", className: "wide", value: (row) => row.resource.name, cell: (row) => textCell(row.resource.name, "name") },
  { title: "Kind", className: "nowrap", value: (row) => kindLabel(row.resource), cell: (row) => kindLabel(row.resource) },
  { title: "Source", className: "nowrap", value: (row) => ORIGIN_LABELS[row.resource.origin], cell: (row) => ORIGIN_LABELS[row.resource.origin] },
  { title: "State", value: (row) => row.resource.state, cell: (row) => statusLabel(STATE_TONES[row.resource.state], row.resource.state) },
  { title: "Path", className: "path", value: (row) => row.resource.path, cell: (row) => pathCell(row.resource.path) },
  { title: "Why", className: "wide", value: (row) => row.resource.detail, cell: (row) => textCell(row.resource.detail) },
];
const agentStates = new Map();
const overviewSort = { column: -1, direction: 1 };
const searchSort = { column: -1, direction: 1 };

function orderedCounts(rows, keyOf, order, modes) {
  const counts = countBy(rows, keyOf);
  for (const value of modes.keys()) if (!counts.has(value)) counts.set(value, 0);
  return [...counts].sort((left, right) => order.indexOf(left[0]) - order.indexOf(right[0]));
}

function contextBlock(agent) {
  const block = el("section", "block");
  block.append(el("h3", "", "Estimated context definition overhead"));
  if (agent.context.length === 0) {
    block.append(el("p", "lede", "No readable definition files contribute to this estimate."));
    return block;
  }
  const totals = agent.context.reduce(
    (sum, estimate) => ({ files: sum.files + estimate.files, words: sum.words + estimate.words, tokens: sum.tokens + estimate.tokens }),
    { files: 0, words: 0, tokens: 0 },
  );
  const table = el("table");
  const headRow = el("tr");
  for (const title of ["Source", "Files", "Words", "Est. tokens", "Share", "Cumulative"]) headRow.append(el("th", title === "Source" ? "" : "numeric", title));
  const thead = el("thead");
  thead.append(headRow);
  const tbody = el("tbody");
  let cumulative = 0;
  for (const estimate of agent.context) {
    cumulative += estimate.tokens;
    const percent = totals.tokens > 0 ? (estimate.tokens / totals.tokens) * 100 : 0;
    const share = el("div", "share");
    const meter = el("div", "meter");
    const fill = el("span");
    fill.style.width = `${percent}%`;
    meter.append(fill);
    share.append(meter, el("span", "", `${percent.toFixed(1)}%`));
    const tr = el("tr");
    const shareCell = el("td", "numeric");
    shareCell.append(share);
    tr.append(
      el("td", "name", estimate.source),
      el("td", "numeric", estimate.files.toLocaleString()),
      el("td", "numeric", estimate.words.toLocaleString()),
      el("td", "numeric", estimate.tokens.toLocaleString()),
      shareCell,
      el("td", "numeric", `${(totals.tokens > 0 ? (cumulative / totals.tokens) * 100 : 0).toFixed(1)}%`),
    );
    tbody.append(tr);
  }
  const footRow = el("tr");
  footRow.append(
    el("td", "", "Total"),
    el("td", "numeric", totals.files.toLocaleString()),
    el("td", "numeric", totals.words.toLocaleString()),
    el("td", "numeric", totals.tokens.toLocaleString()),
    el("td", "numeric", ""),
    el("td", "numeric", ""),
  );
  const tfoot = el("tfoot");
  tfoot.append(footRow);
  table.append(thead, tbody, tfoot);
  const wrap = el("div", "table-wrap");
  wrap.append(table);
  block.append(wrap, el("p", "caption", report.context_caption));
  return block;
}

function renderAgent(agent, focus) {
  if (!agentStates.has(agent.agent)) agentStates.set(agent.agent, { filter: "", origins: new Map(), states: new Map(), sort: { column: -1, direction: 1 } });
  const state = agentStates.get(agent.agent);
  const health = agentHealth(agent);
  const view = el("article");
  const head = el("header", "view-head");
  head.append(el("h2", "", agent.display_name), statusLabel(HEALTH_TONES[health], health));
  const facts = [
    ["Target", agent.agent],
    ["Executable", agent.path === null ? `${agent.executable} · not found on PATH` : displayPath(agent.path), agent.path],
    ["Version", agent.version ?? "—"],
    ["Inspection coverage", agent.support_level],
  ];
  if (agent.version_error !== null) facts.splice(3, 0, ["Version error", agent.version_error]);
  view.append(head, factList(facts));
  if (agent.errors.length > 0) view.append(messagePanel("Incomplete inspection", agent.errors, "bad"));

  const tabs = el("nav", "tabs");
  tabs.setAttribute("aria-label", "Resource kinds");
  for (const tabFocus of ["all", ...report.focuses]) {
    const tab = el("a", "tab");
    tab.href = agentHash(agent.agent, tabFocus);
    if (tabFocus === focus) tab.setAttribute("aria-current", "true");
    const total = agent.resources.filter((resource) => matchesFocus(resource, tabFocus)).length;
    tab.append(el("span", "", tabFocus === "all" ? "All" : FOCUS_TITLES[tabFocus]), el("span", "tab-count", String(total)));
    tabs.append(tab);
  }
  const inFocus = agent.resources.filter((resource) => matchesFocus(resource, focus)).map((resource) => ({ agent, resource }));
  const filter = el("input");
  filter.type = "search";
  filter.placeholder = "Filter resources";
  filter.setAttribute("aria-label", "Filter resources");
  filter.value = state.filter;
  const count = el("span", "count");
  const tableHost = el("div");
  const refresh = () => {
    const terms = searchTerms(state.filter);
    const shows = (modes, value) => modes.get(value) !== "hidden" && (modes.get(value) === "only" || ![...modes.values()].includes("only"));
    const rows = inFocus.filter(
      ({ resource }) => shows(state.origins, resource.origin) && shows(state.states, resource.state) && resourceMatches(agent, resource, terms),
    );
    count.textContent = `${rows.length} of ${inFocus.length}`;
    const emptyText = inFocus.length === 0 ? "None discovered" : "No resources match these filters";
    tableHost.replaceChildren(dataTable({ columns: RESOURCE_COLUMNS, rows, sort: state.sort, onSortChange: refresh, emptyText }));
  };
  filter.addEventListener("input", () => {
    state.filter = filter.value;
    refresh();
  });
  const controls = el("div", "controls");
  controls.append(
    filter,
    chipGroup({
      label: "Source", counts: orderedCounts(inFocus, (row) => row.resource.origin, ORIGIN_ORDER, state.origins),
      modes: state.origins, labelFor: (origin) => ORIGIN_LABELS[origin], onChange: refresh,
    }),
    chipGroup({
      label: "State", counts: orderedCounts(inFocus, (row) => row.resource.state, STATE_ORDER, state.states),
      modes: state.states, labelFor: (resourceState) => resourceState, onChange: refresh,
    }),
    count,
  );
  refresh();
  const resources = el("section", "block");
  resources.append(el("h3", "", "Resources"), tabs, controls, tableHost);
  view.append(resources, contextBlock(agent));
  if (agent.notes.length > 0) view.append(messagePanel("Coverage and inspection notes", agent.notes, "plain"));
  return view;
}

function renderSearch(query) {
  const terms = searchTerms(query);
  const rows = report.agents.flatMap((agent) =>
    agent.resources.filter((resource) => resourceMatches(agent, resource, terms)).map((resource) => ({ agent, resource })),
  );
  const agentCount = new Set(rows.map((row) => row.agent.agent)).size;
  const view = el("article");
  const tableHost = el("div");
  const agentColumn = {
    title: "Agent", value: (row) => row.agent.display_name,
    cell: (row) => {
      const link = el("a", "count-link", row.agent.display_name);
      link.href = agentHash(row.agent.agent, "all");
      return link;
    },
  };
  const refresh = () => {
    tableHost.replaceChildren(
      dataTable({ columns: [agentColumn, ...RESOURCE_COLUMNS], rows, sort: searchSort, onSortChange: refresh, emptyText: "No resources match this search" }),
    );
  };
  refresh();
  view.append(
    el("h2", "", "Search"),
    el(
      "p", "lede",
      `${rows.length} ${rows.length === 1 ? "resource" : "resources"} across ${agentCount} ${agentCount === 1 ? "agent" : "agents"} match “${query.trim()}”. ` +
        "Terms match names, kinds, sources, states, paths and reasons.",
    ),
    tableHost,
  );
  return view;
}
