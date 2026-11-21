import { h } from "/assets/scripts/dom.js";
import { replay } from "../../motion.js";
import { glyphTile } from "../../widgets.js";
import { createBrainArea } from "./workbench_brain.js";
import { createBrowserArea } from "./workbench_browser.js";
import { createComputerArea } from "./workbench_computer.js";
import { createLocalArea } from "./workbench_local.js";
import { createParallelArea } from "./workbench_parallel.js";
import { createSetupArea } from "./workbench_setup.js";

const AREAS = [
  { id: "browser", label: "Browser automation", caption: "A browser for agents", glyph: "browser", hue: 205, create: createBrowserArea },
  { id: "desktop", label: "Desktop control", caption: "Use of this computer", glyph: "monitor", hue: 262, create: createComputerArea },
  { id: "models", label: "Local models", caption: "AI on this machine", glyph: "server", hue: 160, create: createLocalArea },
  { id: "second-brain", label: "Second Brain", caption: "Ask and remember", glyph: "book", hue: 330, create: createBrainArea },
  { id: "parallel", label: "Parallel runs", caption: "Many agents, one job", glyph: "lanes", hue: 32, create: createParallelArea },
  { id: "setup", label: "Setup and cleanup", caption: "Prepare, start fresh", glyph: "wrench", hue: 290, create: createSetupArea },
];

// Each area is built and loaded the first time it is shown. The address is #/agents/workbench/<area>.
export function createWorkbenchSection(context) {
  const built = new Map();
  const tabs = new Map(
    AREAS.map((area) => {
      const status = h("span", { class: "wb-tab-status", text: area.caption });
      const tab = h("a", { class: "wb-tab", href: `#/agents/workbench/${area.id}` }, glyphTile(area.glyph, area.hue, 32), h("span", { class: "wb-tab-text" }, h("strong", { text: area.label }), status));
      return [area.id, { tab, status }];
    }),
  );
  const stage = h("div", { class: "wb-stage" });
  const strip = h("nav", { class: "wb-tabs", "aria-label": "Workbench areas" }, [...tabs.values()].map(({ tab }) => tab));
  const element = h("div", { class: "agents-section workbench" }, strip, stage);
  let current = null;

  function build(area) {
    const { status } = tabs.get(area.id);
    const made = area.create(context, {
      setStatus(text, tone = "") {
        status.textContent = text;
        status.dataset.tone = tone || "quiet";
      },
    });
    built.set(area.id, made);
    stage.append(made.element);
    return made;
  }

  return {
    element,
    show(route) {
      const asked = AREAS.find((candidate) => candidate.id === route[0]);
      const area = asked ?? AREAS.find((candidate) => candidate.id === current) ?? AREAS[0];
      // Coming back through the section switch lands on the area that was open, and the address says so.
      if (!asked && current) history.replaceState(null, "", `#/agents/workbench/${area.id}`);
      const shown = built.get(area.id) ?? build(area);
      for (const [id, made] of built) made.element.hidden = id !== area.id;
      for (const [id, { tab }] of tabs) {
        if (id === area.id) tab.setAttribute("aria-current", "page");
        else tab.removeAttribute("aria-current");
      }
      if (current !== area.id) replay(shown.element, "wb-in");
      if (current !== null && current !== area.id) strip.scrollIntoView({ block: "nearest" });
      current = area.id;
      shown.show(route.slice(1));
    },
  };
}
