import { h, icon, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { confirmAction, openSheet } from "../../overlays.js";
import { button, copyChip } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { createCloudCard } from "./cloud_card.js";
import { readUploadPlan } from "./tools_api.js";
import { everyOption, failureIn, fileCard, part, pathBox, printedLines, statusLine, toolHead } from "./tools_kit.js";
import { bringIntoView, outcomeCard, runCard, showRunWhenClosed, startWatched } from "./tools_run.js";
import { UPLOAD_PROBLEMS } from "./tools_words.js";

const PATH = "devops security upload";
const TOKENS = PATH.split(" ");
const LEDE = "Put a copy of one file in your cloud storage and get a link to it that you can share.";
const FINGERPRINT_SHOWN = 12;
const FINGERPRINT_NOTE = "A folder named after the file's fingerprint. A changed file gets a new one, so an earlier upload stays as it was.";

// Where the file lands, drawn as the folders it goes through. The one named after the fingerprint stands out, since that is the unusual part.
function landing(cloud, plan) {
  const print = plan.fingerprint ? `${plan.fingerprint.slice(0, FINGERPRINT_SHOWN)}…` : "its fingerprint";
  const steps = [[cloud.name, "cloud"], ...plan.folder.split("/").map((name) => [name, ""]), [print, "print"], [plan.file.name, "file"]];
  return h("ol", { class: "sec-landing" }, steps.flatMap(([name, kind], index) => [index > 0 && h("li", { class: "sep", "aria-hidden": "true", text: "/" }), h("li", { class: kind, title: kind === "print" ? FINGERPRINT_NOTE : name, text: name })]));
}

// Upload a file, in a sheet: which cloud it goes to and whether that cloud answers, the file with its size, the exact place it lands, then
// the upload as a task this sheet watches, which ends with the link. `preset.path` is the file to start with.
export async function open(context, { preset = {} }) {
  const { activity, tools } = context;
  const sheet = openSheet({ label: "Upload a file to cloud storage", wide: true });
  const fileHolder = h("div", { class: "sec-tool-holder" });
  const landHolder = h("div", { class: "sec-tool-holder" });
  const runHolder = h("div", { class: "sec-tool-holder" });
  const status = statusLine();
  const problem = h("span", { class: "tool-problem" });
  const go = button({ label: "Upload", glyph: "up", tone: "primary", onclick: () => upload().catch((error) => toast(error.message)) });
  let cloud = null;
  let plan = null;
  let typed = typeof preset.path === "string" ? preset.path : "";
  let ticket = 0;
  let running = null;
  const isOpen = showRunWhenClosed(sheet, () => running);

  const ready = () => cloud !== null && !cloud.problem && plan !== null && plan.problem === null;
  const paintFoot = () => (go.disabled = !ready() || running !== null);

  function paintLanding() {
    landHolder.replaceChildren(
      ...(ready()
        ? [landing(cloud, plan), h("p", { class: "sec-tool-hint", text: `${FINGERPRINT_NOTE} The upload ends with a link, and anyone who has that link can open the file.` })]
        : [h("p", { class: "sec-tool-hint", text: cloud?.problem ? "Set up a cloud first. Then this shows where the file goes." : "Choose a file to see where it goes." })]),
    );
    paintFoot();
  }

  async function look() {
    const mine = (ticket += 1);
    plan = null;
    if (running === null) runHolder.replaceChildren();
    if (typed.trim() === "") {
      status.say("", "");
      fileHolder.replaceChildren();
      return paintLanding();
    }
    status.say("busy", "Looking at the file");
    paintLanding();
    try {
      const found = await readUploadPlan(typed);
      if (mine !== ticket) return;
      plan = found;
      status.say(found.problem ? "bad" : "", found.problem ? UPLOAD_PROBLEMS[found.problem] : "");
      fileHolder.replaceChildren(...(found.file.kind === "missing" ? [] : [fileCard(found.file)]));
    } catch (error) {
      if (mine !== ticket) return;
      status.say("bad", error.message);
      fileHolder.replaceChildren();
    }
    paintLanding();
  }

  const box = pathBox({
    label: "File to upload", placeholder: "Type a file's path, or pick one from the list", value: typed, glyph: "report",
    onChange(text) {
      typed = text;
      look();
    },
  });

  function showOutcome(end, name, shown) {
    const again = button({ label: "Upload another", small: true, onclick: () => (runHolder.replaceChildren(), box.setValue(""), (typed = ""), look()) });
    const consoleButton = button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", onclick: () => (sheet.close(), shown()) });
    if (!end.ok) {
      return runHolder.replaceChildren(
        outcomeCard({ tone: "bad", title: end.stopped ? "The upload was stopped" : "The upload did not finish", body: end.stopped ? "Whatever had reached the cloud may still be there." : failureIn(end.text) || "It gave no reason.", actions: [consoleButton, button({ label: "Try again", glyph: "refresh", small: true, onclick: () => upload() })] }),
      );
    }
    const link = printedLines(end.text).findLast((line) => /^https?:\/\/\S+$/.test(line));
    runHolder.replaceChildren(
      outcomeCard({
        tone: "good", title: `${name} is uploaded`, body: link ? "Anyone who has this link can open the file." : "The link could not be read here. It is the last line in the console.",
        extra: link && h("p", { class: "sec-outcome-path" }, copyChip(link), h("a", { class: "link", href: link, target: "_blank", rel: "noopener noreferrer" }, "Open it", icon("external", 12))),
        actions: [!link && consoleButton, again, button({ label: "Done", small: true, tone: "primary", onclick: () => sheet.close() })],
      }),
    );
  }

  async function upload() {
    if (!ready() || running) return;
    const file = plan.file;
    const sure = await confirmAction({
      title: `Upload ${file.name}?`, confirm: "Upload",
      body: `${formatBytes(file.size)} goes to ${cloud.name}, and a link is made for it. Anyone who has the link can open the file.`,
    });
    if (!sure || !isOpen()) return;
    const card = runCard({ title: `Uploading ${file.name}`, onShow: () => sheet.close(), onStop: () => running?.stop() });
    card.say("Copying it, taking its fingerprint, uploading, then making the link");
    runHolder.replaceChildren(card.element);
    bringIntoView(runHolder);
    running = await startWatched(activity, { title: `Upload ${file.name}`, emoji: "📤", arguments: [...TOKENS, file.path] });
    paintFoot();
    const watched = running;
    const end = await watched.ended;
    running = null;
    card.end();
    if (!isOpen()) return;
    showOutcome(end, file.name, watched.show);
    bringIntoView(runHolder);
    paintFoot();
  }

  const cloudCard = createCloudCard({
    tools, sheet,
    onState(found) {
      cloud = found;
      paintLanding();
    },
  });
  sheet.body.append(toolHead(PATH, LEDE), h("div", { class: "sec-tool" }, part("Cloud", cloudCard.element), part("File", box.element, status.element, fileHolder), part("Where it lands", landHolder), runHolder));
  sheet.foot.hidden = false;
  sheet.foot.append(agentButton(context.activity, { commands: [PATH] }), everyOption({ tools, sheet, path: PATH, preset }), problem, go);
  paintLanding();
  await look();
}
