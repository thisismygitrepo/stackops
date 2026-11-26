import { h } from "/assets/scripts/dom.js";
import { agentButton } from "../agent_ask.js";
import { PLACES } from "../agent_places.js";
import { createDiskCleanup } from "../disk_cleanup.js";
import { CLEANUP_HASH } from "../disk_cleanup_words.js";
import { partLoaders } from "../features.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { createParts, linkCard, toolButton, toolGrid, viewHead } from "../space_kit.js";
import { button, glyphTile, notice, sectionHead } from "../widgets.js";
import { createStatusPanel } from "./machine/status.js";

// Each opens a page of its own (features.js). What starts automatically is one of them and not a list on this page: it runs to dozens of rows.
const CARE_TOOLS = ["utils machine kill-process", "utils machine autostart", "utils machine list-devices", "utils machine mount", "utils machine window", "utils machine environment", "devops self update"];

// Views that swap in place: the overview at #/machine, the disk cleanup at #/machine/cleanup, and the ones features.js lists for this page.
export function createMachineSpace(context) {
  const { activity, tools } = context;
  const fact = (label, value, glyph, hue) => h("article", { class: "spec-card lit" }, glyphTile(glyph, hue, 38), h("span", { class: "stat-label", text: label }), h("strong", { text: value || "—" }));

  const specs = createLivePanel({
    title: "About this machine", path: "utils machine specs", extra: ["--json"], skeletonShape: "card", tunable: false,
    render: (data, { setCount }) => {
      if (!data?.system) return notice({ glyph: "cpu", title: "No details", body: "This machine did not describe itself." });
      setCount(data.hostname ?? "");
      return rise(
        h(
          "div",
          { class: "spec-grid" },
          fact("Name", data.hostname, "cpu", 252),
          fact("System", data.distro || data.system, "layers", 200),
          fact("Processor", [data.machine, data.processor].filter(Boolean).join(" · "), "bolt", 30),
          fact("Signed in as", data.user, "bot", 150),
          fact("Python", data.python_version, "code", 290),
          fact("Home folder", data.home_dir, "folder", 330),
        ),
      );
    },
  });

  const status = createStatusPanel();
  const careGrid = toolGrid(tools, CARE_TOOLS);
  careGrid.prepend(linkCard({ href: CLEANUP_HASH, emoji: "🧹", name: "utils machine clean-drive", title: "Free up disk space", blurb: "See what is taking up room, choose what goes, and clean it." }));
  const overview = h(
    "div",
    {},
    viewHead({
      title: "Machine", lede: "What this computer is, what runs on it, and how to keep it tidy.",
      actions: [agentButton(activity, PLACES.machine), toolButton(tools, "utils machine kill-process", { label: "Stop a process", glyph: "stop" }), button({ label: "Free up disk space", glyph: "trash", tone: "primary", onclick: () => (location.hash = CLEANUP_HASH) })],
    }),
    specs.element,
    status.element,
    h("section", { class: "block" }, sectionHead("Look after it"), careGrid),
  );
  const cleanup = createDiskCleanup(context);
  const element = h("section", { class: "view", hidden: true }, overview, cleanup.element);
  return { element, show: createParts({ element, built: { "": { element: overview, show: () => [specs, status].forEach((panel) => panel.ensure()) }, cleanup }, loaders: partLoaders("machine"), context }) };
}
