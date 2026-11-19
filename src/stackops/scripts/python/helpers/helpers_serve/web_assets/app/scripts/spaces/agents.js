import { h } from "/assets/scripts/dom.js";
import { createView, toolButton } from "../space_kit.js";
import { segmented } from "../widgets.js";
import { createHealthSection } from "./agents/health.js";
import { createPromptsSection } from "./agents/prompts.js";
import { createRunningSection } from "./agents/running.js";
import { createWorkbenchSection } from "./agents/workbench.js";

const SECTIONS = [["running", "Running"], ["prompts", "Prompts"], ["health", "Health"], ["workbench", "Workbench"]];

// Each section is its own module with the same shape as a page: { element, show(route) }. The address is #/agents/<section>/…
export function createAgentsSpace(context) {
  const sections = {
    running: createRunningSection(context),
    prompts: createPromptsSection(context),
    health: createHealthSection(context),
    workbench: createWorkbenchSection(context),
  };
  const picker = segmented(SECTIONS, (id) => (location.hash = id === "running" ? "#/agents" : `#/agents/${id}`));
  const element = createView(
    {
      title: "Agents", lede: "See what your coding agents are doing, and give them more to work with.",
      actions: [
        toolButton(context.tools, "agents ask", { label: "Ask a question", glyph: "chat" }),
        toolButton(context.tools, "agents run-prompt", { label: "Run a prompt", glyph: "sparkle" }),
        toolButton(context.tools, "agents run-interactive", { label: "Start a chat", glyph: "play", tone: "primary" }),
      ],
    },
    h("div", { class: "section-bar" }, picker.element),
    Object.values(sections).map((section) => section.element),
  );
  return {
    element,
    show(route) {
      const id = Object.hasOwn(sections, route[0] ?? "") ? route[0] : "running";
      for (const [key, section] of Object.entries(sections)) section.element.hidden = key !== id;
      picker.set(id);
      sections[id].show(route.slice(1));
    },
  };
}
