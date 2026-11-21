"use strict";

const report = JSON.parse(document.getElementById("report-data").textContent);
const FOCUS_TITLES = { configuration: "Configuration", mcp: "MCP", hook: "Hooks", plugin: "Plugins", skill: "Skills", instructions: "Instructions" };
const ORIGIN_LABELS = { local: "local", global: "inherited · global", admin: "inherited · admin", system: "bundled · system" };
const STATE_TONES = { active: "good", available: "info", configured: "info", referenced: "info", disabled: "warn", missing: "muted", shadowed: "muted" };
const HEALTH_TONES = { installed: "good", "version error": "warn", missing: "muted", incomplete: "bad" };
const TONE_GLYPHS = { good: "✓", warn: "!", bad: "✕", muted: "–", info: "•" };
const agentById = new Map(report.agents.map((agent) => [agent.agent, agent]));
const resourceTexts = new WeakMap();

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function statusLabel(tone, text) {
  const label = el("span", "status");
  const mark = el("span", `mark ${tone}`, TONE_GLYPHS[tone]);
  mark.setAttribute("aria-hidden", "true");
  label.append(mark, el("span", "", text));
  return label;
}

function agentHealth(agent) {
  if (agent.errors.length > 0) return "incomplete";
  if (!agent.installed) return "missing";
  return agent.version_error === null ? "installed" : "version error";
}

function matchesFocus(resource, focus) {
  return focus === "all" || (focus === "mcp" ? resource.is_mcp : resource.kind === focus);
}

function presentCount(agent, focus) {
  return agent.resources.filter((resource) => resource.state !== "missing" && matchesFocus(resource, focus)).length;
}

function relativeTo(path, root, prefix) {
  if (path === root) return prefix;
  return path.startsWith(root) && "/\\".includes(path[root.length]) ? `${prefix}${path.slice(root.length)}` : null;
}

function homePath(path) {
  return relativeTo(path, report.home_directory, "~") ?? path;
}

function displayPath(path) {
  return relativeTo(path, report.project_root, ".") ?? homePath(path);
}

function kindLabel(resource) {
  return resource.is_mcp ? `${resource.kind} · MCP` : resource.kind;
}

function searchTerms(text) {
  return text.toLowerCase().split(/\s+/).filter(Boolean);
}

function resourceMatches(agent, resource, terms) {
  if (!resourceTexts.has(resource)) {
    resourceTexts.set(
      resource,
      [agent.display_name, agent.agent, resource.name, kindLabel(resource), ORIGIN_LABELS[resource.origin], resource.state, resource.path, resource.detail]
        .join(" ")
        .toLowerCase(),
    );
  }
  const text = resourceTexts.get(resource);
  return terms.every((term) => text.includes(term));
}

function agentHash(agentId, focus) {
  return focus === "all" ? `#agent/${agentId}` : `#agent/${agentId}/${focus}`;
}

function readRoute() {
  const parts = location.hash.slice(1).split("/");
  if (parts[0] === "search") {
    const query = decodeURIComponent(parts.slice(1).join("/"));
    if (query.trim()) return { view: "search", query };
  }
  if (parts[0] === "agent" && agentById.has(parts[1])) {
    return { view: "agent", agentId: parts[1], focus: report.focuses.includes(parts[2]) ? parts[2] : "all" };
  }
  if (parts[0] !== "overview" && report.agents.length === 1) return { view: "agent", agentId: report.agents[0].agent, focus: "all" };
  return { view: "overview" };
}
