import { h, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { confirmAction, openSheet } from "../../overlays.js";
import { button, notice, segmented, skeleton } from "../../widgets.js";
import { createKeyList, OWN_KEY } from "./locker_keys.js";
import { compressionPicker, crossHint, eyeFor, lockMarks, madeFor, METHOD_WORDS, replaceSwitch, resultLine, secretBox } from "./locker_parts.js";
import { runLocker } from "./locker_run.js";
import { lookAt, readLocker } from "./tools_api.js";
import { fileCard, part, pathBox, shownPath, statusLine, toolHead } from "./tools_kit.js";
import { showRunWhenClosed } from "./tools_run.js";
import { LOOK_PROBLEMS } from "./tools_words.js";

const PATHS = { encrypt: "devops data encrypt", decrypt: "devops data decrypt" };
const LEDES = {
  encrypt: "Lock a file or a whole folder with GPG, so that only the right password or key opens it.",
  decrypt: "Open a file that was locked with GPG. A folder that was packed before it was locked comes out as a folder.",
};
const MODES = [["encrypt", "Encrypt"], ["decrypt", "Decrypt"]];
const METHODS = [["password", "With a password"], ["key", "With a key"]];
const FILE_TITLES = { encrypt: "File or folder", decrypt: "Encrypted file" };
const LOCK_TITLES = { encrypt: "How to lock it", decrypt: "How it was locked" };

// Encrypt and decrypt share this sheet, since they are the two halves of one job: each card opens it on its own half, and a picked file that
// belongs to the other half offers the switch. The file is looked at as soon as it is picked, the lock is chosen (a password, or a key from
// the ones GPG holds here), the result's name and place are shown, then it runs. `preset` holds the command's values; a password is never
// taken from it, and a password kept in a file or a variable is left to the command's own form.
export async function openLocker(context, startMode, { preset = {} }) {
  const { tools } = context;
  if (preset.password_file || preset.password_env) return tools.open(PATHS[startMode], { preset, plain: true });
  const sheet = openSheet({ label: startMode === "encrypt" ? "Encrypt a file or folder" : "Decrypt a file", wide: true });
  const view = {
    mode: startMode, typed: typeof preset.path === "string" ? preset.path : "", method: ["asymmetric", "a"].includes(preset.encryption) ? "key" : "password",
    recipient: typeof preset.recipient === "string" ? preset.recipient : OWN_KEY, compression: "", output: typeof preset.output === "string" ? preset.output : "",
    overwrite: preset.overwrite === "on", look: null, locker: null, running: null, busy: false,
  };
  let ticket = 0;
  // The file whose lock was last read to set password or key by itself. A choice the person makes after that stands until another file is picked.
  let followed = "";
  const headHolder = h("div");
  const fileTitle = h("h2");
  const lockTitle = h("h2");
  const fileHolder = h("div", { class: "sec-tool-holder" });
  const lockWords = h("p", { class: "sec-tool-hint" });
  const keyHolder = h("div", { class: "sec-tool-holder" });
  const resultHolder = h("div", { class: "sec-tool-holder" });
  const runHolder = h("div", { class: "sec-tool-holder" });
  const status = statusLine();
  const lockNote = statusLine();
  const hint = h("span", { class: "sec-tool-wait" });
  const go = button({ label: startMode === "encrypt" ? "Encrypt" : "Decrypt", glyph: "lock", tone: "primary", onclick: () => run().catch((error) => toast(error.message)) });
  const isOpen = showRunWhenClosed(sheet, () => view.running);
  const changed = () => (runHolder.replaceChildren(), paint());

  const pass = secretBox({ label: "Password", onInput: changed });
  const again = secretBox({ label: "The same password again", onInput: changed });
  const passwordPane = h("div", { class: "sec-secret" }, pass.element, eyeFor([pass, again]), again.element);
  const modeSwitch = segmented(MODES, (mode) => setMode(mode));
  const methodSwitch = segmented(METHODS, (method) => ((view.method = method), changed()));
  const box = pathBox({ label: "File or folder", placeholder: "Type a path, or pick from the list", value: view.typed, onChange: (text) => ((view.typed = text), refresh()) });
  const outBox = pathBox({ label: "Save the result as", placeholder: "", value: view.output, onChange: (text) => ((view.output = text), refresh()) });
  // The boxes that are typed in are made once and stay on the page: one that is put back in by every repaint loses the keyboard mid-word.
  const outField = h("label", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Save the result somewhere else" })), outBox.element, h("span", { class: "field-hint", text: "Leave this empty for the place named above." }));
  let keys = null;

  // Why the run cannot start yet, in a few words, or nothing when it can.
  function blocker() {
    if (!view.look) return view.typed.trim() ? "" : "Choose a file first.";
    const problem = view.look.problem;
    if (problem && problem !== "exists") return LOOK_PROBLEMS[problem];
    if (problem === "exists" && !view.overwrite) return "Something is already at the place for the result.";
    if (view.method === "password") {
      if (pass.input.value === "") return "Type a password.";
      return view.mode === "encrypt" && pass.input.value !== again.input.value ? "Type the same password twice." : "";
    }
    if (view.mode === "encrypt") return keys.usable() ? "" : "Choose a key GPG can encrypt for.";
    return view.look.encrypted.method === "key" && !view.look.encrypted.have_key ? "The key this file was made for is not on this machine." : "";
  }

  function paint() {
    const { mode, look, locker } = view;
    modeSwitch.set(mode);
    methodSwitch.set(view.method);
    fileTitle.textContent = FILE_TITLES[mode];
    lockTitle.textContent = LOCK_TITLES[mode];
    go.querySelector("span").textContent = mode === "encrypt" ? "Encrypt" : "Decrypt";
    const naming = look && !["missing", "not_file", "not_gpg_name", "no_name"].includes(look.problem);
    status.say(look && !naming ? "bad" : "", look && !naming ? LOOK_PROBLEMS[look.problem] : "");
    fileHolder.replaceChildren(...(look && look.source.kind !== "missing" ? [fileCard(look.source, lockMarks(look, mode)), crossHint(look, mode, setMode)].filter(Boolean) : []));
    lockWords.textContent = METHOD_WORDS[mode][view.method];
    passwordPane.hidden = view.method !== "password";
    again.element.hidden = mode !== "encrypt";
    keyHolder.hidden = view.method !== "key" || mode !== "encrypt";
    const [tone, words] = mode === "decrypt" && look ? madeFor(look, locker) : ["", ""];
    const sniffed = look?.encrypted.method;
    const other = mode === "decrypt" && ["password", "key"].includes(sniffed) && sniffed !== view.method;
    lockNote.say(other ? "warn" : tone, other ? `This file looks like it was locked ${sniffed === "key" ? "for a key" : "with a password"}.` : view.method === "key" ? words : "");
    outBox.input.placeholder = naming ? shownPath(look.default_output) : "";
    outField.hidden = !naming;
    resultHolder.replaceChildren(
      ...(naming
        ? [
            resultLine(look, mode),
            mode === "encrypt" && look.source.kind === "folder" && compressionPicker({ choices: locker.compressions, value: view.compression, onPick: (choice) => ((view.compression = choice), refresh()) }),
            look.problem === "exists" && replaceSwitch({ on: view.overwrite, onToggle: () => ((view.overwrite = !view.overwrite), changed()) }),
            look.problem === "overlap" && h("p", { class: "sec-tool-hint bad", text: LOOK_PROBLEMS.overlap }),
          ].filter(Boolean)
        : [h("p", { class: "sec-tool-hint", text: "Choose a file to see what comes out and where." })]),
    );
    const waiting = blocker();
    hint.textContent = view.busy || view.running ? "" : waiting;
    go.disabled = waiting !== "" || !look || view.busy || view.running !== null;
  }

  async function refresh() {
    const mine = (ticket += 1);
    runHolder.replaceChildren();
    if (view.typed.trim() === "") {
      view.look = null;
      return paint();
    }
    try {
      const found = await lookAt({ mode: view.mode, path: view.typed, compression: view.compression, output: view.output });
      if (mine !== ticket) return;
      view.look = found;
      // A file that says how it was locked sets password or key by itself, once per file.
      const told = found.encrypted.method;
      if (view.mode === "decrypt" && ["password", "key"].includes(told) && followed !== found.source.path) view.method = told;
      followed = found.source.path;
    } catch (error) {
      if (mine !== ticket) return;
      view.look = null;
      status.say("bad", error.message);
    }
    paint();
  }

  function setMode(mode) {
    view.mode = mode;
    view.output = "";
    view.overwrite = false;
    followed = "";
    outBox.setValue("");
    headHolder.replaceChildren(toolHead(PATHS[mode], LEDES[mode]));
    refresh();
  }

  async function run() {
    if (blocker() !== "" || view.busy || view.running) return;
    // Replacing takes away what is at the result's place, a whole folder included, so it asks first and names the place.
    if (view.look.problem === "exists" && !(await confirmAction({ title: "Replace what is there?", body: `What is at ${shownPath(view.look.output)} now is removed, with everything in it, and the result takes its place. This cannot be undone.`, confirm: "Replace it", tone: "danger" }))) return;
    if (!isOpen()) return;
    const startOver = () => (box.setValue(""), (view.typed = ""), refresh());
    await runLocker({ context, sheet, view, isOpen, runHolder, paint, refresh, startOver, tokens: PATHS[view.mode].split(" "), secrets: [pass.input, again.input], recipient: keys.chosen() });
  }

  const content = h("div", { class: "sec-tool" }, skeleton(4, "row"));
  headHolder.append(toolHead(PATHS[view.mode], LEDES[view.mode]));
  sheet.body.append(headHolder, content);
  sheet.foot.hidden = false;
  // The foot's link opens the form of the half on show when it is pressed, with the file and nothing else: a password is never handed on.
  const everything = button({ label: "Every option", glyph: "sliders", tone: "ghost", title: "The command's own form, with everything it can do", onclick: () => (sheet.close(), tools.open(PATHS[view.mode], { preset: view.typed.trim() ? { path: view.typed } : {}, plain: true })) });
  sheet.foot.append(agentButton(context.activity, () => ({ commands: [PATHS[view.mode]] })), everything, hint, go);
  go.disabled = true;
  try {
    view.locker = await readLocker();
  } catch (error) {
    content.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "What GPG has here didn't load", body: error.message }));
    return;
  }
  if (!view.locker.gpg) {
    content.replaceChildren(notice({ glyph: "lock", title: "GPG is not installed", body: "Encrypting and decrypting are done by GPG, and this machine does not have it. Install it, then open this again.", action: h("a", { class: "btn primary", href: "#/apps" }, h("span", { text: "Find GPG under Apps" })) }));
    return;
  }
  view.compression = view.locker.compressions.includes(preset.compression) ? preset.compression : view.locker.compressions[0];
  const wanted = view.locker.keys.find((key) => [key.fingerprint, key.id, key.email].includes(view.recipient));
  keys = createKeyList({ locker: view.locker, picked: wanted ? wanted.fingerprint : OWN_KEY, onPick: changed });
  keyHolder.append(keys.element);
  content.replaceChildren(
    h("div", { class: "sec-lock-mode" }, modeSwitch.element, h("span", { class: "sec-lock-gpg", text: `GPG ${view.locker.version} is on this machine` })),
    h("section", { class: "sec-tool-part" }, fileTitle, box.element, status.element, fileHolder),
    h("section", { class: "sec-tool-part" }, lockTitle, methodSwitch.element, lockWords, passwordPane, keyHolder, lockNote.element),
    part("What comes out", resultHolder, outField),
    runHolder,
  );
  await refresh();
}
