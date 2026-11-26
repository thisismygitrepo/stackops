import { h } from "/assets/scripts/dom.js";
import { agentButton } from "../agent_ask.js";
import { createView, toolButton } from "../space_kit.js";
import { segmented } from "../widgets.js";
import { createHealthSection } from "./agents/health.js";
import { createPromptsSection } from "./agents/prompts.js";
import { createRunningSection } from "./agents/running.js";
import { createWorkbench } from "./agents/workbench.js";

const SECTIONS = [["running", "Running"], ["prompts", "Prompts"], ["health", "Health"]];
// What "Ask an agent" in the page's heading says of the section or area on show (agent_brief.js describes a place). An area is known by its commands.
const PLACES = {
  running: {
    title: "Running agents", commands: ["agents status", "agents"],
    about: "The coding agents running in this machine's terminal sessions and what each is doing, with ways to start a chat, hand one a prompt, or ask one a side question.",
    ideas: ["Which of my agents are waiting for me?"],
  },
  prompts: {
    title: "Saved prompts", commands: ["agents run-prompt"], settings: "prompts",
    about: "Named pieces of context and instructions kept in prompts files, the person's own, this project's and the ones StackOps ships, ready to be handed to a coding agent.",
    ideas: ["Save a prompt that …"],
  },
  health: {
    title: "Agent health", commands: ["agents doctor", "agents add-skill", "agents add-mcp", "agents reset"],
    about: "How each coding agent's setup stands on this machine and in this project: its program, settings, skills, MCP servers, hooks, plugins and instruction files, and where each of those comes from.",
    ideas: ["Add an MCP server for …", "What is slowing my agents down at start?"],
  },
  browser: { commands: ["agents browser"] },
  desktop: { commands: ["agents computer"] },
  models: { commands: ["agents local"] },
  "second-brain": { commands: ["agents second-brain"] },
  loops: { commands: ["agents iter"] },
  setup: {
    title: "Setup and cleanup", commands: ["agents init", "agents config", "agents reset"],
    about: "Getting a project ready for coding agents, the lists agents draw from (prompts and MCP servers), and what a clean slate would remove.",
  },
};

// Each section is its own module with the same shape as a page: { element, show(route) }. The address is #/agents/<section>/…
// Under the switch sits the strip of things agents can be given, each a page of its own at #/agents/<area>. While one is open no section is.
export function createAgentsSpace(context) {
  const sections = {
    running: createRunningSection(context),
    prompts: createPromptsSection(context),
    health: createHealthSection(context),
  };
  const workbench = createWorkbench(context, (id) => agentButton(context.activity, PLACES[id], { small: true }));
  const left = {};
  let current = null;
  let here = "running";
  // The switch comes back to the agent or prompt a section was left on. Picking the section already on screen goes to its start.
  const picker = segmented(SECTIONS, (id) => {
    left[current] = location.hash;
    location.hash = (id !== current && left[id]) || (id === "running" ? "#/agents" : `#/agents/${id}`);
  });
  workbench.strip.addEventListener("click", () => (left[current] = location.hash));
  const element = createView(
    {
      title: "Agents", lede: "See what your coding agents are doing, and give them more to work with.",
      actions: [
        agentButton(context.activity, () => PLACES[here]),
        toolButton(context.tools, "agents ask", { label: "Ask a question", glyph: "chat" }),
        toolButton(context.tools, "agents run-prompt", { label: "Run a prompt", glyph: "sparkle" }),
        toolButton(context.tools, "agents run-interactive", { label: "Continue a session", glyph: "clock", preset: { followup: "on" } }),
        toolButton(context.tools, "agents run-interactive", { label: "Start a chat", glyph: "play", tone: "primary" }),
      ],
    },
    h("div", { class: "section-bar" }, picker.element),
    workbench.strip,
    Object.values(sections).map((section) => section.element),
    workbench.element,
  );
  return {
    element,
    show(route) {
      const id = workbench.show(route) ? "workbench" : Object.hasOwn(sections, route[0] ?? "") ? route[0] : "running";
      for (const [key, section] of Object.entries(sections)) section.element.hidden = key !== id;
      picker.set(id);
      if (current !== id) element.closest(".stage").scrollTo(0, 0);
      current = id;
      here = id === "workbench" ? route[0] : id;
      sections[id]?.show(route.slice(1));
    },
  };
}
