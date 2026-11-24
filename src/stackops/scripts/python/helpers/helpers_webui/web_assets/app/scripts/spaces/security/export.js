import { h, icon } from "/assets/scripts/dom.js";
import { openSheet } from "../../overlays.js";
import { button, notice, pathChip, skeleton } from "../../widgets.js";
import { formatBytes, plural } from "../../words.js";
import { createRunPicker } from "./run_picker.js";
import { createScanStarter } from "./scan_start.js";
import { checkExportPlace, exportRun, readExportPlan, readRuns } from "./tools_api.js";
import { everyOption, part, pathBox, shownPath, statusLine, toolHead } from "./tools_kit.js";
import { outcomeCard } from "./tools_run.js";
import { EXPORT_FILES } from "./tools_words.js";

const PATH = "devops security export";
const LEDE = "Save one scan as four files in a folder of its own, to open in a spreadsheet or to keep somewhere else.";
const FIT = {
  label: "Ran to the end", accepts: (run) => ["completed", "completed_with_errors"].includes(run.status), note: () => "",
  sort: ["Most files", (first, second) => second.targets - first.targets],
};
const PLACES = {
  exists: ["bad", () => "Something is already there. An export needs a folder of its own, so add the name of a new one."],
  blocked: ["bad", () => "A folder cannot be made there. Choose a place you can write in."],
  new: ["good", (place) => (place.creates > 1 ? `A new folder is made there, with the ${plural(place.creates - 1, "folder")} above it that ${place.creates === 2 ? "is" : "are"} missing.` : "A new folder is made there.")],
};

// The files an export writes, each with what it is, how many rows it holds and its share of the whole as a bar.
function fileRows(files) {
  const largest = Math.max(...files.map((file) => file.bytes), 1);
  return h(
    "ul",
    { class: "sec-export-files" },
    files.map((file) =>
      h(
        "li",
        {},
        h("span", { class: "sec-export-glyph" }, icon("report", 16)),
        h("span", { class: "sec-export-text" }, h("strong", { text: file.name }), h("span", { text: `${EXPORT_FILES[file.name]}${file.rows === null ? "" : ` · ${plural(file.rows, "row")}`}` })),
        h("span", { class: "sec-meter thin" }, h("i", { class: "go", style: `--share:${file.bytes / largest}` })),
        h("span", { class: "sec-export-size num", text: formatBytes(file.bytes) }),
      ),
    ),
  );
}

// Export a scan, in a sheet: the saved scans to choose from, the four files the folder will hold with their real sizes, the folder they go
// to with a check that it is a new one, then the export, which answers with what it wrote. `preset.run` is the scan to start with and
// `preset.output` a folder to offer.
export async function open(context, { preset = {} }) {
  const { tools } = context;
  // The view reads the usual place for saved scans. A scan kept elsewhere is left to the command's own form.
  if (preset.records_dir) return tools.open(PATH, { preset, plain: true });
  const sheet = openSheet({ label: "Export a scan", wide: true });
  const content = h("div", { class: "sec-tool" }, skeleton(4, "row"));
  const filesHolder = h("div", { class: "sec-tool-holder" });
  const problem = h("span", { class: "tool-problem" });
  const go = button({ label: "Export", glyph: "up", tone: "primary", onclick: () => run() });
  const status = statusLine();
  go.disabled = true;
  let open = true;
  let plan = null;
  let place = null;
  let typed = typeof preset.output === "string" ? preset.output : "";
  // Once the person has typed a folder, choosing another scan leaves it alone. Until then, and again once the box is emptied, the folder offered follows the scan.
  let touched = typed !== "";
  let planTicket = 0;
  let placeTicket = 0;
  let busy = false;
  sheet.closed.then(() => (open = false));

  const paintFoot = () => (go.disabled = busy || plan === null || place?.state !== "new");

  async function checkPlace() {
    const mine = (placeTicket += 1);
    place = null;
    paintFoot();
    if (typed.trim() === "") return status.say("", "Name a folder for the export.");
    status.say("busy", "Checking the folder");
    try {
      const found = await checkExportPlace(typed);
      if (mine !== placeTicket) return;
      place = found;
      const [tone, words] = PLACES[found.state];
      status.say(tone, words(found));
    } catch (error) {
      if (mine !== placeTicket) return;
      status.say("bad", error.message);
    }
    paintFoot();
  }

  const box = pathBox({
    label: "Folder for the export", placeholder: "A folder that is not there yet", value: typed, foldersOnly: true,
    onChange(text) {
      typed = text;
      touched = text.trim() !== "";
      checkPlace();
    },
  });

  async function loadPlan(runId) {
    const mine = (planTicket += 1);
    plan = null;
    paintFoot();
    filesHolder.replaceChildren(...skeleton(3, "row"));
    try {
      const found = await readExportPlan(runId);
      if (mine !== planTicket) return;
      plan = found;
      const total = found.files.reduce((sum, file) => sum + file.bytes, 0);
      filesHolder.replaceChildren(fileRows(found.files), h("p", { class: "sec-tool-hint", text: `${plural(found.files.length, "file")}, ${formatBytes(total)} in all. The scan itself stays where it is.` }));
      if (!touched) {
        typed = shownPath(found.suggested);
        box.setValue(typed);
      }
      checkPlace();
    } catch (error) {
      if (mine !== planTicket) return;
      filesHolder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This scan didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => loadPlan(runId) }) }));
    }
  }

  async function run() {
    if (busy || plan === null) return;
    busy = true;
    paintFoot();
    problem.textContent = "";
    try {
      const done = await exportRun(plan.run.run_id, typed);
      if (!open) return;
      const total = done.files.reduce((sum, file) => sum + file.bytes, 0);
      filesHolder.replaceChildren(
        outcomeCard({
          tone: "good", title: "Exported", body: `${plural(done.files.length, "file")}, ${formatBytes(total)}, in a new folder.`,
          extra: [h("p", { class: "sec-outcome-path" }, pathChip(done.output)), fileRows(done.files)],
          actions: [button({ label: "Done", small: true, tone: "primary", onclick: () => sheet.close() })],
        }),
      );
      // The folder is there now, so this place cannot take a second export. Typing another folder checks that one.
      place = null;
      status.say("good", "The export is in this folder now.");
    } catch (error) {
      if (open) problem.textContent = error.message;
      checkPlace();
    }
    busy = false;
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
  if (found.runs.length === 0) {
    const starter = createScanStarter(context);
    content.replaceChildren(
      notice({
        glyph: "clock", title: "No scans yet", body: "An export saves one scan as files. Once a scan has run, it can be exported from here.",
        action: button({ label: "Scan every app", glyph: "shield", tone: "primary", onclick: () => (sheet.close(), starter.everything()) }),
      }),
    );
    return;
  }
  const asked = found.runs.find((candidate) => candidate.run_id === preset.run);
  if (preset.run && !asked) problem.textContent = "The scan this was opened for is no longer saved, so the latest one is shown.";
  const first = asked ?? found.runs[0];
  content.replaceChildren(
    part("Scan", createRunPicker({ runs: found.runs, picked: first.run_id, fit: FIT, onPick: loadPlan }).element),
    part("What the folder will hold", filesHolder),
    part("Where it goes", box.element, status.element),
  );
  await loadPlan(first.run_id);
}
