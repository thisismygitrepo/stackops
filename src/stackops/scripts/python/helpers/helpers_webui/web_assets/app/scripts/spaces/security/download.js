import { debounce, h, icon, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { openSheet } from "../../overlays.js";
import { button, copyChip, notice, pill, textBox } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { createScanStarter } from "./scan_start.js";
import { checkDriveLink, readDownloadPlace } from "./tools_api.js";
import { everyOption, failureIn, part, pathWord, printedLines, statusLine, toolHead } from "./tools_kit.js";
import { bringIntoView, outcomeCard, runCard, showRunWhenClosed, startWatched } from "./tools_run.js";
import { LINK_FORMS, LINK_STATES } from "./tools_words.js";

const PATH = "devops security download";
const TOKENS = PATH.split(" ");
const LEDE = "Fetch a file that was shared from Google Drive, by its link or its file ID.";
const FILE_LINK = "https://drive.google.com/uc?id=";
// What the command prints when Google Drive refuses a file. Its last line alone says too little to show.
const NOT_HANDED_OVER = "Cannot retrieve the public link";
const CHECK_DELAY_MILLISECONDS = 500;
const PROGRESS_MILLISECONDS = 700;
// States in which a download cannot work, so the button stays off. In the others the check could not say, and a try is allowed.
const DEAD_ENDS = ["private", "missing"];
// Google Drive's page for a large file gives its size as "476M" or "2.1G".
const roughSize = (text) => text.replace(/^([\d.]+)\s*([kKMGT])$/, (_whole, amount, unit) => `${amount} ${unit.toUpperCase()}B`);

// Download from Google Drive, in a sheet: the pasted link is read and Google Drive is asked about the file before anything is fetched, the
// place the file goes to is shown with the room there, then the download runs as a task this sheet watches, with the command's own progress.
// `preset.url` is the link to start with.
export async function open(context, { preset = {} }) {
  const { activity, tools } = context;
  const sheet = openSheet({ label: "Download from Google Drive", wide: true });
  const status = statusLine();
  const foundHolder = h("div", { class: "sec-tool-holder" });
  const placeHolder = h("div", { class: "sec-tool-holder" });
  const runHolder = h("div", { class: "sec-tool-holder" });
  const problem = h("span", { class: "tool-problem" });
  const go = button({ label: "Download", glyph: "download", tone: "primary", onclick: () => download().catch((error) => toast(error.message)) });
  let typed = typeof preset.url === "string" ? preset.url : "";
  let link = null;
  let place = null;
  let checking = new AbortController();
  let running = null;
  const isOpen = showRunWhenClosed(sheet, () => running);
  sheet.closed.then(() => checking.abort());

  const usable = () => link !== null && link.form === "file" && !DEAD_ENDS.includes(link.state);
  const paintFoot = () => (go.disabled = !usable() || !place?.ready || running !== null);

  function paintPlace() {
    if (place === null) return;
    if (!place.ready) {
      placeHolder.replaceChildren(notice({ glyph: "plug", title: "Downloads from Google Drive are not available here", body: "The part of StackOps that fetches from Google Drive is missing from this install. Update StackOps to get it back." }));
      return paintFoot();
    }
    const tight = link?.size !== null && link?.size !== undefined && link.size > place.free;
    placeHolder.replaceChildren(
      h("p", { class: "sec-tool-line" }, "A new folder inside ", pathWord(place.folder), ", made for this download. The file keeps the name it has on Google Drive."),
      h("p", { class: `sec-tool-hint${tight ? " bad" : ""}`, text: tight ? `The file is larger than the ${formatBytes(place.free)} free on this disk.` : `${formatBytes(place.free)} free on this disk. That folder is for temporary files, so move the file out if you want to keep it.` }),
    );
    paintFoot();
  }

  function paintFound() {
    const found = link?.form === "file" && link.state === "found";
    foundHolder.replaceChildren(
      ...(found
        ? [h("div", { class: "sec-file" }, h("span", { class: "sec-file-glyph" }, icon("report", 20)), h("div", { class: "sec-file-text" }, h("strong", {}, h("span", { text: link.name || "A file without a name" }), pill("Shared by link", "good")), h("span", { text: link.size !== null ? formatBytes(link.size) : link.size_text ? `About ${roughSize(link.size_text)}` : "Size not given" }), h("span", { class: "dim", text: `File ID ${link.id}` })))]
        : []),
    );
  }

  async function check() {
    checking.abort();
    checking = new AbortController();
    const mine = checking;
    link = null;
    paintFound();
    paintFoot();
    if (typed.trim() === "") return status.say("", "");
    status.say("busy", "Asking Google Drive about this file");
    try {
      const found = await checkDriveLink(typed, mine.signal);
      link = found;
      if (found.form !== "file") status.say(...LINK_FORMS[found.form]);
      else if (found.state === "found") status.say("good", "Google Drive has this file, and anyone with the link may fetch it.");
      else status.say(...LINK_STATES[found.state]);
    } catch (error) {
      if (mine.signal.aborted) return;
      status.say("bad", error.message);
    }
    paintFound();
    paintPlace();
  }

  const box = textBox(typed, {
    placeholder: "Paste a Google Drive link or a file ID", "aria-label": "Google Drive link or file ID",
    oninput: debounce(() => {
      typed = box.value;
      check();
    }, CHECK_DELAY_MILLISECONDS),
  });

  function showOutcome(end, shown) {
    const consoleButton = button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", onclick: () => (sheet.close(), shown()) });
    if (!end.ok) {
      return runHolder.replaceChildren(
        outcomeCard({ tone: "bad", title: end.stopped ? "The download was stopped" : "The download did not finish", body: end.stopped ? "A part of the file may be left in the folder made for it." : end.text.includes(NOT_HANDED_OVER) ? "Google Drive would not hand the file over. It may not be shared with everyone who has the link, or too many people fetched it lately." : failureIn(end.text) || "It gave no reason.", actions: [consoleButton, button({ label: "Try again", glyph: "refresh", small: true, onclick: () => download() })] }),
      );
    }
    const file = printedLines(end.text).findLast((line) => /^(\/|[A-Za-z]:[\\/])/.test(line));
    const starter = createScanStarter(context);
    runHolder.replaceChildren(
      outcomeCard({
        tone: "good", title: "Downloaded", body: file ? "The file is at the path below." : "The path could not be read here. It is the last line in the console.",
        extra: file && h("p", { class: "sec-outcome-path" }, copyChip(file)),
        actions: [
          !file && consoleButton,
          file && button({ label: "Scan this file", glyph: "shield", small: true, title: "Ask VirusTotal's antivirus engines about it", onclick: () => (sheet.close(), starter.path(file)) }),
          button({ label: "Done", small: true, tone: "primary", onclick: () => sheet.close() }),
        ],
      }),
    );
  }

  async function download() {
    if (!usable() || running) return;
    const card = runCard({ title: link.name ? `Downloading ${link.name}` : "Downloading", onShow: () => sheet.close(), onStop: () => running?.stop() });
    card.say("Starting");
    runHolder.replaceChildren(card.element);
    bringIntoView(runHolder);
    // The file goes to the command as a link built from its ID, which is the ID the command would read out of what was pasted. A bare ID
    // can start with a dash, and the command line would take that for an option.
    running = await startWatched(activity, { title: "Download from Google Drive", emoji: "📥", arguments: [...TOKENS, `${FILE_LINK}${link.id}`] });
    paintFoot();
    const watched = running;
    // The command draws its own progress line in the console. The latest percentage on it is shown here as a bar.
    const progress = setInterval(() => {
      const share = [...watched.text().matchAll(/(\d{1,3})%\|/g)].at(-1);
      card.say(share ? `${share[1]}% fetched` : "Fetching");
      card.share(share ? Number(share[1]) / 100 : null);
    }, PROGRESS_MILLISECONDS);
    const end = await watched.ended;
    clearInterval(progress);
    running = null;
    card.end();
    if (!isOpen()) return;
    showOutcome(end, watched.show);
    bringIntoView(runHolder);
    paintFoot();
  }

  sheet.body.append(toolHead(PATH, LEDE), h("div", { class: "sec-tool" }, part("Link", box, status.element, foundHolder), part("Where it goes", placeHolder), runHolder));
  sheet.foot.hidden = false;
  sheet.foot.append(agentButton(context.activity, { commands: [PATH] }), everyOption({ tools, sheet, path: PATH, preset }), problem, go);
  paintFoot();
  box.focus();
  try {
    place = await readDownloadPlace();
    paintPlace();
  } catch (error) {
    placeHolder.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "Where downloads go could not be read", body: error.message }));
  }
  if (typed.trim() !== "") await check();
}
