import { debounce, h, icon, tildify } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { button, emojiTile } from "../../widgets.js";
import { formatBytes, plural, relativeTime, titleOf } from "../../words.js";

const TYPING_PAUSE_MILLISECONDS = 250;
const REASON_LIMIT = 320;
const STATUS_GLYPHS = { good: "check", warn: "alert", bad: "alert", "": "info" };

export const shownPath = (path) => tildify(path, state.boot.home);

// What every sheet of these tools opens with: the tool's own mark and name, and a sentence on what it is for.
export function toolHead(path, lede) {
  const node = state.nodes.get(path);
  return h("header", { class: "tool-head" }, emojiTile(node.icon || "✨", node.path, 56), h("div", {}, h("span", { class: "overline", text: "Security" }), h("h1", { text: titleOf(node) }), h("p", { text: lede })));
}

// A path as a word in a sentence: shortened, in the code font, with the whole of it on hover.
export const pathWord = (path) => h("code", { class: "sec-path", title: path, text: shownPath(path) });

export const part = (title, ...content) => h("section", { class: "sec-tool-part" }, h("h2", { text: title }), ...content);

// The way to the command's own form, which has every option the view leaves out. It goes in the sheet's foot.
export function everyOption({ tools, sheet, path, preset }) {
  return button({
    label: "Every option", glyph: "sliders", tone: "ghost", title: "The command's own form, with everything it can do",
    onclick: () => {
      sheet.close();
      tools.open(path, { preset, plain: true });
    },
  });
}

// A box for a file or a folder on this machine, with the path suggestions every form has. An empty box lists the home folder.
// `onChange(text)` hears the box settle: after a pause in typing, and at once for a pick from the list. It always gets what the box holds
// at that moment, so a pause that ends after a pick does not bring back the text from before it.
export function pathBox({ label, placeholder, value = "", foldersOnly = false, glyph = "folder", onChange }) {
  const read = () => onChange(combo.input.value);
  const combo = createCombo({
    value, label, placeholder, glyph, emptyText: "Nothing here by that name",
    suggest: async (typed) => (await api.paths(typed || "~/", state.settings.workingDirectory)).entries.filter((entry) => !foldersOnly || entry.endsWith("/")).map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
    onInput: debounce(read, TYPING_PAUSE_MILLISECONDS),
    onPick: read,
  });
  return combo;
}

// One line under a box that says what was found there, in a tone. "busy" shows the turning ring.
export function statusLine() {
  const element = h("p", { class: "sec-tool-status", hidden: true });
  return {
    element,
    say(tone, text) {
      element.hidden = !text;
      element.className = `sec-tool-status ${tone}`;
      element.replaceChildren(tone === "busy" ? h("i", { class: "ring" }) : icon(STATUS_GLYPHS[tone], 14), h("span", { text }));
    },
  };
}

// What sits at a path, in a few words: a file's size, or how many files a folder holds and their size. The count stops at a limit on the server.
export function measureWords(measure) {
  const changed = measure.modified ? `changed ${relativeTime(measure.modified)}` : "";
  if (measure.kind === "file") return ["File", formatBytes(measure.size), changed].filter(Boolean).join(" · ");
  const most = measure.capped ? "more than " : "";
  return ["Folder", `${most}${plural(measure.files, "file")}`, `${most}${formatBytes(measure.size)}`, changed].filter(Boolean).join(" · ");
}

// A picked file as a card: its name, what it is, where it is, and any marks the view adds beside the name.
export function fileCard(measure, marks = []) {
  return h(
    "div",
    { class: "sec-file" },
    h("span", { class: "sec-file-glyph" }, icon(measure.kind === "folder" ? "folder" : "report", 20)),
    h("div", { class: "sec-file-text" }, h("strong", {}, h("span", { text: measure.name || measure.path }), marks), h("span", { text: measureWords(measure) }), h("span", { class: "dim", title: measure.path, text: shownPath(measure.path) })),
  );
}

// What a command said went wrong, from the console of its run: what stands under "Error", or its last line, which is where a failure that was
// not caught names itself. The line the server closes every run with ("[exit 1 · 0.9s]") ends it.
export function failureIn(text) {
  const lines = text.split("\n").map((line) => line.replace(/[│╭╮╰╯─]/g, "").trim()).filter(Boolean);
  const closing = lines.findIndex((line) => /^\[(exit \d+|stopped|done) · /.test(line));
  const said = closing < 0 ? lines : lines.slice(0, closing);
  const error = said.findIndex((line) => /^error(:|$)/i.test(line));
  const reason = (error >= 0 ? said.slice(/^error$/i.test(said[error]) ? error + 1 : error).join(" ") : (said.at(-1) ?? "")).replace(/^(error|\w+(Error|Exception)):\s*/i, "");
  return reason.length > REASON_LIMIT ? `${reason.slice(0, REASON_LIMIT)}…` : reason;
}

// The lines a run printed before the server's closing line, newest last.
export function printedLines(text) {
  const lines = text.split("\n").map((line) => line.trim()).filter(Boolean);
  const closing = lines.findIndex((line) => /^\[(exit \d+|stopped|done) · /.test(line));
  return closing < 0 ? lines : lines.slice(0, closing);
}
