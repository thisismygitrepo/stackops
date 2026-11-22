import { h, icon, toast } from "/assets/scripts/dom.js";
import { api } from "/assets/scripts/state.js";
import { markStale } from "../../data.js";
import { confirmAction, openDialog } from "../../overlays.js";
import { button, copyText, glyphTile, iconButton, notice, pathChip, pill, segmented, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { KIND_BY_ID, ORIGINS, STATES } from "./health_model.js";
import { TEXT_VIEWS, readingStats, renderLooseText } from "./loose_text.js";

const MARKDOWN = /\.(md|mdc|markdown)$/i;
// The settings block some files open with. Read as prose it would turn into a heading, so it is shown as written above the text.
const FRONT_MATTER = /^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;

function formatted(text) {
  const front = text.match(FRONT_MATTER);
  return [front && h("pre", { class: "prompt-code file-front", title: "Settings at the top of this file", text: front[1] }), renderLooseText(front ? text.slice(front[0].length) : text, "")].filter(Boolean);
}

// One file an agent reads, in a window of its own: read it, change it and save, or take it away. `remove` is left out for a file that holds several things.
export function openResourceFile({ kind, origin, path, status, remove }) {
  const label = KIND_BY_ID[kind];
  const fileName = path.split("/").at(-1);
  const markdown = MARKDOWN.test(fileName);
  let file = null;
  let view = markdown ? "formatted" : "plain";
  let editor = null;
  let baseline = "";

  const dirty = () => editor !== null && editor.value !== baseline;
  const leave = (after) => confirmAction({ title: "Leave without saving?", body: `What you changed in ${fileName} has not been saved.`, confirm: "Discard changes", tone: "danger" }).then((yes) => yes && after());
  // Unsaved text outlives a move to another page (⌘K, Back, Forward): `holdsWork` keeps the window open over it. A reload or a closed tab is the browser's to question.
  const dialog = openDialog({
    label: fileName, size: "file-view", holdsWork: dirty,
    canDismiss: () => {
      if (dirty()) leave(() => dialog.close());
      return !dirty();
    },
  });
  const warnUnsaved = (event) => dirty() && event.preventDefault();
  window.addEventListener("beforeunload", warnUnsaved);
  dialog.closed.then(() => window.removeEventListener("beforeunload", warnUnsaved));
  const bar = h("div", { class: "file-bar" });
  const scroll = h("div", { class: "file-scroll", tabindex: "0" });
  const picker = segmented(TEXT_VIEWS, (value) => {
    view = value;
    read();
  });
  const copy = iconButton("copy", "Copy the whole file", async () => (await copyText(file.text)) && toast(`Copied ${fileName}.`, "info"));
  const removeButton = remove && button({ label: "Remove", glyph: "trash", title: `Remove this ${label.one}. You are shown what changes first.`, onclick: async () => (await remove()) && dialog.close() });
  if (removeButton) removeButton.classList.add("caution");

  function load() {
    editor = null;
    bar.replaceChildren();
    scroll.classList.remove("editing");
    scroll.replaceChildren(...skeleton(4, "row"));
    api.file(path).then(
      (loaded) => {
        file = loaded;
        read();
      },
      (error) => scroll.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This could not be opened", body: error.message })),
    );
  }

  function read() {
    editor = null;
    const stats = readingStats(file.text);
    const size = markdown ? `${plural(stats.words, "word")} · about ${stats.minutes} min to read` : plural(file.text.split("\n").length, "line");
    bar.replaceChildren(...[h("span", { class: "dim", text: size }), h("span", { class: "spacer" }), markdown && picker.element, copy, button({ label: "Edit", glyph: "pencil", onclick: edit }), removeButton].filter(Boolean));
    picker.set(view);
    scroll.classList.remove("editing");
    scroll.replaceChildren(...(file.text.trim() === "" ? [h("p", { class: "dim", text: "This file is empty." })] : view === "formatted" ? formatted(file.text) : [h("pre", { class: "prompt-plain", text: file.text })]));
    scroll.scrollTop = 0;
  }

  function edit() {
    editor = h("textarea", { class: "file-editor", spellcheck: "false", autocapitalize: "off", autocomplete: "off", "aria-label": `Contents of ${fileName}` });
    editor.value = file.text;
    // Compared with what the box itself holds, since a browser may hand line endings back differently from how the file had them.
    baseline = editor.value;
    const save = button({ label: "Save", glyph: "check", tone: "primary", title: "Write these changes to the file (⌘S or Ctrl+S)", onclick: store });
    const note = h("span", { class: "file-editing" }, icon("pencil", 14), h("span", { text: "Editing · the file only changes when you save" }));
    let conflicted = false;
    save.disabled = true;

    async function store() {
      save.disabled = true;
      try {
        file = await api.saveFile({ path, text: editor.value, version: file.version });
      } catch (error) {
        // A 409 means something else wrote to the file since it was opened. Save stays off from then on, since taking the newer version here
        // would silently undo that other write, and Cancel fetches what the file holds now.
        if (error.status === 409) {
          conflicted = true;
          note.classList.add("conflict");
          note.replaceChildren(icon("alert", 14), h("span", { text: "Not saved: the file changed on disk. Copy what you need, then Cancel shows what it holds now." }));
        } else save.disabled = false;
        return toast(error.message);
      }
      toast(`Saved ${fileName}.`, "info");
      markStale();
      read();
    }

    editor.addEventListener("input", () => (save.disabled = conflicted || !dirty()));
    editor.addEventListener("keydown", (event) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      if (!save.disabled) store();
    });
    const back = () => (conflicted ? load() : read());
    bar.replaceChildren(note, h("span", { class: "spacer" }), button({ label: "Cancel", onclick: () => (dirty() ? leave(back) : back()) }), save);
    scroll.classList.add("editing");
    scroll.replaceChildren(editor);
    editor.focus({ preventScroll: true });
  }

  dialog.body.append(
    h(
      "header",
      { class: "file-head" },
      glyphTile(label.glyph, label.hue, 46),
      h("div", { class: "file-title" }, h("span", { class: "overline", text: `${label.label} · ${ORIGINS[origin].label}` }), h("h2", {}, fileName, status && pill(STATES[status].label, STATES[status].tone)), pathChip(path)),
      iconButton("close", "Close", () => dialog.dismiss()),
    ),
    bar,
    scroll,
  );
  load();
}
