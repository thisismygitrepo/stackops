import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { markStale } from "../../data.js";
import { confirmAction, openDialog } from "../../overlays.js";
import { button, copyChip, glyphTile, iconButton, notice, pill, segmented, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { KIND_BY_ID, ORIGINS, STATES } from "./health_model.js";
import { readingStats, renderPromptText } from "./prompts_text.js";

const MARKDOWN = /\.(md|mdc|markdown)$/i;
// The settings block some files open with. Read as prose it would turn into a heading, so it is shown as written above the text.
const FRONT_MATTER = /^---\r?\n([\s\S]*?)\r?\n---[ \t]*(?:\r?\n|$)/;

function formatted(text) {
  const front = text.match(FRONT_MATTER);
  return [front && h("pre", { class: "prompt-code file-front", title: "Settings at the top of this file", text: front[1] }), renderPromptText(front ? text.slice(front[0].length) : text, "")].filter(Boolean);
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
  const dialog = openDialog({
    label: fileName, size: "file-view",
    canDismiss: () => {
      if (dirty()) leave(() => dialog.close());
      return !dirty();
    },
  });
  const bar = h("div", { class: "file-bar" });
  const scroll = h("div", { class: "file-scroll", tabindex: "0" }, skeleton(4, "row"));
  const picker = segmented([["formatted", "Easy to read"], ["plain", "As written"]], (value) => {
    view = value;
    read();
  });
  const copy = iconButton("copy", "Copy the whole file", async () => {
    if (!navigator.clipboard) return toast("The browser only allows copying on localhost or HTTPS.");
    await navigator.clipboard.writeText(file.text);
    toast(`Copied ${fileName}.`, "info");
  });
  const removeButton = remove && button({ label: "Remove", glyph: "trash", title: `Remove this ${label.one}. You are shown what changes first.`, onclick: async () => (await remove()) && dialog.close() });
  if (removeButton) removeButton.classList.add("caution");

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
    save.disabled = true;

    async function store() {
      save.disabled = true;
      try {
        file = await api.saveFile({ path, text: editor.value, version: file.version });
      } catch (error) {
        save.disabled = false;
        return toast(error.message);
      }
      toast(`Saved ${fileName}.`, "info");
      markStale();
      read();
    }

    editor.addEventListener("input", () => (save.disabled = !dirty()));
    editor.addEventListener("keydown", (event) => {
      if (!(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== "s") return;
      event.preventDefault();
      if (!save.disabled) store();
    });
    bar.replaceChildren(
      h("span", { class: "file-editing" }, icon("pencil", 14), h("span", { text: "Editing · the file only changes when you save" })),
      h("span", { class: "spacer" }),
      button({ label: "Cancel", onclick: () => (dirty() ? leave(read) : read()) }),
      save,
    );
    scroll.classList.add("editing");
    scroll.replaceChildren(editor);
    editor.focus({ preventScroll: true });
  }

  dialog.body.append(
    h(
      "header",
      { class: "file-head" },
      glyphTile(label.glyph, label.hue, 46),
      h("div", { class: "file-title" }, h("span", { class: "overline", text: `${label.label} · ${ORIGINS[origin].label}` }), h("h2", {}, fileName, status && pill(STATES[status].label, STATES[status].tone)), copyChip(path, tildify(path, state.boot.home))),
      iconButton("close", "Close", () => dialog.dismiss()),
    ),
    bar,
    scroll,
  );
  api.file(path).then(
    (loaded) => {
      file = loaded;
      read();
    },
    (error) => scroll.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This could not be opened", body: error.message })),
  );
}
