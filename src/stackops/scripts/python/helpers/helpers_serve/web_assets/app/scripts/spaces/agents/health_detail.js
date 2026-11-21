import { h, icon } from "/assets/scripts/dom.js";
import { commandDetail } from "../../data.js";
import { toolButton } from "../../space_kit.js";
import { avatar, keyValue, pill, searchInput, sectionHead } from "../../widgets.js";
import { KINDS, KIND_BY_ID, ORIGINS, matchesTerm } from "./health_model.js";
import { agentHash, callout, pathChip } from "./health_overview.js";
import { renderResources } from "./health_resources.js";

const AGENT_TOOLS = [["agents run-interactive", "Start a chat", "play"], ["agents run-prompt", "Run a prompt", "sparkle"]];

// What can be started for the agent on screen, with it filled in. A chat or a prompt is only offered for the agents those tools can drive.
function agentActions(agent, tools) {
  const row = h(
    "div",
    { class: "chip-row" },
    toolButton(tools, "agents init", { label: "Set up this project", glyph: "wrench", preset: { agent: agent.id } }),
    toolButton(tools, "agents add-mcp", { label: "Add a tool server", glyph: "plug", preset: { agents: agent.id } }),
  );
  for (const [path, label, glyph] of AGENT_TOOLS) {
    commandDetail(path).then(({ parameters }) => parameters.find((spec) => spec.name === "agent").choices.includes(agent.id) && row.append(toolButton(tools, path, { label, glyph, preset: { agent: agent.id } })));
  }
  return row;
}

function limitsFold(agent) {
  const remarks = [...agent.coverage.map((text) => ({ text, where: null })), ...agent.limits];
  return (
    remarks.length > 0 &&
    h(
      "details",
      { class: "fold health-limits" },
      h("summary", {}, icon("chevron", 13), h("span", { text: "What this check covers, and what it cannot see" }), h("b", { text: String(remarks.length) })),
      h("ul", {}, remarks.map(({ text, where }) => h("li", {}, h("p", { text }), where && h("span", { class: "about" }, h("span", { class: "dim", text: "About" }), pathChip(where))))),
    )
  );
}

// One agent, swapped in where the list was: what is wrong first, then everything it uses, one kind at a time.
export function renderDetail({ agent, kind, view, tools, previous, next }) {
  const term = () => view.term.trim().toLowerCase();
  const passes = (item) => (view.showEmpty || item.present) && (view.origins.size === 0 || view.origins.has(item.origin)) && matchesTerm(item, term());
  const ofKind = (id) => agent.items.filter((item) => item.kind === id);
  // With no kind in the address the view opens on the first kind that has something to show, and follows the search there.
  const choose = () => (KIND_BY_ID[kind] ? kind : (KINDS.find(({ id }) => ofKind(id).some(passes)) ?? KINDS.find(({ id }) => agent.counts[id] > 0) ?? KINDS[0]).id);
  const blurb = h("p", { class: "health-blurb dim" });
  const origins = Object.keys(ORIGINS).filter((origin) => agent.items.some((item) => item.origin === origin));
  // The source filter is shared between agents. One this agent has no chip for could not be cleared, so it is dropped on the way in.
  for (const origin of [...view.origins]) if (!origins.includes(origin)) view.origins.delete(origin);
  const holder = h("div", { class: "health-holder" });

  const tabs = KINDS.map((entry) => {
    const count = h("b");
    const tab = h("button", { class: "chip-button", type: "button", title: entry.blurb, onclick: () => (location.hash = agentHash(agent, entry.id)) }, icon(entry.glyph, 14), h("span", { text: entry.label }), count);
    return { id: entry.id, tab, count };
  });
  const originChips = origins.map((origin) => {
    const chip = h("button", { class: "chip-button", type: "button", title: ORIGINS[origin].hint, text: ORIGINS[origin].label });
    chip.addEventListener("click", () => {
      if (!view.origins.delete(origin)) view.origins.add(origin);
      paint();
    });
    return { origin, chip };
  });
  const emptyCount = h("b");
  const emptyChip = h("button", { class: "chip-button", type: "button", title: "Places this agent looks in where nothing was found." }, h("span", { text: "Empty places" }), emptyCount);
  const showEmpty = (on) => {
    view.showEmpty = on;
    paint();
  };
  emptyChip.addEventListener("click", () => showEmpty(!view.showEmpty));

  function paint() {
    const chosen = choose();
    const all = ofKind(chosen);
    const emptyPlaces = all.filter((item) => !item.present).length;
    blurb.textContent = KIND_BY_ID[chosen].blurb;
    tabs.forEach(({ id, tab, count }) => {
      const size = ofKind(id).filter(passes).length;
      count.textContent = String(size);
      tab.classList.toggle("zero", size === 0);
      tab.setAttribute("aria-pressed", String(id === chosen));
    });
    originChips.forEach(({ origin, chip }) => {
      chip.hidden = !view.origins.has(origin) && !agent.items.some((item) => item.origin === origin && (view.showEmpty || item.present));
      chip.setAttribute("aria-pressed", String(view.origins.has(origin)));
    });
    emptyChip.hidden = emptyPlaces === 0;
    emptyChip.setAttribute("aria-pressed", String(view.showEmpty));
    emptyCount.textContent = String(emptyPlaces);
    const hosts = chosen === "server" ? agent.items.filter((item) => item.kind === "configuration" && item.holdsServers && (view.showEmpty || item.present)) : [];
    holder.replaceChildren(
      renderResources({ agent, kind: chosen, items: all.filter(passes), term: term(), hiddenEmpty: view.showEmpty ? 0 : emptyPlaces, onShowEmpty: () => showEmpty(true) }),
      ...(hosts.length > 0 ? [sectionHead("Files that can list tool servers"), renderResources({ agent, kind: "configuration", items: hosts, term: "", hiddenEmpty: 0 })] : []),
    );
  }

  const search = searchInput({
    placeholder: `Find in ${agent.name}'s setup`,
    oninput: (value) => {
      view.term = value;
      paint();
    },
  });
  search.input.value = view.term;
  paint();
  // A remark about a handful of items is only useful if they can be found: searching for their state brings them up, whichever kind they are.
  const find = (word) => {
    view.term = word;
    search.input.value = word;
    if (KIND_BY_ID[kind]) location.hash = agentHash(agent);
    else paint();
  };
  const asides = agent.asides.map((aside) => h("p", { class: "aside" }, aside.text, h("button", { class: "link", type: "button", text: "Show", onclick: () => find(aside.find) })));
  const facts = [
    ["Program", agent.programPath ? pathChip(agent.programPath) : `“${agent.program}” was not found on this machine`],
    ["Checked from", pathChip(agent.directory)],
    agent.projectRoot !== agent.directory && ["Project", pathChip(agent.projectRoot)],
    ["Check", agent.thorough ? "In depth, made for this agent" : "Standard"],
  ].filter(Boolean);
  return h(
    "div",
    { class: "health-detail" },
    h(
      "div",
      { class: "health-nav" },
      h("a", { class: "btn small ghost", href: "#/agents/health" }, icon("back", 14), h("span", { text: "All agents" })),
      h("span", { class: "spacer" }),
      previous && h("a", { class: "btn small ghost", href: agentHash(previous), title: `Previous: ${previous.name}` }, icon("up", 14), h("span", { text: previous.name })),
      next && h("a", { class: "btn small ghost", href: agentHash(next), title: `Next: ${next.name}` }, h("span", { text: next.name }), icon("down", 14)),
    ),
    h(
      "header",
      { class: `health-agent${agent.installed ? "" : " absent"}` },
      avatar(agent.name, 52),
      h("div", { class: "agent-id" }, h("h3", {}, agent.name, pill(agent.status.label, agent.status.tone)), h("p", { class: "dim", text: agent.installed ? agent.version ?? "Version unknown" : "Not installed on this machine" })),
      keyValue(facts),
    ),
    agent.installed && agentActions(agent, tools),
    (agent.issues.length > 0 || agent.asides.length > 0) && h("div", { class: "health-issues" }, agent.issues.map(callout), asides.length > 0 && callout({ tone: "", title: "Worth knowing", extra: asides })),
    h("div", { class: "health-kinds", role: "group", "aria-label": "Kind" }, tabs.map(({ tab }) => tab)),
    h("div", { class: "health-filter" }, search.element, originChips.length > 1 && h("div", { class: "chip-row" }, originChips.map(({ chip }) => chip)), h("span", { class: "spacer" }), emptyChip),
    blurb,
    holder,
    limitsFold(agent),
  );
}
