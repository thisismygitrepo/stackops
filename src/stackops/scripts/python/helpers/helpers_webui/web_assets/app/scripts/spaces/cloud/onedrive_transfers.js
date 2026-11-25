import { debounce, h, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { confirmAction, openDialog } from "../../overlays.js";
import { button, field, iconButton, pathChip, textBox } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { failureIn, pathBox } from "../security/tools_kit.js";
import { outcomeCard, runCard, startWatched } from "../security/tools_run.js";
import { downloadArguments, removeItem, startInTurn, uploadArguments } from "./onedrive_api.js";
import { isFolder, joinPath } from "./onedrive_words.js";

const CHECK_PAUSE_MILLISECONDS = 250;
let lastSaveFolder = null;

// A path as the command needs it: `~` is this machine's home, and a name that starts with a dash is anchored so it is not read as an option.
function localPath(typed) {
  const text = typed.trim();
  if (text === "~") return state.boot.home;
  if (text.startsWith("~/")) return `${state.boot.home}/${text.slice(2)}`;
  return text.startsWith("-") ? `./${text}` : text;
}
const lastPart = (path) => path.replace(/[\\/]+$/, "").split(/[\\/]/).pop();
const problemLine = () => {
  const element = h("p", { class: "od-problem", hidden: true });
  return { element, say: (text) => ((element.textContent = text), (element.hidden = text === "")) };
};

// The uploads and downloads of this visit, each as a card: on its way with a clock and Stop, then how it ended. They run as tasks kept out
// of the Activity panel; "Show the console" brings one there.
export function createTransfers({ activity }) {
  const element = h("div", { class: "od-transfers", hidden: true });
  const tidy = () => (element.hidden = element.childElementCount === 0);

  async function run({ title, emoji, runArguments, doing, done, onDone }) {
    const holder = h("div", {});
    element.prepend(holder);
    tidy();
    const dismiss = () => (holder.remove(), tidy());
    let task;
    try {
      task = await startInTurn(() => startWatched(activity, { title, emoji, arguments: runArguments }));
    } catch (error) {
      holder.replaceChildren(outcomeCard({ tone: "bad", title: `${title} could not start`, body: error.message, actions: [button({ label: "Dismiss", small: true, tone: "ghost", onclick: dismiss })] }));
      return;
    }
    const card = runCard({ title: doing, onStop: task.stop, onShow: task.show });
    holder.replaceChildren(card.element);
    const end = await task.ended;
    card.end();
    const consoleButton = button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", onclick: task.show });
    const closer = iconButton("close", "Dismiss", dismiss);
    if (end.ok) {
      holder.replaceChildren(outcomeCard({ tone: "good", title: done.title, extra: done.extra ?? [], actions: [consoleButton, closer] }));
      onDone?.();
    } else {
      holder.replaceChildren(outcomeCard({ tone: "bad", title: end.stopped ? `${title} was stopped` : `${title} did not work`, body: end.stopped ? "" : failureIn(end.text), actions: [consoleButton, closer] }));
    }
  }
  return { element, run };
}

// Upload: a file of this computer into the folder on show. `names` are the files already in that folder, so replacing one is a choice made
// here and not a surprise from the drive. `preset` is a path to start with.
export function openUpload({ account, folder, names, preset = "", transfers, onDone }) {
  const dialog = openDialog({ label: "Upload a file to OneDrive", size: "small od-dialog" });
  const problem = problemLine();
  const name = textBox("", { "aria-label": "Name on OneDrive", placeholder: "The file's own name" });
  let named = false;
  let replace = false;
  name.addEventListener("input", () => ((named = name.value !== ""), check()));
  const toggle = h("button", { class: "mini-toggle", type: "button", role: "switch", "aria-checked": "false", onclick: () => ((replace = !replace), toggle.setAttribute("aria-checked", String(replace)), check()) }, h("i", { class: "switch" }), h("span", { text: "Replace a file of the same name" }));
  const go = button({ label: "Upload", glyph: "up", tone: "primary", onclick: () => submit() });
  const box = pathBox({ label: "File on this computer", placeholder: "Type a file's path, or pick one from the list", value: preset, glyph: "report", onChange: () => (named || (name.value = lastPart(box.input.value)), check()) });

  function reason() {
    const typed = box.input.value.trim();
    if (typed === "") return "";
    if (/[\\/]$/.test(typed)) return "That is a folder. Choose a file.";
    const target = name.value.trim();
    if (target === "") return "Give the file a name on OneDrive.";
    if (target.includes("/")) return "A name cannot contain a slash.";
    if (names.includes(target) && !replace) return `${target} is already in this folder. Turn on “Replace” to overwrite it.`;
    return "";
  }
  function check() {
    const why = reason();
    problem.say(why);
    go.disabled = why !== "" || box.input.value.trim() === "";
  }
  function submit() {
    check();
    if (go.disabled) return;
    const target = name.value.trim();
    dialog.close();
    transfers.run({
      title: `Upload of ${target}`, emoji: "📤", runArguments: uploadArguments(account, localPath(box.input.value), joinPath(folder, target), replace), doing: `Uploading ${target}`,
      done: { title: `${target} is on OneDrive`, extra: [h("p", { text: `In ${folder === "/" ? "the top folder" : folder}.` })] },
      onDone,
    });
  }

  dialog.body.append(
    h("h2", { text: "Upload a file" }),
    h("p", { text: `It goes to ${folder === "/" ? "the top folder" : folder} of ${account}.` }),
    field("File on this computer", box.element),
    field("Name on OneDrive", name),
    toggle,
    problem.element,
    h("div", { class: "dialog-actions" }, button({ label: "Cancel", onclick: () => dialog.close() }), go),
  );
  if (preset) name.value = lastPart(preset);
  check();
  box.input.focus();
}

// Download: one file of the drive into a folder of this computer. The command never overwrites, so a name that is taken there is said here.
export function openDownload({ account, path, item, transfers }) {
  const dialog = openDialog({ label: "Download a file from OneDrive", size: "small od-dialog" });
  const problem = problemLine();
  const name = textBox(item.name, { "aria-label": "Name on this computer" });
  const go = button({ label: "Download", glyph: "download", tone: "primary", onclick: () => submit() });
  let ticket = 0;
  let folderPath = null;

  // The folder is read the way the suggestions read it, which gives its full path, and the list of what starts with the name there says
  // whether that name is taken.
  async function check() {
    const mine = (ticket += 1);
    go.disabled = true;
    folderPath = null;
    const target = name.value.trim();
    if (box.input.value.trim() === "" || target === "") return problem.say(target === "" ? "Give the file a name." : "");
    if (/[\\/]/.test(target)) return problem.say("A name cannot contain a slash.");
    try {
      const { path: full } = await api.directory(box.input.value.trim(), state.settings.workingDirectory);
      const { entries } = await api.paths(`${full}/${target}`, state.settings.workingDirectory);
      if (mine !== ticket) return;
      if (entries.some((entry) => lastPart(entry) === target)) return problem.say(`${target} is already in that folder. Downloads never overwrite: choose another name or folder.`);
      folderPath = full;
      problem.say("");
      go.disabled = false;
    } catch (error) {
      if (mine === ticket) problem.say(error.message);
    }
  }
  const checkSoon = debounce(check, CHECK_PAUSE_MILLISECONDS);
  name.addEventListener("input", checkSoon);
  const box = pathBox({ label: "Folder on this computer", placeholder: "Type a folder", value: lastSaveFolder ?? state.settings.workingDirectory, foldersOnly: true, onChange: check });

  function submit() {
    if (go.disabled || folderPath === null) return;
    const target = name.value.trim();
    const saved = `${folderPath}/${target}`;
    lastSaveFolder = folderPath;
    dialog.close();
    transfers.run({
      title: `Download of ${item.name}`, emoji: "📥", runArguments: downloadArguments(account, path, saved), doing: `Downloading ${item.name}`,
      done: { title: `${item.name} is downloaded`, extra: [h("div", { class: "sec-outcome-path" }, pathChip(saved))] },
    });
  }

  dialog.body.append(
    h("h2", { text: `Download ${item.name}` }),
    h("p", { text: `${formatBytes(item.size ?? 0)} from ${account}.` }),
    field("Save in", box.element),
    field("Name on this computer", name),
    problem.element,
    h("div", { class: "dialog-actions" }, button({ label: "Cancel", onclick: () => dialog.close() }), go),
  );
  check();
}

// Delete, after a yes: the drive moves the item to its recycle bin, from where OneDrive's site can bring it back.
export async function deleteItem({ account, path, item, onDone }) {
  const what = isFolder(item) ? "The folder and everything in it go" : "It goes";
  if (!(await confirmAction({ title: `Move “${item.name}” to the recycle bin?`, body: `${what} to the recycle bin of ${account}. OneDrive's site can restore it from there.`, confirm: "Move to recycle bin", tone: "danger" }))) return;
  try {
    await removeItem(account, path);
  } catch (error) {
    return toast(`${item.name} was not removed. ${error.message}`);
  }
  toast(`${item.name} is in the recycle bin.`, "info");
  onDone();
}
