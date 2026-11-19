import { h } from "/assets/scripts/dom.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { dataTable } from "../result_view.js";
import { createView, toolButton, toolGrid } from "../space_kit.js";
import { glyphTile, notice, sectionHead } from "../widgets.js";
import { plural } from "../words.js";

const CARE_TOOLS = ["utils machine clean-drive", "utils machine kill-process", "utils machine list-devices", "utils machine mount", "utils machine window", "devops self update"];

export function createMachineSpace({ tools }) {
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

  const element = createView(
    {
      title: "Machine", lede: "What this computer is, what runs on it, and how to keep it tidy.",
      actions: [
        toolButton(tools, "utils machine kill-process", { label: "Stop a process", glyph: "stop" }),
        toolButton(tools, "utils machine clean-drive", { label: "Free up disk space", glyph: "trash", tone: "primary", preset: { dry_run: "on" } }),
      ],
    },
    specs.element,
    h("section", { class: "block" }, sectionHead("Look after it"), toolGrid(tools, CARE_TOOLS)),
    startup.element,
  );
  return {
    element,
    show() {
      specs.ensure();
      startup.ensure();
    },
  };
}
