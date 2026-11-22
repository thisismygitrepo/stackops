import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../../live_panel.js";
import { replay } from "../../motion.js";
import { button, notice } from "../../widgets.js";
import { plural } from "../../words.js";
import { renderDetail } from "./health_detail.js";
import { prepare } from "./health_model.js";
import { renderOverview } from "./health_overview.js";

// The address is #/agents/health for everyone, #/agents/health/<agent> for one, and #/agents/health/<agent>/<kind> for one kind of thing it uses.
export function createHealthSection({ openReport, tools }) {
  const view = { filter: null, term: "", origins: new Set(), showEmpty: false };
  const holder = h("div", { class: "health" });
  let agents = null;
  let route = [];
  let shownKey = null;

  // The whole-machine report already has a home on the Reports page. A narrower one is built to order, and built again each time it is asked for,
  // so it shows the setup as it is now. The Reports page keeps one board per report and shows its last build while the new one is made.
  function openFullReport(agent) {
    const directory = agents[0].directory;
    if (!agent && directory === state.settings.workingDirectory) return void (location.hash = "#/reports/doctor");
    openReport({ title: agent ? `${agent.name} health` : "Agents health", blurb: `Checked from ${directory}.`, arguments: ["agents", "doctor", ...(agent ? [agent.id] : []), "--directory", directory, "--as-html"] });
  }

  function paint() {
    const index = agents.findIndex((candidate) => candidate.id === route[0]);
    const agent = agents[index];
    const key = agent?.id ?? "";
    // A kind tab goes through the address, and that rebuilds the agent's view, so a tab pressed with the keyboard is given its focus back.
    // A design choice: the rest of the view (the rows shown, an open fold) starts over on a tab press and on a refresh, which keeps one way of painting.
    const onTab = holder.contains(document.activeElement) && document.activeElement.closest(".health-kinds");
    holder.replaceChildren(agent ? renderDetail({ agent, kind: route[1], view, tools, previous: agents[index - 1], next: agents[index + 1] }) : renderOverview({ agents, view }));
    if (onTab) holder.querySelector(`.health-kinds [aria-pressed="true"]`)?.focus({ preventScroll: true });
    if (key === shownKey) return;
    if (agent) replay(holder, "health-swap");
    if (shownKey !== null && panel.element.getBoundingClientRect().top < 0) panel.element.scrollIntoView({ block: "start" });
    shownKey = key;
  }

  const panel = createLivePanel({
    title: "Health check", path: "agents doctor", extra: ["--json"], locked: ["agent", "resource"],
    actions: [button({ label: "Full report", glyph: "report", small: true, tone: "ghost", title: "Open the complete report for what is on screen", onclick: () => agents && openFullReport(agents.find((candidate) => candidate.id === route[0])) })],
    render: (data, { setCount, reload }) => {
      if (!Array.isArray(data) || data.length === 0) {
        agents = null;
        setCount("");
        return notice({ glyph: "alert", tone: "bad", title: "The check came back empty", body: "No agent could be looked at from this folder.", action: button({ label: "Try again", glyph: "refresh", small: true, onclick: reload }) });
      }
      agents = prepare(data);
      const installed = agents.filter((agent) => agent.installed).length;
      setCount(`${plural(agents.length, "agent")} · ${installed} installed`);
      paint();
      return holder;
    },
  });

  return {
    element: h("div", { class: "agents-section" }, panel.element),
    show(next) {
      route = next;
      panel.ensure();
      if (agents) paint();
    },
  };
}
