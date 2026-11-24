import { h, icon, toast } from "/assets/scripts/dom.js";
import { markStale } from "../../data.js";
import { confirmAction, openSheet } from "../../overlays.js";
import { avatar, button, notice, pill, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { createInstallPlan } from "./install_plan.js";
import { createRunPicker } from "./run_picker.js";
import { readInstallPlan, readRuns } from "./tools_api.js";
import { everyOption, part, shownPath, toolHead } from "./tools_kit.js";
import { outcomeCard, runCard, showRunWhenClosed, startWatched } from "./tools_run.js";

const PATH = "devops security install";
const TOKENS = PATH.split(" ");
const SCAN_PATH = "devops security scan";
const LEDE = "Put apps back from the copies a scan uploaded, once the scan found them clean.";
const FIT = {
  label: "With apps to install", accepts: (run) => run.installable > 0,
  note: (run) => (run.installable > 0 ? `${run.installable} to install` : "Nothing to install"),
  sort: ["Most to install", (first, second) => second.installable - first.installable],
};

const SAID_LIMIT = 200;

// What the installer said about each download that failed: the first sentence after the link it failed on. Several downloads print at once,
// so what follows that sentence may belong to another app.
function failuresIn(text) {
  const sentences = text.replace(/\s*\n\s*/g, " ").split("Failed to install app").slice(1);
  return sentences.map((sentence) => sentence.slice(sentence.indexOf(": ") + 2).split(/(?<=\.)\s/)[0].trim().slice(0, SAID_LIMIT)).filter(Boolean);
}

// Install from a scan, in a sheet over the scan it belongs to: the saved scans to choose from, what the chosen one would install and what it
// leaves alone and why, the apps to tick, then the install as a task this sheet watches, and what came of it for each app.
// `preset.run` is the scan to start with and `preset.name` the one app to tick.
export async function open(context, { preset = {} }) {
  const { activity, tools } = context;
  // The view reads the usual place for saved scans. A scan kept elsewhere is left to the command's own form.
  if (preset.records_dir) return tools.open(PATH, { preset, plain: true });
  const sheet = openSheet({ label: "Install from a scan", wide: true });
  const content = h("div", { class: "sec-tool" }, skeleton(4, "row"));
  const planHolder = h("div", { class: "sec-tool-holder" });
  const problem = h("span", { class: "tool-problem" });
  const goLabel = h("span", { text: "Install" });
  const go = h("button", { class: "btn primary", type: "button", disabled: true, onclick: () => install().catch((error) => toast(error.message)) }, icon("download", 16), goLabel);
  let running = null;
  let current = null;
  // Whether the plan is what the sheet shows. While a run or its result is in its place, the button that starts an install stays off.
  let planShown = false;
  let ticket = 0;
  const isOpen = showRunWhenClosed(sheet, () => running);
  const scanWithUpload = () => {
    sheet.close();
    tools.open(SCAN_PATH, { preset: { all_apps: "on", upload: "on" } });
  };
  const plan = createInstallPlan({ onChange: paintFoot, onScanWithUpload: scanWithUpload });

  function paintFoot() {
    const count = plan.picked().length;
    goLabel.textContent = count ? `Install ${plural(count, "app")}` : "Install";
    go.disabled = count === 0 || running !== null || !planShown;
  }

  async function loadPlan(runId) {
    const mine = (ticket += 1);
    current = null;
    planShown = false;
    paintFoot();
    planHolder.replaceChildren(...skeleton(4, "row"));
    try {
      const found = await readInstallPlan(runId);
      if (mine !== ticket) return;
      current = found;
      planShown = true;
      planHolder.replaceChildren(plan.element);
      plan.show(found, typeof preset.name === "string" ? preset.name : "");
    } catch (error) {
      if (mine !== ticket) return;
      planHolder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This scan didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => loadPlan(runId) }) }));
    }
  }

  function showOutcome(going, after, startedAt, said, stopped) {
    const landed = (entry) => after.rows.some((fresh) => fresh.file_name === entry.file_name && fresh.installed_at !== null && fresh.installed_at >= startedAt - 1);
    const done = going.filter(landed);
    const tone = done.length === going.length ? "good" : "bad";
    const failures = [...new Set(said.flatMap(failuresIn))];
    planHolder.replaceChildren(
      outcomeCard({
        tone, title: done.length === going.length ? `${plural(done.length, "app")} installed` : `${done.length} of ${plural(going.length, "app")} installed`,
        body: stopped ? "The install was stopped before it finished." : done.length === going.length ? `${done.length === 1 ? "It is" : "They are"} in ${shownPath(after.folder)}.` : `${done.length === 0 ? "None" : "The rest"} could not be installed. Nothing was put in place for them.`,
        extra: failures.length > 0 && h("ul", { class: "sec-outcome-said" }, failures.map((text) => h("li", { text }))),
        actions: [button({ label: "Back to the plan", glyph: "back", small: true, onclick: () => loadPlan(after.run.run_id) }), button({ label: "Done", small: true, tone: "primary", onclick: () => sheet.close() })],
      }),
      h("ul", { class: "sec-install-list" }, going.map((entry) => h("li", { class: "sec-install-row done" }, avatar(entry.name, 34), h("span", { class: "sec-install-text" }, h("strong", { text: entry.name }), h("span", { text: landed(entry) ? entry.destination : "Not installed" })), landed(entry) ? pill("Installed", "good") : pill("Not installed", "bad")))),
    );
  }

  async function install() {
    const going = plan.picked();
    const replaced = going.filter((entry) => entry.installed_at !== null).length;
    const swaps = replaced === 0 ? "" : replaced === 1 ? " One of them replaces a file that is there now." : ` ${replaced} of them replace a file that is there now.`;
    const sure = await confirmAction({
      title: `Install ${plural(going.length, "app")}?`, confirm: "Install",
      body: `Each one is downloaded from the copy this scan uploaded, checked against the fingerprint the scan recorded, and put in ${shownPath(current.folder)}.${swaps}`,
    });
    if (!sure || !isOpen()) return;
    const runId = current.run.run_id;
    // One run of the command takes one app or every app it finds fit. So every fit app chosen is one run, and anything less is a run per app.
    const whole = current.whole && going.length === plan.ready().length;
    const batches = whole ? [{ label: plural(going.length, "app"), runArguments: [...TOKENS, "--all", "--run", runId] }] : going.map((entry) => ({ label: entry.name, runArguments: [...TOKENS, "--run", runId, entry.name] }));
    let stopped = false;
    let startedAt = null;
    const said = [];
    planShown = false;
    const card = runCard({
      title: `Installing ${plural(going.length, "app")}`, onShow: () => sheet.close(),
      onStop() {
        stopped = true;
        running?.stop();
      },
    });
    planHolder.replaceChildren(card.element, h("ul", { class: "sec-install-list" }, going.map((entry) => h("li", { class: "sec-install-row done" }, avatar(entry.name, 34), h("span", { class: "sec-install-text" }, h("strong", { text: entry.name }), h("span", { text: entry.destination }))))));
    for (const [index, batch] of batches.entries()) {
      if (stopped) break;
      card.say(batches.length > 1 ? `${batch.label}, ${index + 1} of ${batches.length}` : "Downloading, checking and putting in place");
      running = await startWatched(activity, { title: `Install ${batch.label} from a scan`, emoji: "📦", arguments: batch.runArguments });
      paintFoot();
      startedAt ??= running.startedAt;
      const end = await running.ended;
      said.push(end.text);
      stopped ||= end.stopped;
      // The sheet went while this app was installing: its task is in the Activity panel now, and the apps after it are not started unseen.
      if (!isOpen()) {
        const left = batches.length - index - 1;
        if (left > 0) toast(`${plural(left, "app")} after ${batch.label} ${left === 1 ? "was" : "were"} not started. Open "Install from a scan" again for ${left === 1 ? "it" : "them"}.`, "info");
        break;
      }
    }
    running = null;
    card.end();
    // A run that stays out of the Activity panel does not tell the pages to read again, and the installed apps changed.
    markStale();
    if (!isOpen()) return;
    try {
      showOutcome(going, await readInstallPlan(runId), startedAt, said, stopped);
    } catch (error) {
      planHolder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The install ended, but its result could not be read", body: error.message }));
    }
    paintFoot();
  }

  sheet.body.append(toolHead(PATH, LEDE), content);
  sheet.foot.hidden = false;
  sheet.foot.append(everyOption({ tools, sheet, path: PATH, preset }), problem, go);
  let found;
  try {
    found = await readRuns();
  } catch (error) {
    content.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The saved scans didn't load", body: error.message }));
    return;
  }
  if (found.folder === "") {
    content.replaceChildren(notice({ glyph: "plug", title: "Installing from a scan is not available on this system", body: "StackOps knows where apps go on Linux, macOS and Windows only." }));
    return;
  }
  if (found.runs.length === 0) {
    content.replaceChildren(
      notice({
        glyph: "clock", title: "No scans yet", body: "Apps are installed from the cloud copies a scan keeps of the clean ones. Run a scan with uploading on, then come back here.",
        action: button({ label: "Scan with uploading on", glyph: "shield", tone: "primary", onclick: scanWithUpload }),
      }),
    );
    return;
  }
  const asked = found.runs.find((run) => run.run_id === preset.run);
  if (preset.run && !asked) problem.textContent = "The scan this was opened for is no longer saved, so another one is shown.";
  const first = asked ?? found.runs.find(FIT.accepts) ?? found.runs[0];
  content.replaceChildren(part("Scan", createRunPicker({ runs: found.runs, picked: first.run_id, fit: FIT, onPick: loadPlan }).element), part("What it would install", planHolder));
  await loadPlan(first.run_id);
}
