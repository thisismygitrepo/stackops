import { h } from "/assets/scripts/dom.js";
import { replay } from "../../motion.js";
import { glyphTile } from "../../widgets.js";
import { createBrainArea } from "./workbench_brain.js";
import { createBrowserArea } from "./workbench_browser.js";
import { createComputerArea } from "./workbench_computer.js";
import { createLocalArea } from "./workbench_local.js";
import { createLoopsArea } from "./workbench_loops.js";
import { createSetupArea } from "./workbench_setup.js";

const AREAS = [
  { id: "browser", label: "Browser automation", caption: "A browser for agents", glyph: "browser", hue: 205, create: createBrowserArea },
  { id: "desktop", label: "Desktop control", caption: "Use of this computer", glyph: "monitor", hue: 262, create: createComputerArea },
  { id: "models", label: "Local models", caption: "AI on this machine", glyph: "server", hue: 160, create: createLocalArea },
  { id: "second-brain", label: "Second Brain", caption: "Ask and remember", glyph: "book", hue: 330, create: createBrainArea },
  { id: "loops", label: "Loops", caption: "Agents working in rounds", glyph: "lanes", hue: 32, create: createLoopsArea },
  { id: "setup", label: "Setup and cleanup", caption: "Prepare, start fresh", glyph: "wrench", hue: 290, create: createSetupArea },
];

// `askFor(id)` makes the "Ask an agent" button of one area, which the area puts in its heading.
// The strip of areas stays on the Agents page whichever section is open. Each area is built and loaded the first time it is shown. The address is #/agents/<area>.
export function createWorkbench(context, askFor) {
  const built = new Map();
  const tabs = new Map(
    AREAS.map((area) => {
      const status = h("span", { class: "wb-tab-status", text: area.caption });
      const tab = h("a", { class: "wb-tab", href: `#/agents/${area.id}` }, glyphTile(area.glyph, area.hue, 32), h("span", { class: "wb-tab-text" }, h("strong", { text: area.label }), status));
      return [area.id, { tab, status }];
    }),
  );
  const strip = h("nav", { class: "wb-tabs", "aria-label": "More for your agents" }, [...tabs.values()].map(({ tab }) => tab));
  const element = h("div", { class: "agents-section workbench", hidden: true });
  let current = null;

  function build(area) {
    const { status } = tabs.get(area.id);
    const setStatus = (text, tone = "") => {
      status.textContent = text;
      status.dataset.tone = tone || "quiet";
    };
    // `failStatus` is for the panel an area takes its status from: when that panel does not load, the strip says so instead of keeping the last good status.
    const made = area.create(context, { setStatus, failStatus: () => setStatus("Couldn't check", "warn"), ask: askFor(area.id) });
    built.set(area.id, made);
    element.append(made.element);
    return made;
  }

  return {
    strip,
    element,
    // Shows the area the address names, and says whether it named one.
    show(route) {
      const area = AREAS.find((candidate) => candidate.id === route[0]);
      element.hidden = !area;
      for (const [id, { tab }] of tabs) {
        if (id === area?.id) tab.setAttribute("aria-current", "page");
        else tab.removeAttribute("aria-current");
      }
      if (!area) {
        current = null;
        return false;
      }
      const shown = built.get(area.id) ?? build(area);
      for (const [id, made] of built) made.element.hidden = id !== area.id;
      if (current !== area.id) replay(shown.element, "wb-in");
      if (current !== null && current !== area.id) strip.scrollIntoView({ block: "nearest" });
      current = area.id;
      shown.show(route.slice(1));
      return true;
    },
  };
}
