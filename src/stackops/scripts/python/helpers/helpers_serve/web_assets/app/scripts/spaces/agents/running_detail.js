import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { toneOf } from "../../result_view.js";
import { avatar, button, copyChip, keyValue, pill } from "../../widgets.js";
import { humanize, plural, relativeTime } from "../../words.js";
import { callout } from "./health_overview.js";
import { renderPromptText } from "./prompts_text.js";

const ADDRESS = "#/agents/running";
const TASK_LABEL = /^(First retained request|Retained goal context):\s*/;
const REPLY_LABEL = /^Latest retained agent reply:/;
const KINDS = { user: "You", goal_context: "Its standing goal" };
const NEEDS_YOU = new Set(["waiting", "blocked"]);

// Pane ids repeat across sessions in some backends, so an agent's address carries both.
export const agentHash = (agent) => `${ADDRESS}/${encodeURIComponent(agent.session)}/${encodeURIComponent(agent.window_id)}`;
export const findAgent = (agents, [session, pane]) => agents.find((agent) => agent.session === session && agent.window_id === pane);
export const agentName = (agent) => agent.window_name || agent.agent_session_name || agent.harness;
export const taskText = (agent) => agent.task.replace(TASK_LABEL, "");
export const statusPills = (agent) => [pill(humanize(agent.status), NEEDS_YOU.has(agent.status) ? "warn" : toneOf(agent.status) || "accent"), agent.task_status && pill(humanize(agent.task_status), toneOf(agent.task_status))];

function pendingQuestion(prompt) {
  if (!prompt.found && !prompt.blocked) return null;
  const lines = Array.isArray(prompt.lines) ? prompt.lines.filter((line) => typeof line === "string").join("\n") : "";
  return lines || prompt.message || prompt.reason || "It says it needs an answer, but the question itself could not be read.";
}

const part = (title, when, ...content) => h("section", { class: "agent-part" }, h("header", {}, h("h3", { text: title }), when && h("span", { class: "dim", title: when, text: relativeTime(when) })), ...content);

// Built only when opened: a long session keeps hundreds of lines. `opened` outlives a repaint, so a refresh leaves an open fold open.
export function fold(opened, title, size, build) {
  const details = h("details", { class: "fold", open: opened.has(title) }, h("summary", {}, icon("chevron", 13), h("span", { text: title }), size > 0 && h("b", { text: String(size) })));
  if (details.open) details.append(build());
  else details.addEventListener("toggle", () => details.append(build()), { once: true });
  details.addEventListener("toggle", () => (details.open ? opened.add(title) : opened.delete(title)));
  return details;
}

function said(message) {
  return h("li", {}, h("header", {}, h("strong", { text: KINDS[message.kind] ?? humanize(message.kind) }), message.timestamp && h("span", { class: "dim", title: message.timestamp, text: relativeTime(message.timestamp) })), renderPromptText(message.text, ""));
}

// One running agent, swapped in where the cards were, drawn from what the list already downloaded. It borrows Health's one-agent header and callout.
export function renderAgent({ agent, opened, onAsk }) {
  const { history, process } = agent;
  const question = pendingQuestion(agent.prompt);
  const first = history.messages.find((message) => KINDS[message.kind]);
  const later = history.messages.filter((message) => message !== first);
  const limits = [...new Set([...agent.limitations, ...history.limitations, ...process.limitations])];
  const facts = [
    ["Folder", agent.cwd && copyChip(agent.cwd, tildify(agent.cwd, state.boot.home))],
    ["Where", [agent.session, agent.workspace_name, agent.tab_name].filter(Boolean).join(" › ")],
    ["Pane", copyChip(agent.window_id)],
    ["Conversation", process.session_id && copyChip(process.session_id)],
  ];
  return h(
    "div",
    { class: "agent-open" },
    h(
      "div",
      { class: "health-nav" },
      h("a", { class: "btn small ghost", href: ADDRESS }, icon("back", 14), h("span", { text: "All agents" })),
      h("span", { class: "spacer" }),
      button({ label: "Ask for an update", glyph: "chat", small: true, title: "Ask this agent what it is doing, without interrupting its work", onclick: onAsk }),
    ),
    h(
      "header",
      { class: "health-agent" },
      avatar(agent.harness || "agent", 52),
      h("div", { class: "agent-id" }, h("h3", {}, agentName(agent), statusPills(agent)), h("p", { class: "dim", text: [agent.harness, process.pid && `process ${process.pid}`].filter(Boolean).join(" · ") })),
      keyValue(facts),
    ),
    question && callout({ tone: "warn", title: "Waiting on you", extra: h("pre", { class: "agent-question", text: question }) }),
    part("The task", first?.timestamp, renderPromptText(first ? first.text : taskText(agent), "")),
    history.latest_reply
      ? part("Its latest reply", history.latest_reply_at, renderPromptText(history.latest_reply, ""))
      : agent.latest_activity && part("Latest activity", "", h("p", { class: "dim", text: agent.latest_activity })),
    history.latest_reply && agent.latest_activity && !REPLY_LABEL.test(agent.latest_activity) && h("p", { class: "agent-latest dim", text: agent.latest_activity }),
    later.length + history.omitted_messages > 0 &&
      fold(opened, "What else you told it", later.length, () =>
        h("ol", { class: "agent-said" }, history.omitted_messages > 0 && h("li", { class: "dim", text: `${plural(history.omitted_messages, "earlier message")} not shown.` }), later.map(said)),
      ),
    agent.capture && fold(opened, "On screen now", 0, () => h("pre", { class: "agent-screen", text: agent.capture })),
    limits.length > 0 && fold(opened, "What this view cannot see", limits.length, () => h("ul", { class: "agent-limits" }, limits.map((text) => h("li", { text })))),
  );
}
