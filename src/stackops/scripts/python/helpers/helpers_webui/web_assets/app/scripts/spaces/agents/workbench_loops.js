import { h } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { createPanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { avatar, button, notice } from "../../widgets.js";
import { humanize, plural } from "../../words.js";
import { actionBlock, areaHead, cardHead, installButton, pathText, statusPill } from "./workbench_kit.js";

const PREVIEW_ALL = { all_workspaces: "on", dry_run: "on" };
const MOODS = { working: ["Working", "accent", "bolt"], idle: ["Idle", "", null], done: ["Finished", "good", "check"], blocked: ["Waiting on you", "warn", "alert"] };
const TIDY = [
  { path: "agents iter close", blurb: "Close tabs from rounds that have already handed over. You see the plan first.", preset: PREVIEW_ALL },
  { path: "agents iter clean", blurb: "Remove records left behind by loops that are gone. You see the list first.", preset: PREVIEW_ALL, caution: "Deletes records" },
  { path: "agents iter status", title: "Inspect every loop", blurb: "Each loop with its tabs, and which of them are safe to close.", preset: { all_workspaces: "on" } },
];

export function createLoopsArea({ tools }, { setStatus, failStatus }) {
  const clearButton = (count) => button({ label: `Clear ${plural(count, "old record")}`, glyph: "trash", small: true, onclick: () => tools.open("agents iter clean", { preset: PREVIEW_ALL }) });

  function loopCard(loop) {
    const { workspace, plan } = loop;
    const mood = statusPill(...(MOODS[workspace.agent_status] ?? [humanize(workspace.agent_status), "", null]));
    const agent = loop.latest_agent;
    const closable = plan.closable_tabs.length;
    return h(
      "article",
      { class: "wb-card lit" },
      cardHead(avatar(workspace.label, 44), workspace.label, loop.latest_iteration === null ? "No round yet" : `Round ${loop.latest_iteration}`, mood),
      agent && h("p", { class: "wb-note", text: `${agent.display_agent ?? agent.agent ?? "An agent"} has the current round${loop.latest_agent_tab ? `, in the tab “${loop.latest_agent_tab.label}”` : ""}.` }),
      h("span", { class: "stat-label", text: `${plural(plan.tabs.length, "tab")} · ${closable} finished and safe to close · ${plan.retained_tabs.length + plan.protected_tabs.length} kept` }),
      h(
        "footer",
        {},
        agent?.cwd ? pathText(agent.cwd) : h("span"),
        closable > 0 && button({ label: "Close finished tabs", glyph: "stop", small: true, onclick: () => tools.open("agents iter close", { preset: { workspace_id: workspace.workspace_id, dry_run: "on" } }) }),
      ),
    );
  }

  const loops = createPanel({
    title: "Loops in progress", skeletonShape: "card", onFail: failStatus,
    load: async (fresh) => {
      const [status, leftovers] = await Promise.allSettled([
        query(["agents", "iter", "status", "--all", "--json"], fresh),
        query(["agents", "iter", "clean", "--all", "--dry-run", "--json"], fresh),
      ]);
      if (status.status === "rejected") throw status.reason;
      return { loops: Array.isArray(status.value.json) ? status.value.json : [], leftovers: leftovers.status === "fulfilled" ? (leftovers.value.json?.removed_runs?.length ?? 0) : 0 };
    },
    explain: (error) => {
      if (!/herdr/i.test(error.message) || !/not found/i.test(error.message)) return null;
      setStatus("Loops need Herdr", "");
      return notice({
        glyph: "lanes", title: "Loops need Herdr", body: "A loop runs inside Herdr, a workspace that keeps each round of an agent's work in its own tab. Install it to use loops.",
        action: installButton(tools, "herdr", "Install Herdr"),
      });
    },
    render: (data, { setCount }) => {
      const closable = data.loops.reduce((total, loop) => total + loop.plan.closable_tabs.length, 0);
      setCount(data.loops.length ? `${plural(data.loops.length, "loop")} · ${plural(closable, "tab")} ready to close` : "");
      setStatus(data.loops.length ? `${plural(data.loops.length, "loop")} running` : "Nothing running", data.loops.length ? "good" : "");
      if (data.loops.length === 0) {
        return notice({
          glyph: "lanes", title: "No loops are running",
          body: `A loop is an agent working toward a goal in rounds, handing over to a fresh agent each time. ${data.leftovers ? "Earlier loops left some records behind in this project." : "Running ones show up here."}`,
          action: data.leftovers > 0 && clearButton(data.leftovers),
        });
      }
      return h("div", { class: "stack" }, rise(h("div", { class: "card-grid wide" }, data.loops.map(loopCard))), data.leftovers > 0 && h("div", { class: "wb-line" }, h("span", { class: "dim", text: "Earlier loops left records behind in this project." }), clearButton(data.leftovers)));
    },
  });

  const element = h("div", { class: "wb-area" }, areaHead({ title: "Loops", lede: "Let agents work in rounds until a goal is met." }), loops.element, actionBlock(tools, "Tidy up loops", TIDY));
  return {
    element,
    show() {
      loops.ensure();
    },
  };
}
