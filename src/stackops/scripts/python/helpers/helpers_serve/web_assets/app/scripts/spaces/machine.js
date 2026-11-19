import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createDiskCleanup } from "../disk_cleanup.js";
import { CLEANUP_HASH } from "../disk_cleanup_words.js";
import { createLivePanel } from "../live_panel.js";
import { replay, rise } from "../motion.js";
import { dataTable } from "../result_view.js";
import { toolButton, toolCard } from "../space_kit.js";
import { button, emojiTile, glyphTile, notice, sectionHead } from "../widgets.js";
import { plural } from "../words.js";

const CARE_TOOLS = ["utils machine kill-process", "utils machine list-devices", "utils machine mount", "utils machine window", "devops self update"];

// Two views that swap in place: the overview at #/machine and the disk cleanup at #/machine/cleanup.
export function createMachineSpace(context) {
  const { tools } = context;
  const fact = (label, value, glyph, hue) => h("article", { class: "spec-card lit" }, glyphTile(glyph, hue, 38), h("span", { class: "stat-label", text: label }), h("strong", { text: value || "—" }));

  const specs = createLivePanel({
    title: "About this machine", path: "utils machine specs", extra: ["--json"], skeletonShape: "card",
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

  const startup = createLivePanel({
    title: "Starts automatically", path: "utils machine autostart", extra: ["--json"],
    render: (data, { setCount }) => {
      const items = Array.isArray(data) ? data : [];
      setCount(items.length ? plural(items.length, "program") : "");
      if (items.length === 0) return notice({ glyph: "bolt", title: "Nothing starts on its own", body: "No services or programs are set to start automatically." });
      return dataTable(items.map((item) => ({ name: item.name, what_it_does: item.description, category: item.category, scope: item.scope, source: item.source, built_in: item.stock })));
    },
  });

  const cleanupCard = h(
    "a",
    { class: "tool-card lit", href: CLEANUP_HASH },
    emojiTile("🧹", "utils machine clean-drive", 40),
    h("span", { class: "tool-card-text" }, h("strong", { text: "Free up disk space" }), h("span", { text: "See what is taking up room, choose what goes, and clean it." })),
    icon("arrow", 14),
  );
  const overview = h(
    "div",
    { class: "machine-part" },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("h1", { text: "Machine" }), h("p", { text: "What this computer is, what runs on it, and how to keep it tidy." })),
      h("div", { class: "view-actions" }, toolButton(tools, "utils machine kill-process", { label: "Stop a process", glyph: "stop" }), button({ label: "Free up disk space", glyph: "trash", tone: "primary", onclick: () => (location.hash = CLEANUP_HASH) })),
    ),
    specs.element,
    h("section", { class: "block" }, sectionHead("Look after it"), h("div", { class: "tool-grid" }, cleanupCard, CARE_TOOLS.filter((path) => state.nodes.has(path)).map((path) => toolCard(tools, state.nodes.get(path))))),
    startup.element,
  );
  const cleanup = createDiskCleanup(context);
  cleanup.element.classList.add("machine-part");
  const element = h("section", { class: "view", hidden: true }, overview, cleanup.element);
  let shown = null;

  return {
    element,
    show(route) {
      const part = route[0] === "cleanup" ? cleanup.element : overview;
      overview.hidden = part !== overview;
      cleanup.element.hidden = part !== cleanup.element;
      if (shown && shown !== part) {
        replay(part, "swap");
        element.closest(".stage")?.scrollTo(0, 0);
      }
      shown = part;
      if (part === overview) {
        specs.ensure();
        startup.ensure();
      } else cleanup.show();
    },
  };
}
