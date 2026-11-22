import { h, toast } from "/assets/scripts/dom.js";
import { openPopover } from "../../overlays.js";
import { editButton } from "../../space_kit.js";
import { button, pathChip, pill } from "../../widgets.js";
import { humanize, plural } from "../../words.js";

const SOURCE_LABELS = { workspace: "This project", user: "Yours", library: "Built in", "custom-file": "Chosen file" };
const BLURBS = {
  workspace: "Shared with everyone who works in this project.",
  user: "Your own, on hand in every project.",
  library: "Comes with StackOps and is updated with it.",
};

const kindOf = (record) => record.source.split(":")[0];
export function sourceLabel(source) {
  const [kind, member] = source.split(":");
  const label = SOURCE_LABELS[kind] ?? humanize(kind);
  return member ? `${label} · ${member}` : label;
}
export const canChange = (record) => kindOf(record) !== "library";
// What the shared Edit control needs to open the file behind a place, or behind one prompt: both carry `source` and `path`.
export const editTarget = (record) => ({ title: `prompts · ${sourceLabel(record.source)}`, kind: "prompts", path: record.path });

// Makes the file with one example prompt in it. Runs out of sight and only opens the activity panel if it goes wrong.
export async function createPromptFile(activity, record) {
  const run = await activity.start({ title: "Create a prompts file", emoji: "📄", arguments: ["agents", "config", "init", "prompts", "--custom-path", record.path], interactive: false, reveal: false });
  const outcome = await run.done;
  if (outcome.exit_code !== 0) {
    activity.reveal(run.id);
    return false;
  }
  activity.remove(run.id);
  toast("Created the file with one example prompt for you to rewrite.", "info");
  return true;
}

export function openPromptFiles(anchor, { activity, sources, onCreate }) {
  const edit = (record) => {
    const control = editButton(activity, editTarget(record), { small: true });
    control.addEventListener("click", () => popover.close());
    return control;
  };
  const create = (record) => () => {
    popover.close();
    onCreate(record);
  };
  const popover = openPopover(
    anchor,
    h(
      "div",
      { class: "prompt-files" },
      h("h3", { text: "Where prompts are kept" }),
      h("p", { class: "dim", text: "Every prompt is a named piece of text in one of these files. Add one to a file and it shows up here." }),
      sources.map((record) =>
        h(
          "div",
          { class: "prompt-file" },
          h("div", { class: "prompt-file-head" }, h("strong", { text: sourceLabel(record.source) }), record.exists ? pill(plural(record.prompt_count, "prompt"), record.prompt_count ? "accent" : "") : pill("Not created yet", "warn")),
          h("p", { class: "dim", text: BLURBS[kindOf(record)] ?? "" }),
          pathChip(record.path),
          canChange(record) &&
            h(
              "div",
              { class: "prompt-file-actions" },
              record.exists ? edit(record) : button({ label: "Create this file", glyph: "plus", small: true, tone: "primary", onclick: create(record) }),
            ),
        ),
      ),
    ),
  );
  return popover;
}
