import { h, icon } from "/assets/scripts/dom.js";
import { query, staleKeeper } from "../../data.js";
import { createLivePanel } from "../../live_panel.js";
import { replay, rise } from "../../motion.js";
import { dataTable } from "../../result_view.js";
import { toolButton } from "../../space_kit.js";
import { button, copyChip, glyphTile, notice, pill, sectionHead, skeleton, stat } from "../../widgets.js";
import { plural } from "../../words.js";
import { targetGroups } from "./app_rows.js";
import { openTargetSheet } from "./app_sheet.js";
import { countsLine, RUN_STATES, runTiming, SCANS_HASH, scopeTitle } from "./words.js";

const SCOPE_GLYPHS = { all: "shield", apps: "apps", path: "report" };
const STATE_HUES = { good: 155, warn: 35, bad: 345, accent: 252, "": 220 };
const ACCOUNT_NUMBERS = ["requests", "success", "expected", "failed", "in_flight", "retries", "failovers"];
// The history command's own default for Limit, which holds until one is set under Options. Written here, not read from the CLI: if that default
// ever moves, a full list reads as a plain count again, as it did before.
const HISTORY_LIMIT = 20;

// Security › Scans: every saved scan, newest first at #/security/scans, and one of them opened in its place at #/security/scans/<run>.
export function createScansSection({ tools, starter }) {
  const runRow = (run) => {
    const [label, tone] = RUN_STATES[run.status];
    return h(
      "li",
      {},
      h(
        "a",
        { class: "session-row scan-run", href: `${SCANS_HASH}/${run.run_id}`, title: "Open this scan" },
        glyphTile(SCOPE_GLYPHS[run.scope], STATE_HUES[tone], 40),
        h("div", { class: "session-text" }, h("strong", { text: scopeTitle(run) }), h("span", { class: "dim", text: runTiming(run) })),
        h("span", { class: "dim scan-counts", text: `${plural(run.targets, "file")} · ${countsLine(run.counts)}` }),
        pill(label, tone),
        h("span", { class: "scan-go" }, icon("chevron", 14)),
      ),
    );
  };

  const history = createLivePanel({
    title: "Scan history", path: "devops security history", extra: ["--json"], locked: ["format_type", "records_dir"],
    render: (runs, { setCount, options }) => {
      // A list as long as the limit in force may not be all of them, so it does not pass for a count.
      const full = runs.length === Number(options.get("limit") ?? HISTORY_LIMIT);
      setCount(runs.length === 0 ? "" : full ? `the latest ${plural(runs.length, "scan")}` : plural(runs.length, "scan"));
      if (runs.length === 0) return notice({ glyph: "clock", title: "No scans yet", body: "Every scan is kept here with what it found, so you can come back to it.", action: button({ label: "Scan every app", glyph: "shield", tone: "primary", onclick: starter.everything }) });
      return rise(h("ul", { class: "session-list" }, runs.map(runRow)));
    },
  });

  const opened = h("div", { class: "scan-opened", hidden: true });
  const back = () => h("a", { class: "btn small", href: SCANS_HASH }, icon("back", 14), h("span", { text: "All scans" }));
  let shownId = null;

  function runView({ run, targets, engines, accounts }) {
    const [label, tone] = RUN_STATES[run.status];
    const counts = run.counts;
    const flagged = (counts.flagged ?? 0) + (counts.review ?? 0);
    const unanswered = run.targets - (counts.clean ?? 0) - flagged;
    const tiles = [
      [stat({ glyph: "report", hue: 252, label: "Files in this scan" }), run.targets, run.scope === "all" ? "every installed app" : run.scope === "path" ? "one file" : "the apps that were picked"],
      [stat({ glyph: "check", hue: 155, label: "Clean" }), counts.clean ?? 0, "no engine flagged them"],
      [stat({ glyph: "alert", hue: 345, label: "Flagged" }), flagged, flagged ? "by at least one engine" : "nothing was flagged"],
      [stat({ glyph: "info", hue: 35, label: "Without an answer" }), unanswered, unanswered ? "failed, or never reached" : "every file got one"],
    ];
    requestAnimationFrame(() => tiles.forEach(([tile, value, note]) => tile.set(value, note)));
    const again = { all: starter.everything, apps: () => starter.apps(run.requested), path: () => starter.path(run.requested[0]) }[run.scope];
    const open = (target) =>
      openTargetSheet({ target, loadEngines: async () => engines.filter((engine) => engine.target_id === target.target_id), onScan: run.scope !== "path" && ((app) => starter.apps([app.name])) });
    return h(
      "div",
      { class: "stack" },
      h(
        "header",
        { class: "scan-head" },
        back(),
        h("div", { class: "scan-title" }, h("h2", { text: scopeTitle(run) }), pill(label, tone)),
        h("span", { class: "spacer" }),
        targets.some((target) => target.app_url) && toolButton(tools, "devops security install", { label: "Install its clean apps", glyph: "download", preset: { run: run.run_id, all_apps: "on" } }),
        toolButton(tools, "devops security export", { label: "Export", glyph: "up", preset: { run: run.run_id } }),
        button({ label: "Scan these again", glyph: "shield", tone: "primary", onclick: again }),
      ),
      h(
        "div",
        { class: "project-facts" },
        h("span", { class: "fact", title: new Date(run.started_at).toLocaleString() }, icon("clock", 13), runTiming(run)),
        h("span", { class: "fact" }, icon("cpu", 13), run.hostname),
        copyChip(run.run_id, `Scan ${run.run_id.slice(0, 16)}`),
      ),
      (run.message || run.status === "running") &&
        h("div", { class: "session-row" }, glyphTile("info", STATE_HUES[tone], 36), h("div", { class: "session-text" }, h("strong", { text: run.message ?? "No final status was recorded" }), run.status === "running" && h("span", { class: "dim", text: "The scan may still be going, or it was stopped abruptly." }))),
      rise(h("div", { class: "stats" }, tiles.map(([tile]) => tile.element))),
      h("div", { class: "scan-groups" }, targetGroups(targets, { onOpen: open, onScan: run.scope !== "path" && ((app) => starter.apps([app.name])), unfolded: true })),
      accounts.length > 0 &&
        h("section", { class: "block" }, sectionHead("VirusTotal requests"), dataTable(accounts.map((account) => ({ ...account, ...Object.fromEntries(ACCOUNT_NUMBERS.map((key) => [key, Number(account[key])])) })))),
    );
  }

  // With no `id` it reads the scan on show again, which is what the refresh signal asks for. No `fresh` then: the signal emptied the cache.
  async function openRun(id = shownId, fresh = false) {
    if (shownId !== id) opened.replaceChildren(back(), ...skeleton(4, "row"));
    shownId = id;
    try {
      const { json } = await query(["devops", "security", "report", "--run", id, "--json"], fresh);
      if (shownId === id) opened.replaceChildren(runView(json));
    } catch (error) {
      if (shownId !== id) return;
      keeper.spoil();
      opened.replaceChildren(back(), notice({ glyph: "alert", tone: "bad", title: "This scan didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => keeper.load(id, true) }) }));
    }
  }
  const keeper = staleKeeper(opened, openRun);

  const element = h("div", { class: "security-section" }, history.element, opened);
  return {
    element,
    show(route) {
      const id = route[0] ?? null;
      const part = id ? opened : history.element;
      if (part.hidden) replay(part, "scan-swap");
      history.element.hidden = id !== null;
      opened.hidden = id === null;
      if (id === null) {
        shownId = null;
        history.ensure();
      } else if (shownId !== id) keeper.load(id);
      else keeper.ensure();
    },
  };
}
