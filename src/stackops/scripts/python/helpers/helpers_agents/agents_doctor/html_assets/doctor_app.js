function tile(label, value, tone) {
  const node = el("div", "tile");
  const valueLine = el("div", "tile-value");
  if (tone) {
    const mark = el("span", `mark ${tone}`, TONE_GLYPHS[tone]);
    mark.setAttribute("aria-hidden", "true");
    valueLine.append(mark);
  }
  valueLine.append(value.toLocaleString());
  node.append(el("div", "tile-label", label), valueLine);
  return node;
}

function renderOverview() {
  const view = el("article");
  const incomplete = report.agents.filter((agent) => agent.errors.length > 0);
  const tiles = el("div", "tiles");
  tiles.append(
    tile("Agents inspected", report.agents.length, null),
    tile("Binaries installed", report.agents.filter((agent) => agent.installed).length, null),
    tile("Resources present", report.agents.reduce((sum, agent) => sum + presentCount(agent, "all"), 0), null),
    tile("Incomplete inspections", incomplete.length, incomplete.length > 0 ? "bad" : "good"),
  );
  view.append(
    el("h2", "", "Agent health"),
    tiles,
    factList([
      ["Working directory", homePath(report.working_directory), report.working_directory],
      ["Project root", homePath(report.project_root), report.project_root],
    ]),
  );
  if (incomplete.length > 0) {
    const errors = incomplete.flatMap((agent) => agent.errors.map((error) => `${agent.display_name}: ${error}`));
    view.append(messagePanel("Incomplete inspections", errors, "bad"));
  }
  const columns = [
    {
      title: "Agent", value: (agent) => agent.display_name,
      cell: (agent) => {
        const link = el("a", "name", agent.display_name);
        link.href = agentHash(agent.agent, "all");
        return link;
      },
    },
    { title: "Health", value: (agent) => agentHealth(agent), cell: (agent) => statusLabel(HEALTH_TONES[agentHealth(agent)], agentHealth(agent)) },
    { title: "Version", value: (agent) => agent.version ?? "", cell: (agent) => agent.version ?? el("span", "zero", "—") },
    ...report.focuses.map((focus) => ({
      title: FOCUS_TITLES[focus], className: "numeric", value: (agent) => presentCount(agent, focus),
      cell: (agent) => {
        const count = presentCount(agent, focus);
        if (count === 0) return el("span", "zero", "0");
        const link = el("a", "count-link", String(count));
        link.href = agentHash(agent.agent, focus);
        return link;
      },
    })),
  ];
  const matrixHost = el("div");
  const refresh = () => {
    matrixHost.replaceChildren(
      dataTable({
        columns, rows: report.agents, sort: overviewSort, onSortChange: refresh, emptyText: "No agents inspected",
        onRowClick: (agent) => { location.hash = agentHash(agent.agent, "all"); },
      }),
    );
  };
  refresh();
  const matrix = el("section", "block");
  matrix.append(el("h3", "", "Health matrix"), el("p", "lede", "Counts are resources present on disk. Select a count to open that agent filtered to the kind."), matrixHost);
  view.append(matrix);
  view.append(
    messagePanel(
      "Reading this report",
      [
        "Hook counts cover recognized persisted resources. Open an agent for source files and coverage limits.",
        "Preview a full reset with “agents reset <target>”. Add --resource hook to limit cleanup to hooks.",
      ],
      "plain",
    ),
  );
  return view;
}

const sidebar = el("nav", "sidebar");
sidebar.setAttribute("aria-label", "Agents");
const brand = el("div", "brand");
brand.append(el("h1", "", "Agents doctor"), el("p", "", homePath(report.working_directory)));
const agentFilter = el("input");
agentFilter.type = "search";
agentFilter.placeholder = "Filter agents";
agentFilter.setAttribute("aria-label", "Filter agents");
const agentList = el("ul", "nav-list");
const hint = el("p", "hint");
hint.append(el("kbd", "", "/"), " search · ", el("kbd", "", "j"), " ", el("kbd", "", "k"), " next / previous agent");
sidebar.append(brand, agentFilter, agentList, hint);
const searchInput = el("input");
searchInput.type = "search";
searchInput.placeholder = "Search every agent's resources";
searchInput.setAttribute("aria-label", "Search every agent's resources");
const topbar = el("header", "topbar");
topbar.append(searchInput, el("span", "generated", `Generated ${report.generated_at}`));
const main = el("main");
const content = el("div", "content");
content.append(topbar, main);
document.getElementById("app").append(sidebar, content);
let lastHash = "#overview";
let lastViewKey = "";

function navItem(href, title, subtitle, tone, active, count) {
  const item = el("li");
  const link = el("a", "nav");
  link.href = href;
  if (active) link.setAttribute("aria-current", "page");
  const text = el("span", "nav-text");
  text.append(el("span", "nav-title", title), el("span", "nav-sub", subtitle));
  if (tone) {
    const mark = el("span", `mark ${tone}`, TONE_GLYPHS[tone]);
    mark.setAttribute("aria-hidden", "true");
    link.append(mark);
  }
  link.append(text, el("span", "nav-count", count));
  item.append(link);
  return item;
}

function renderSidebar(route) {
  const terms = searchTerms(agentFilter.value);
  agentList.replaceChildren(navItem("#overview", "Overview", "Health matrix", null, route.view === "overview", String(report.agents.length)));
  for (const [title, installed] of [["Installed", true], ["Not installed", false]]) {
    const agents = report.agents.filter((agent) => {
      const text = `${agent.display_name} ${agent.agent} ${agentHealth(agent)} ${agent.version ?? ""}`.toLowerCase();
      return agent.installed === installed && terms.every((term) => text.includes(term));
    });
    if (agents.length === 0) continue;
    agentList.append(el("li", "nav-group", `${title} · ${agents.length}`));
    for (const agent of agents) {
      const health = agentHealth(agent);
      const subtitle = agent.version ?? (health === "installed" ? "version unavailable" : health);
      const active = route.view === "agent" && route.agentId === agent.agent;
      agentList.append(navItem(agentHash(agent.agent, "all"), agent.display_name, subtitle, HEALTH_TONES[health], active, String(presentCount(agent, "all"))));
    }
  }
}

function render() {
  const route = readRoute();
  renderSidebar(route);
  const viewKey = route.view === "agent" ? `agent/${route.agentId}` : route.view;
  if (route.view === "search") {
    if (document.activeElement !== searchInput) searchInput.value = route.query;
    main.replaceChildren(renderSearch(route.query));
  } else {
    lastHash = route.view === "agent" ? agentHash(route.agentId, route.focus) : "#overview";
    if (document.activeElement !== searchInput) searchInput.value = "";
    main.replaceChildren(route.view === "agent" ? renderAgent(agentById.get(route.agentId), route.focus) : renderOverview());
  }
  if (viewKey !== lastViewKey) window.scrollTo(0, 0);
  lastViewKey = viewKey;
}

agentFilter.addEventListener("input", () => renderSidebar(readRoute()));
searchInput.addEventListener("input", () => {
  history.replaceState(null, "", searchInput.value.trim() ? `#search/${encodeURIComponent(searchInput.value)}` : lastHash);
  render();
});
window.addEventListener("hashchange", render);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && event.target === searchInput) {
    searchInput.value = "";
    searchInput.blur();
    searchInput.dispatchEvent(new Event("input"));
    return;
  }
  if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey || event.altKey) return;
  if (event.key === "/") {
    event.preventDefault();
    searchInput.focus();
  } else if (event.key === "j" || event.key === "k") {
    const hrefs = [...agentList.querySelectorAll("a.nav")].map((link) => link.getAttribute("href"));
    const route = readRoute();
    const current = hrefs.indexOf(route.view === "agent" ? agentHash(route.agentId, "all") : "#overview");
    location.hash = hrefs[(current + (event.key === "j" ? 1 : hrefs.length - 1)) % hrefs.length];
  }
});
render();
