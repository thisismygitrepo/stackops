import { h, icon } from "/assets/scripts/dom.js";
import { editButton } from "../../../space_kit.js";
import { button, emojiTile, keyValue, pathChip, pill } from "../../../widgets.js";
import { formatBytes, relativeTime } from "../../../words.js";
import { FILES, SCHEMA_WORDS, standingOf, tidyProblem } from "../words.js";

const REASONS = {
  unavailable: "The working folder is not part of a project, so there is no place for this file. Choose a project folder at the top of the page.",
  blocked: "Something that is not a file sits at this path. Move it away and the file can be created.",
};

// One settings file. The card is drawn again only when what it shows changed, so a check that comes in for another file leaves it alone, and
// the keyboard stays on the button it was on. `handlers` are the page's: `onCreate`, `onSchema`, `onCheck` and `onExample`, each given the file.
export function fileCard(kind, { activity, handlers }) {
  const words = FILES[kind];
  const element = h("article", { class: "settings-file", "data-kind": kind, tabindex: "-1" });
  let drawn = "";

  const act = (name, control) => {
    control.dataset.action = name;
    return control;
  };

  function paint(file, check, busy) {
    const stamp = JSON.stringify([file, check ?? null, busy]);
    if (stamp === drawn) return;
    drawn = stamp;
    const standing = standingOf(file, check);
    const held = element.contains(document.activeElement) ? document.activeElement.dataset.action : null;
    const problem = standing.id === "problem" || standing.id === "unchecked" ? tidyProblem(check.problem, file.path) : REASONS[standing.id];
    const schemaFix =
      file.exists && file.schema !== "current" &&
      act("schema", h("button", { class: "link", type: "button", text: file.schema === "missing" ? "Put it there" : "Bring it up to date", onclick: () => handlers.onSchema(file) }));
    const example = act("example", button({ label: file.exists ? "Example" : "See the example", glyph: "eye", small: true, title: "What StackOps ships as a starting point for this file", onclick: () => handlers.onExample(file) }));
    const actions = file.exists
      ? [
          act("edit", editButton(activity, { title: words.title, kind }, { small: true })),
          act("check", button({ label: "Check", glyph: "check", small: true, title: "Runs the check StackOps runs before it uses this file", onclick: () => handlers.onCheck(file) })),
          example,
          h("span", { class: "spacer" }),
          h("a", { class: "settings-file-used", href: words.used.href }, h("span", { text: words.used.label }), icon("arrow", 13)),
        ]
      : [
          file.available && !file.blocked && act("create", button({ label: "Create it", glyph: "plus", small: true, tone: "primary", title: "Starts the file from the example StackOps ships, with its schema beside it", onclick: () => handlers.onCreate(file) })),
          example,
        ];
    element.className = `settings-file ${standing.id}${busy ? " working" : ""}`;
    element.replaceChildren(
      ...[
        h(
          "header",
          {},
          emojiTile(words.emoji, kind, 44),
          h("div", { class: "settings-file-title" }, h("h3", { text: words.title }), h("span", { text: `${file.format.toUpperCase()}${file.private ? " · only you can read it" : ""}` })),
          standing.id === "checking" ? h("span", { class: "pill settings-file-checking" }, h("i", { class: "ring" }), standing.label) : pill(standing.label, standing.tone),
        ),
        h("p", { class: "settings-file-about", text: words.about }),
        file.available &&
          keyValue([
            ["Where", pathChip(file.path)],
            ["On disk", file.exists && `${formatBytes(file.size)} · changed ${relativeTime(file.modified_at)}`],
            ["Schema", file.exists && h("span", { class: "settings-file-schema", title: "The schema is the set of rules this file is checked against. Beside the file, an editor reads it and checks as you type." }, SCHEMA_WORDS[file.schema], schemaFix)],
          ]),
        problem && h("div", { class: `settings-file-problem ${standing.tone}` }, icon(standing.id === "unavailable" ? "info" : "alert", 15), h("p", { text: problem })),
        h("footer", {}, actions),
      ].filter(Boolean),
    );
    for (const control of element.querySelectorAll("footer button, .settings-file-schema button")) control.disabled = busy;
    if (held) element.querySelector(`[data-action="${held}"]`)?.focus({ preventScroll: true });
  }

  return { element, paint };
}
