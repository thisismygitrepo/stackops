import { h, icon } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { dataTable } from "../../result_view.js";
import { button, notice, segmented } from "../../widgets.js";
import { plural } from "../../words.js";
import { barList, createStatePanel, stateCard, statRow, tally } from "./workbench_kit.js";

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
  // A design choice: a scope looked at before is shown from memory, so it can be older than the files. The refresh button asks again.
  const picker = segmented(SCOPES, (value) => {
    scope = value;
    picker.set(scope);
    panel.load();
  });

  const panel = createStatePanel({
    title: "If you reset your agents", actions: [picker.element], skeletonShape: "card",
    load: async (fresh) => (await query(["agents", "reset", "--scope", scope, "--json"], fresh)).json,
    render: (data, { setCount }) => {
      const entries = data?.plan?.entries ?? [];
      const changes = data?.plan?.changes ?? [];
      const blockers = data?.plan?.blockers ?? [];
      const blocked = blockers.length > 0;
      setCount(blocked ? "a preview — blocked as it stands" : entries.length ? "a preview — nothing is changed" : "");
      if (entries.length === 0 && !blocked) return notice({ glyph: "check", tone: "good", title: "Already a clean slate", body: "Nothing has been added to your agents here, so there is nothing a reset would remove." });
      const agents = tally(entries, (entry) => entry.agent);
      const deleted = changes.filter((change) => change.action === "remove").length;
      const tiles = [
        { glyph: "sparkle", hue: 262, label: "Additions found", value: entries.length, note: `across ${plural(agents.length, "agent")}` },
        { glyph: "trash", hue: 350, label: "Files a reset would touch", value: changes.length, note: `${deleted} deleted · ${changes.length - deleted} edited` },
        { glyph: blocked ? "alert" : "shield", hue: blocked ? 32 : 160, label: "In the way", value: blockers.length, note: blocked ? "a reset stops while these are in scope" : "nothing stops a reset" },
      ];
      const rows = () => entries.map((entry) => ({ agent: entry.agent, kind: KINDS[entry.event] ?? `Hook · ${entry.event}`, name: entry.name, where: HOMES[entry.origin] ?? entry.origin, state: entry.state, file: entry.path }));
      // The two buttons act on the scope this plan was read for, not on one picked since whose plan is still loading.
      const shown = scope;
      const place = SCOPES.find(([value]) => value === shown)[1].toLowerCase();
      // "Everywhere" is the command's default and is asked for without --scope, so it opens the Reports page's own cleanup preview and adds no twin of it.
      const report = button({
        label: "Open as a report", glyph: "report", small: true,
        onclick: () => openReport({ title: `Agent cleanup preview: ${place}`, blurb: "What a reset would remove. Nothing is changed.", arguments: ["agents", "reset", ...(shown === "all" ? [] : ["--scope", shown]), "--as-html"] }),
      });
      return h(
        "div",
        { class: "stack" },
        // A reset is all or nothing: the command refuses to run while anything in scope cannot be removed. It never skips those and carries on.
        blocked &&
          stateCard({
            tone: "warn", glyph: "alert", title: "A reset of this scope would be refused",
            body: `${plural(blockers.length, "item")} in scope ${blockers.length === 1 ? "is" : "are"} read-only, managed elsewhere or unreadable, and a reset is all or nothing. Narrow it so they fall outside: pick another scope above, or one agent, kind or name in the Reset form. They are listed below.`,
          }),
        statRow(tiles),
        h(
          "div",
          { class: "wb-split even" },
          h("div", {}, h("span", { class: "stat-label", text: "What they are" }), barList(tally(entries, (entry) => KINDS[entry.event] ?? "Hooks").slice(0, BAR_LIMIT))),
          h("div", {}, h("span", { class: "stat-label", text: "Which agents have them" }), barList(agents.slice(0, BAR_LIMIT))),
        ),
        fold(blocked ? "Everything in scope" : "Everything a reset would remove", entries.length, () => dataTable(rows())),
        blocked && fold("What is in the way", blockers.length, () => h("ul", { class: "wb-skipped" }, blockers.map((reason) => h("li", { text: reason })))),
        h(
          "div",
          { class: "wb-line" },
          h("span", { class: "dim", text: blocked ? "As it stands, a reset would stop without changing anything." : "A reset is permanent and keeps no backup." }),
          h("span", { class: "wb-line-actions" }, report, button({ label: "Reset…", glyph: "trash", small: true, onclick: () => tools.open("agents reset", { preset: { scope: shown } }) })),
        ),
      );
    },
  });
  picker.set(scope);
  return panel;
}
