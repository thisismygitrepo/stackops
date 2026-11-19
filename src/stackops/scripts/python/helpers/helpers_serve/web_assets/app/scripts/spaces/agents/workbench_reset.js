import { h, icon } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { rise } from "../../motion.js";
import { dataTable } from "../../result_view.js";
import { button, notice, segmented, stat } from "../../widgets.js";
import { plural } from "../../words.js";
import { barList, createStatePanel, tally } from "./workbench_kit.js";

const SCOPES = [["all", "Everywhere"], ["workspace", "This project"], ["user", "Your account"]];
const KINDS = { skill: "Skills", instructions: "Instruction files", configuration: "Settings", plugin: "Plugins", mcp: "Tool servers", workspace: "Project scratch folders" };
const HOMES = { global: "Your account", local: "This project", system: "Built into the agent" };
const BAR_LIMIT = 7;

// Built only when opened: the full list can run to hundreds of rows.
function fold(title, size, build) {
  const details = h("details", { class: "fold" }, h("summary", {}, icon("chevron", 13), h("span", { text: title }), h("b", { text: String(size) })));
  details.addEventListener("toggle", () => details.append(build()), { once: true });
  return details;
}

// The plan is read with the preview-only form of the command. Applying a reset is only ever reachable through the tool sheet.
export function createResetPanel({ tools, openReport }) {
  let scope = "all";
  const picker = segmented(SCOPES, (value) => {
    scope = value;
    picker.set(scope);
    panel.reload();
  });

  const panel = createStatePanel({
    title: "If you reset your agents", actions: [picker.element], skeletonShape: "card",
    load: async (fresh) => (await query(["agents", "reset", "--scope", scope, "--json"], fresh)).json,
    render: (data, { setCount }) => {
      const entries = data?.plan?.entries ?? [];
      const changes = data?.plan?.changes ?? [];
      const skipped = data?.plan?.blockers ?? [];
      setCount(entries.length ? "a preview — nothing is changed" : "");
      if (entries.length === 0) return notice({ glyph: "check", tone: "good", title: "Already a clean slate", body: "Nothing has been added to your agents here, so there is nothing a reset would remove." });
      const agents = tally(entries, (entry) => entry.agent);
      const deleted = changes.filter((change) => change.action === "remove").length;
      const tiles = [
        [stat({ glyph: "sparkle", hue: 262, label: "Additions found" }), entries.length, `across ${plural(agents.length, "agent")}`],
        [stat({ glyph: "trash", hue: 350, label: "Files a reset would touch" }), changes.length, `${deleted} deleted · ${changes.length - deleted} edited`],
        [stat({ glyph: "shield", hue: 160, label: "Left alone" }), skipped.length, "managed elsewhere, so a reset skips them"],
      ];
      requestAnimationFrame(() => tiles.forEach(([tile, value, note]) => tile.set(value, note)));
      const rows = () => entries.map((entry) => ({ agent: entry.agent, kind: KINDS[entry.event] ?? `Hook · ${entry.event}`, name: entry.name, where: HOMES[entry.origin] ?? entry.origin, state: entry.state, file: entry.path }));
      // The report form of the command ends with a failure whenever something is left alone, so the report is only offered when it can open.
      const report = skipped.length === 0 && button({ label: "Open as a report", glyph: "report", small: true, onclick: () => openReport({ title: "Agent cleanup preview", blurb: "What a reset would remove. Nothing is changed.", arguments: ["agents", "reset", "--scope", scope, "--as-html"] }) });
      return h(
        "div",
        { class: "stack" },
        rise(h("div", { class: "stats" }, tiles.map(([tile]) => tile.element))),
        h(
          "div",
          { class: "wb-split even" },
          h("div", {}, h("span", { class: "stat-label", text: "What they are" }), barList(tally(entries, (entry) => KINDS[entry.event] ?? "Hooks").slice(0, BAR_LIMIT))),
          h("div", {}, h("span", { class: "stat-label", text: "Which agents have them" }), barList(agents.slice(0, BAR_LIMIT))),
        ),
        fold("Everything a reset would remove", entries.length, () => dataTable(rows())),
        skipped.length > 0 && fold("Left alone", skipped.length, () => h("ul", { class: "wb-skipped" }, skipped.map((reason) => h("li", { text: reason })))),
        h(
          "div",
          { class: "wb-line" },
          h("span", { class: "dim", text: "A reset is permanent and keeps no backup." }),
          h("span", { class: "wb-line-actions" }, report, button({ label: "Reset…", glyph: "trash", small: true, onclick: () => tools.open("agents reset", { preset: { scope } }) })),
        ),
      );
    },
  });
  picker.set(scope);
  return panel;
}
