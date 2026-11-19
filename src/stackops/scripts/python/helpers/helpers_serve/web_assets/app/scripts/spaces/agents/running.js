import { h, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { query } from "../../data.js";
import { createLivePanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { toneOf } from "../../result_view.js";
import { toolButton } from "../../space_kit.js";
import { avatar, notice, pill, sectionHead } from "../../widgets.js";
import { humanize, plural } from "../../words.js";

const trim = (text, limit) => (text.length > limit ? `${text.slice(0, limit).trimEnd()}…` : text);

export function createRunningSection({ tools }) {
  let skills = null;

  const panel = createLivePanel({
    title: "Agents right now", path: "agents status", extra: ["--json"], skeletonShape: "card",
    render: (data, { setCount }) => {
      const agents = data?.agents ?? [];
      const coverage = data?.coverage ?? {};
      setCount(`${plural(agents.length, "agent")} · ${plural(coverage.sessions_inspected ?? 0, "session")} checked`);
      if (agents.length === 0) return notice({ glyph: "bot", title: "No agents are running", body: "Start a chat or hand off a prompt and it will appear here.", action: toolButton(tools, "agents run-interactive", { label: "Start a chat", tone: "primary" }) });
      return rise(
        h(
          "div",
          { class: "card-grid wide" },
          agents.map((agent) =>
            h(
              "article",
              { class: "agent-card lit" },
              h("header", {}, avatar(agent.harness || "agent", 44), h("div", {}, h("h3", { text: agent.window_name || agent.agent_session_name || agent.harness }), h("span", { class: "dim", text: `${agent.harness} · ${agent.session}` })), pill(humanize(agent.status), toneOf(agent.status) || "accent")),
              agent.task && h("p", { class: "agent-task", text: trim(agent.task.replace(/^First retained request:\s*/, ""), 180) }),
              agent.latest_activity && h("p", { class: "agent-latest dim", text: trim(agent.latest_activity, 160) }),
              h("footer", {}, h("code", { class: "path", text: tildify(agent.cwd, state.boot.home) }), agent.task_status && pill(humanize(agent.task_status), toneOf(agent.task_status))),
            ),
          ),
        ),
      );
    },
  });

  const skillCombo = createCombo({
    large: true, glyph: "sparkle", label: "Add a skill", placeholder: "Add a skill — type to search", emptyText: "No skill matches that.",
    suggest: async (text) => {
      skills ??= await query(["agents", "add-skill", "--list", "--json"]).then(({ json }) => Object.entries(json ?? {}).map(([name, detail]) => ({ name, ...detail })));
      const word = text.trim().toLowerCase();
      return skills
        .filter((skill) => `${skill.name} ${skill.group} ${skill.source}`.toLowerCase().includes(word))
        .slice(0, 12)
        .map((skill) => ({ value: skill.name, label: skill.name, hint: skill.source, lead: avatar(skill.name, 32), trail: pill(skill.group, ""), fill: false }));
    },
    onPick: (option) => {
      skillCombo.setValue("");
      skillCombo.input.blur();
      tools.open("agents add-skill", { preset: { skill_name: option.value } });
    },
  });

  const servers = h("div", { class: "chip-row" });
  async function loadServers() {
    try {
      const { json } = await query(["agents", "add-mcp", "--list", "--json"]);
      servers.replaceChildren(
        ...(Array.isArray(json) ? json : []).map((name) => h("button", { class: "chip-button", type: "button", onclick: () => tools.open("agents add-mcp", { preset: { requested_mcp_servers: name } }) }, h("span", { text: name }))),
      );
    } catch (error) {
      servers.replaceChildren(h("span", { class: "dim", text: `The server list didn't load: ${error.message}` }));
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
  let asked = false;
  return {
    element,
    show() {
      panel.ensure();
      if (!asked) loadServers();
      asked = true;
    },
  };
}
