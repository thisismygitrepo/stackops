import { h, icon } from "/assets/scripts/dom.js";
import { rise } from "../../motion.js";
import { avatar, callout, highlight, notice, pathChip, pill, searchInput } from "../../widgets.js";
import { plural } from "../../words.js";
import { KINDS, matchesTerm, summarize } from "./health_model.js";

const FILTERS = [
  { id: "all", label: "Known agents", test: () => true },
  { id: "installed", label: "Installed", test: (agent) => agent.installed },
  { id: "attention", label: "Need attention", test: (agent) => agent.issues.length > 0 },
  { id: "absent", label: "Not installed", test: (agent) => !agent.installed },
];

export const agentHash = (agent, kind) => `#/agents/health/${encodeURIComponent(agent.id)}${kind ? `/${kind}` : ""}`;

// While a search finds things inside an agent's setup, its numbers count the finds, so the row says where they are.
function matrixRow(agent, term, found) {
  const hits = found.length;
  const sub = hits > 0 ? `${hits === 1 ? "1 match" : `${hits.toLocaleString()} matches`} in its setup` : agent.issues[0]?.title ?? agent.version ?? (agent.installed ? "Version unknown" : `“${agent.program}” was not found`);
  const row = h(
    "tr",
    { class: `health-row${agent.installed ? "" : " absent"}${hits > 0 ? " finds" : ""}`, tabindex: "0", role: "link", "aria-label": `Open ${agent.name}` },
    h("td", { class: "who" }, h("div", {}, avatar(agent.name, 34), h("span", { class: "who-text" }, h("strong", {}, highlight(agent.name, term)), h("span", { class: hits > 0 ? "hit" : "dim", text: sub })))),
    h("td", {}, pill(agent.status.label, agent.status.tone), agent.asides.length > 0 && h("span", { class: "aside-dot", title: agent.asides.map((aside) => aside.text).join(" ") }, icon("info", 14))),
    KINDS.map((kind) => {
      const count = hits > 0 ? found.filter((item) => item.kind === kind.id).length : agent.counts[kind.id];
      const title = hits > 0 ? `${count === 1 ? "1 match" : `${count} matches`} in ${kind.label.toLowerCase()} — open` : `${plural(count, kind.one)} — open`;
      return h("td", { class: "tally" }, count > 0 ? h("a", { href: agentHash(agent, kind.id), title, text: count.toLocaleString() }) : h("span", { class: "none", text: "–" }));
    }),
    h("td", { class: "go" }, icon("chevron", 15)),
  );
  const open = () => (location.hash = agentHash(agent));
  row.addEventListener("click", (event) => !(event.target instanceof Element && event.target.closest("a")) && open());
  row.addEventListener("keydown", (event) => event.key === "Enter" && event.target === row && open());
  return row;
}

// `view` outlives a repaint, so the chosen filter and the search survive a refresh and a trip into one agent.
export function renderOverview({ agents, view }) {
  const { verdict, troubled, counts } = summarize(agents);
  view.filter ??= counts.installed > 0 ? "installed" : "all";
  const body = h("tbody");
  const shown = h("span", { class: "count" });
  const empty = h("div", { class: "health-empty", hidden: true });
  const scroll = h(
    "div",
    { class: "table-scroll" },
    h(
      "table",
      { class: "health-matrix" },
      h("thead", {}, h("tr", {}, h("th", { text: "Agent" }), h("th", { text: "State" }), KINDS.map((kind) => h("th", { class: "tally", title: kind.blurb }, h("span", {}, icon(kind.glyph, 13), kind.short))), h("th"))),
      body,
    ),
  );
  const tabs = FILTERS.map((filter) => {
    const tab = h("button", { class: `health-tab ${filter.id}${counts[filter.id] === 0 ? " zero" : ""}`, type: "button" }, h("strong", { text: counts[filter.id].toLocaleString() }), h("span", { text: filter.label }));
    tab.addEventListener("click", () => {
      view.filter = filter.id;
      paint();
    });
    return tab;
  });

  function paint() {
    const term = view.term.trim().toLowerCase();
    const filter = FILTERS.find((candidate) => candidate.id === view.filter);
    const rows = agents
      .filter(filter.test)
      .map((agent) => ({ agent, found: term === "" ? [] : agent.items.filter((item) => item.present && matchesTerm(item, term)) }))
      .filter(({ agent, found }) => term === "" || found.length > 0 || agent.text.includes(term));
    tabs.forEach((tab, index) => tab.setAttribute("aria-pressed", String(FILTERS[index].id === view.filter)));
    body.replaceChildren(...rows.map(({ agent, found }) => matrixRow(agent, term, found)));
    shown.textContent = rows.some(({ found }) => found.length > 0) ? "Numbers count what was found" : rows.length === agents.length ? "" : `Showing ${rows.length} of ${agents.length}`;
    scroll.hidden = rows.length === 0;
    empty.hidden = rows.length > 0;
    if (rows.length === 0) {
      const nothing = term !== "" ? { title: "Nothing matches that", body: `No agent in “${filter.label}” has “${view.term.trim()}” in its name or its setup.` } : { title: "Nobody here", body: "No agent falls under this heading right now." };
      empty.replaceChildren(notice({ glyph: term !== "" ? "search" : "bot", ...nothing }));
    }
  }

  const search = searchInput({
    placeholder: "Find an agent, a skill, a file…",
    oninput: (value) => {
      view.term = value;
      paint();
    },
  });
  search.input.value = view.term;
  paint();
  return rise(
    h(
      "div",
      { class: "health-overview" },
      h(
        "div",
        { class: `health-hero ${verdict.tone}` },
        h("span", { class: "health-badge" }, icon(verdict.glyph, 26)),
        h("div", { class: "health-verdict" }, h("h3", { text: verdict.title }), h("p", { text: verdict.body })),
        h("div", { class: "health-where" }, h("span", { class: "overline", text: "Checked from" }), pathChip(agents[0].directory)),
      ),
      troubled.length > 0 && h("div", { class: "health-issues" }, troubled.flatMap((agent) => agent.issues.map((issue) => callout({ ...issue, lead: agent.name, href: agentHash(agent) })))),
      h("div", { class: "health-bar" }, h("div", { class: "health-tabs", role: "group", "aria-label": "Narrow the list" }, tabs), h("span", { class: "spacer" }), shown, search.element),
      scroll,
      empty,
    ),
  );
}
