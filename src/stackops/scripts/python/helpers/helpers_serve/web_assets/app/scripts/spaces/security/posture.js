import { h, icon } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { createLivePanel } from "../../live_panel.js";
import { button, notice, searchInput } from "../../widgets.js";
import { plural, relativeTime } from "../../words.js";
import { targetGroups } from "./app_rows.js";
import { openTargetSheet } from "./app_sheet.js";
import { postureRing } from "./posture_ring.js";
import { groupOf, needsScan, RUN_STATES, SCAN_COMMAND, SCANS_HASH } from "./words.js";

const REFRESH_MILLISECONDS = 10000;
const FILTERS = [
  ["all", "Everything", () => true],
  ["attention", "Flagged", (app) => ["flagged", "review"].includes(groupOf(app))],
  ["scan", "To scan", needsScan],
  ["clean", "Clean", (app) => groupOf(app) === "clean"],
];

function headline(apps, flagged, review, toScan) {
  const checked = apps.filter((app) => app.verdict !== "unchecked").length;
  if (flagged > 0) return ["bad", `${plural(flagged, "app")} flagged`, "More than a few antivirus engines report a problem. Open each one to see which engines, and what they found."];
  if (review > 0) return ["warn", `${plural(review, "app")} worth a look`, "Only one or two engines flagged them, which is often a false alarm. Open each one to see what was found."];
  if (checked === 0) return ["", "Nothing has been checked yet", "A scan asks VirusTotal's antivirus engines about every app installed here, and keeps their answers."];
  if (toScan > 0) return ["", `Nothing flagged, ${plural(toScan, "app")} left to scan`, "Those were never checked, were changed after their check, or could not be checked."];
  return ["good", "Everything is clean", `All ${plural(apps.length, "installed app")} passed their latest check.`];
}

// Security › This machine: every installed app with the latest answer VirusTotal gave about it, worst first.
export function createPostureSection({ activity, starter }) {
  let filter = "all";
  let term = "";
  let settled = false;

  const open = (target) =>
    openTargetSheet({
      target, onScan: (app) => starter.apps([app.name]),
      loadEngines: async () => (await query(["devops", "security", "report", "--run", target.run_id, "--json", target.name])).json.engines.filter((engine) => engine.target_id === target.target_id),
    });

  const groupAction = (id, members) =>
    ["changed", "unknown", "unchecked"].includes(id) && members.length > 1 && button({ label: `Scan these ${members.length}`, glyph: "shield", small: true, onclick: () => starter.apps(members.map((app) => app.name)) });

  function render(data, { setCount }) {
    const { apps, accounts, latest_run: latest } = data;
    if (apps.length === 0) return notice({ glyph: "shield", title: "No installed apps were found", body: "Apps that StackOps installs are listed here, each with what VirusTotal makes of it." });
    const count = (id) => apps.filter((app) => groupOf(app) === id).length;
    const [flagged, review, clean] = [count("flagged"), count("review"), count("clean")];
    const toScan = apps.filter(needsScan).length;
    const [tone, title, body] = headline(apps, flagged, review, toScan);
    setCount(`${plural(apps.length, "installed app")} · ${apps.length - count("unchecked")} checked`);
    const [runState, runTone] = latest ? RUN_STATES[latest.status] : [];
    const list = h("div", { class: "scan-groups" });
    const chips = FILTERS.map(([id, label, accepts]) =>
      h(
        "button",
        {
          class: "chip-button", type: "button", "aria-pressed": String(id === filter),
          onclick: () => {
            filter = id;
            for (const chip of chips) chip.setAttribute("aria-pressed", String(chip.dataset.id === id));
            paint();
          },
          "data-id": id,
        },
        h("span", { text: label }),
        h("b", { text: String(apps.filter(accepts).length) }),
      ),
    );
    const search = searchInput({
      placeholder: "Filter apps",
      oninput: (value) => {
        term = value.trim().toLowerCase();
        paint();
      },
    });
    search.input.value = term;

    function paint() {
      const accepts = FILTERS.find(([id]) => id === filter)[2];
      const found = apps.filter((app) => accepts(app) && `${app.name} ${app.path}`.toLowerCase().includes(term));
      list.replaceChildren(
        ...(found.length ? targetGroups(found, { onOpen: open, onScan: (app) => starter.apps([app.name]), groupAction, settled, unfolded: filter !== "all" || term !== "" }) : [notice({ glyph: "search", title: "Nothing here", body: term ? "No app matches that. Try another word." : "No app is in this group right now." })]),
      );
    }
    paint();
    return h(
      "div",
      { class: "stack" },
      h(
        "div",
        { class: `posture ${tone}` },
        postureRing({ clean, review, flagged, total: apps.length, tone }),
        h(
          "div",
          { class: "posture-text" },
          h("h3", { text: title }),
          h("p", { text: body }),
          h(
            "div",
            { class: "project-facts" },
            accounts.problem ? h("span", { class: "pill warn", text: "Scans cannot run yet" }) : h("span", { class: "fact" }, icon("check", 13), `${plural(accounts.count, "VirusTotal account")} ready`),
            latest ? h("a", { class: "fact posture-last", href: `${SCANS_HASH}/${latest.run_id}`, title: "Open the latest scan" }, icon("clock", 13), `Last scan ${relativeTime(latest.started_at)}`, h("span", { class: `pill ${runTone}`, text: runState })) : h("span", { class: "fact" }, icon("clock", 13), "No scan has run yet"),
          ),
          accounts.problem && h("p", { class: "dim", text: `${accounts.problem} ${starter.keyEntry}` }),
        ),
        h(
          "div",
          { class: "posture-actions" },
          accounts.problem
            ? button({ label: "Add a VirusTotal key", glyph: "lock", tone: "primary", onclick: starter.addKey })
            : toScan > 0 && toScan < apps.length && button({ label: `Scan the ${toScan} that need it`, glyph: "shield", tone: "primary", onclick: () => starter.apps(apps.filter(needsScan).map((app) => app.name)) }),
        ),
      ),
      h("div", { class: "scan-filter" }, h("div", { class: "chip-row" }, chips), search.element),
      list,
    );
  }

  const panel = createLivePanel({ title: "This machine", path: "devops security status", extra: ["--json"], tunable: false, render });

  // While a scan started from this app is going, its answers are saved one file at a time, so the list is read again as they come in.
  const scanning = () => activity.runs().some((run) => run.exit_code === null && SCAN_COMMAND.every((word, index) => run.arguments[index] === word));
  setInterval(async () => {
    if (!panel.element.isConnected || panel.element.closest("[hidden]") || !scanning()) return;
    settled = true;
    panel.element.classList.add("quiet");
    await panel.load(true);
    panel.element.classList.remove("quiet");
    settled = false;
  }, REFRESH_MILLISECONDS);

  return { element: h("div", { class: "security-section" }, panel.element), show: () => panel.ensure() };
}
