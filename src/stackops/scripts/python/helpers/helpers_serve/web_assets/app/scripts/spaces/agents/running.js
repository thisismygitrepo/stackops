import { formatClock, h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { on, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { query } from "../../data.js";
import { createLivePanel } from "../../live_panel.js";
import { replay, rise } from "../../motion.js";
import { confirmAction } from "../../overlays.js";
import { toolButton } from "../../space_kit.js";
import { avatar, button, notice, pill, sectionHead } from "../../widgets.js";
import { plural } from "../../words.js";
import { agentHash, agentName, findAgent, fold, renderAgent, statusPills, taskText } from "./running_detail.js";

const FRESH_MILLISECONDS = 60_000;
const trim = (text, limit) => (text.length > limit ? `${text.slice(0, limit).trimEnd()}…` : text);

function agentCard(agent) {
  return h(
    "a",
    { class: "agent-card lit", href: agentHash(agent), title: "Open this agent" },
    h("header", {}, avatar(agent.harness || "agent", 44), h("div", {}, h("h3", { text: agentName(agent) }), h("span", { class: "dim", text: `${agent.harness} · ${agent.session}` })), statusPills(agent)[0]),
    agent.task && h("p", { class: "agent-task", text: trim(taskText(agent), 180) }),
    agent.latest_activity && h("p", { class: "agent-latest dim", text: trim(agent.latest_activity, 160) }),
    h("footer", {}, h("code", { class: "path", text: tildify(agent.cwd, state.boot.home) }), h("span", { class: "agent-go" }, statusPills(agent)[1], icon("arrow", 14))),
  );
}

// The address is #/agents/running for everyone and #/agents/running/<session>/<pane> for one agent.
export function createRunningSection({ activity, tools }) {
  const holder = h("div", { class: "agent-holder" });
  const opened = new Set();
  let skills = null;
  let snapshot = null;
  let route = [];
  let shownKey = null;

  // Asking spends model turns in each agent asked and can take minutes, so it is only ever a button with a question first, and never part of a refresh.
  // A design choice: asking everyone ignores what Options narrowed the list to; the live panel does not share its choices, and the question says "every".
  async function askForUpdate(agent) {
    const sure = await confirmAction({
      title: `Ask ${agent ? agentName(agent) : "every running agent"} for an update?`, confirm: "Ask",
      body: `${agent ? "It is" : "Each one is"} asked how it is doing and what it is working on, in a copy of its conversation, so its own work is not interrupted. This uses the agent's model and can take a few minutes.`,
    });
    if (!sure) return;
    const only = !agent ? [] : snapshot.backend === "t3" ? ["--agent-session", agent.window_id] : ["--session", agent.session, "--pane", agent.window_id];
    const runArguments = ["agents", "status", "--btw", "--format", "rich", "--backend", snapshot.backend, ...(snapshot.backend === "tuios" && snapshot.server ? ["--server", snapshot.server] : []), ...only];
    activity.start({ title: agent ? `Update from ${agentName(agent)}` : "Updates from your agents", emoji: "💬", arguments: runArguments, interactive: false, reveal: true }).catch((error) => toast(error.message));
  }
  const askButton = button({ label: "Ask for an update", glyph: "chat", small: true, tone: "ghost", title: "Ask every running agent what it is doing, without interrupting its work", onclick: () => askForUpdate(null) });
  askButton.hidden = true;

  function paint() {
    const agent = findAgent(snapshot.agents, route);
    // An agent that has finished since it was opened has nothing left to show, so the list takes its place and it is forgotten: if it comes back
    // it is a card again. The address follows only while this tab is on show, since a list can arrive after the tab was left.
    if (route.length > 0 && !agent) {
      route = [];
      if (!panel.element.closest("[hidden]")) history.replaceState(null, "", "#/agents/running");
    }
    const key = agent ? route.join("\n") : "";
    if (key !== shownKey) opened.clear();
    askButton.hidden = Boolean(agent) || snapshot.agents.length === 0;
    // What the status command says it could not look at goes under the list. Without it a list that is short for a stated reason reads as complete.
    const unseen = snapshot.limitations.length > 0 ? [fold(opened, "What this list cannot see", snapshot.limitations.length, () => h("ul", { class: "agent-limits" }, snapshot.limitations.map((text) => h("li", { text }))))] : [];
    if (agent) holder.replaceChildren(renderAgent({ agent, opened, onAsk: () => askForUpdate(agent) }));
    else if (snapshot.agents.length > 0) holder.replaceChildren(rise(h("div", { class: "card-grid wide" }, snapshot.agents.map(agentCard))), ...unseen);
    else holder.replaceChildren(notice({ glyph: "bot", title: "No agents are running", body: "Start a chat or hand off a prompt and it will appear here.", action: toolButton(tools, "agents run-interactive", { label: "Start a chat", tone: "primary" }) }), ...unseen);
    if (key === shownKey) return;
    if (agent) replay(holder, "health-swap");
    if (shownKey !== null && panel.element.getBoundingClientRect().top < holder.closest(".stage").getBoundingClientRect().top) panel.element.scrollIntoView({ block: "start" });
    shownKey = key;
  }

  // A design choice: Format, Output, Force and Btw are left out of Options. This panel re-runs by itself on every change and refresh,
  // and those four would break its JSON, write files as a path is typed, or spend model turns in every agent each time.
  const panel = createLivePanel({
    title: "Agents right now", path: "agents status", extra: ["--json"], locked: ["output_format", "output", "force", "btw"], skeletonShape: "card", actions: [askButton],
    render: (data, { setCount }) => {
      snapshot = { backend: data?.backend, server: data?.server, agents: data?.agents ?? [], limitations: data?.limitations ?? [], observedAt: Date.parse(data?.observed_at) };
      // T3 Code has projects where the other backends have sessions. The time is the snapshot's own, so a list left on screen shows its age.
      const coverage = data?.coverage ?? {};
      const checked = "projects" in coverage ? plural(coverage.projects, "project") : plural(coverage.sessions_inspected ?? 0, "session");
      setCount(`${plural(snapshot.agents.length, "agent")} · ${checked} checked${Number.isNaN(snapshot.observedAt) ? "" : ` · as of ${formatClock(snapshot.observedAt / 1000)}`}`);
      paint();
      return holder;
    },
  });

  // "Right now" is the point of this list, so one that is over a minute old when the tab is arrived at is asked for again. The first look can
  // be that old too, since it shares Home's copy. Age is judged by the snapshot's own time: a browser clock that disagrees with the server's
  // costs one extra run per arrival, and never a loop.
  let reloading = false;
  async function arrive() {
    const old = () => Date.now() - snapshot?.observedAt > FRESH_MILLISECONDS;
    if (!snapshot) await panel.load();
    else if (!old()) return panel.ensure();
    if (!old() || reloading) return;
    reloading = true;
    await panel.load(true);
    reloading = false;
  }

  const skillCombo = createCombo({
    large: true, glyph: "sparkle", label: "Add a skill", placeholder: "Add a skill — type to search", emptyText: "No skill matches that.",
    suggest: async (text) => {
      // Asked once and kept, failure included: a list that did not load says so once and reads as empty, instead of running again on every keystroke.
      skills ??= query(["agents", "add-skill", "--list", "--json"]).then(
        ({ json }) => Object.entries(json ?? {}).map(([name, detail]) => ({ name, ...detail })),
        (error) => {
          toast(`The skill list didn't load: ${error.message}`);
          return [];
        },
      );
      const word = text.trim().toLowerCase();
      return (await skills)
        .filter((skill) => `${skill.name} ${skill.group} ${skill.source}`.toLowerCase().includes(word))
        .map((skill) => ({ value: skill.name, label: skill.name, hint: skill.source, lead: avatar(skill.name, 32), trail: pill(skill.group, ""), fill: false }));
    },
    onPick: (option) => {
      skillCombo.setValue("");
      skillCombo.input.blur();
      tools.open("agents add-skill", { preset: { skill_name: option.value } });
    },
  });

  const servers = h("div", { class: "chip-row" });
  let asked = false;
  async function loadServers() {
    asked = true;
    try {
      const { json } = await query(["agents", "add-mcp", "--list", "--json"]);
      const names = Array.isArray(json) ? json : [];
      servers.replaceChildren(
        ...names.map((name) => h("button", { class: "chip-button", type: "button", onclick: () => tools.open("agents add-mcp", { preset: { requested_mcp_servers: name } }) }, h("span", { text: name }))),
        ...(names.length === 0 ? [h("span", { class: "dim", text: "No tool servers in your catalogs yet." })] : []),
      );
    } catch (error) {
      servers.replaceChildren(h("span", { class: "dim", text: `The server list didn't load: ${error.message}` }));
      asked = false;
    }
  }

  const element = h(
    "div",
    { class: "agents-section" },
    panel.element,
    h(
      "section",
      { class: "panel" },
      h("header", { class: "panel-head" }, h("h2", { text: "Teach them something" })),
      h("div", { class: "panel-body teach" }, h("div", {}, sectionHead("Skills"), skillCombo.element), h("div", {}, sectionHead("Tool servers"), servers)),
    ),
  );
  // Both lists come from catalogs that a finished run or a saved file may have changed, so they are asked for again when the data is marked stale.
  on("data-stale", () => {
    skills = null;
    asked = false;
    if (!element.closest("[hidden]")) loadServers();
  });

  return {
    element,
    show(next) {
      route = next;
      if (snapshot) paint();
      arrive();
      if (!asked) loadServers();
    },
  };
}
