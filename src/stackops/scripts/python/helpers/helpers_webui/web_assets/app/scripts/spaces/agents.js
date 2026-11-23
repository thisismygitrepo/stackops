import { h } from "/assets/scripts/dom.js";
import { createView, toolButton } from "../space_kit.js";
import { segmented } from "../widgets.js";
import { createHealthSection } from "./agents/health.js";
import { createPromptsSection } from "./agents/prompts.js";
import { createRunningSection } from "./agents/running.js";
import { createWorkbench } from "./agents/workbench.js";

const SECTIONS = [["running", "Running"], ["prompts", "Prompts"], ["health", "Health"]];

// Each section is its own module with the same shape as a page: { element, show(route) }. The address is #/agents/<section>/…
// Under the switch sits the strip of things agents can be given, each a page of its own at #/agents/<area>. While one is open no section is.
export function createAgentsSpace(context) {
  const sections = {
    running: createRunningSection(context),
    prompts: createPromptsSection(context),
    health: createHealthSection(context),
  };
  const workbench = createWorkbench(context);
  const left = {};
  let current = null;
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
      sections[id]?.show(route.slice(1));
    },
  };
}
