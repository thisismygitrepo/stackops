import { h, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { editButton } from "../../space_kit.js";
import { button, glyphTile, pathChip, pill } from "../../widgets.js";
import { formatBytes, plural, relativeTime } from "../../words.js";
import { FILE_BLURBS, fileTitle, standingOf } from "./file_words.js";
import { busyButton, mark } from "./tools_kit.js";
import { kindOf } from "./words.js";

const editTarget = (file) => ({ title: "the vault file", kind: "secrets", path: file.path });

// One line of a file's checklist: a mark, what was checked, what that means, and the one thing to do about it.
function checkRow(tone, title, detail, action) {
  return h("li", { class: `vault-file-check ${tone}` }, mark(tone), h("div", { class: "vault-file-check-text" }, h("strong", { text: title }), detail && h("p", { text: detail })), action);
}

// What a check found wrong: which login and secret, what is wrong with it, and the checker's own sentence for someone who wants it.
function findingBlock(finding, activity, file) {
  return h(
    "div",
    { class: "vault-file-finding" },
    finding.where && h("span", { class: "vault-file-where", text: finding.where }),
    h("p", { text: finding.what }),
    finding.said && finding.said !== finding.what && h("details", {}, h("summary", { text: "The check's own words" }), h("code", { text: finding.said })),
    editButton(activity, editTarget(file), { label: "Open the file to repair it", small: true }),
  );
}

function checklist({ file, check, activity, actions }) {
  const held = file.holds;
  const due = held.rotation.filter((row) => row.state === "due").length;
  const fullCheck = !check
    ? checkRow("busy", "Running the full check", "Every field against the vault's schema. It takes a second or two.")
    : check.verdict === "valid"
      ? checkRow("good", "Passes the full check", "Every field matches the vault's schema.")
      : check.verdict === "invalid"
        ? h("li", { class: "vault-file-check bad" }, mark("bad"), h("div", { class: "vault-file-check-text" }, h("strong", { text: "Fails the full check" }), findingBlock(check.finding, activity, file)))
        : checkRow("note", "The full check could not run", check.trouble, busyButton({ label: "Try again", small: true }, () => actions.recheck(file)));
  return h(
    "ul",
    { class: "vault-file-checks" },
    checkRow("good", "Reads as a vault file", `${plural(held.logins, "login")}, ${plural(held.secrets, "secret")} and ${plural(held.values, "value")} found.`),
    held.untouched && checkRow("note", "It still holds the example logins", "They came with the new file and carry placeholder values. Replace them with your own on the Vault page.", button({ label: "Go to the logins", small: true, onclick: actions.showLogins })),
    fullCheck,
    file.private
      ? checkRow("good", "Only you can read it", "No other account on this machine can open the file.")
      : checkRow("warn", "Other accounts on this machine can read it", "The file's permissions let more than its owner open it.", busyButton({ label: "Make it private", small: true }, () => actions.protect(file))),
    file.schema === "current"
      ? checkRow("good", "Its schema file is beside it", "A text editor uses it to check the vault file as you type.")
      : checkRow(
          "note", file.schema === "missing" ? "Its schema file is missing" : "Its schema file is from another version of StackOps",
          "The vault works without it. A text editor uses it to check the vault file as you type.",
          busyButton({ label: file.schema === "missing" ? "Add it" : "Update it", small: true }, () => actions.schema(file)),
        ),
    held.unloadable_names > 0 && checkRow(
      "warn", `${plural(held.unloadable_names, "value name")} cannot be loaded into a terminal`,
      "A value loads as an environment variable, and its name must be letters, digits and underscores that do not start with a digit. Rename it on the Vault page.",
    ),
    held.repeated_names > 0 && checkRow(
      "note", `${plural(held.repeated_names, "value name")} repeated across secrets`,
      "Fine while secrets are loaded one at a time. Loading several at once stops when two of them give one name different values.",
    ),
    due > 0 && checkRow("warn", `${plural(due, "secret")} due for replacement`, "By the dates and intervals the secrets record themselves.", button({ label: "See which", small: true, onclick: actions.showDue })),
  );
}

// One vault file as a card: whose it is, how it stands, and either its checklist, what is wrong with it, or the one step that creates it.
export function fileCard({ file, check, starter, activity, actions }) {
  const standing = standingOf(file, check);
  const shown = tildify(file.path, state.boot.home);
  const head = h(
    "header",
    {},
    glyphTile(kindOf(file.name) === "user" ? "key" : "folder", kindOf(file.name) === "user" ? 252 : 200, 42),
    h("div", { class: "vault-file-title" }, h("span", { class: "overline", text: FILE_BLURBS[kindOf(file.name)] }), h("h3", { text: fileTitle(file.name) })),
    pill(standing.label, standing.tone === "idle" ? "" : standing.tone),
  );
  if (!file.exists) {
    const examples = starter.length > 0 ? `${plural(starter.length, "example login")} (${starter.join(", ")}) to replace with your own` : "an example to replace with your own";
    return h(
      "article",
      { class: "vault-file-card missing", "data-source": file.name },
      head,
      h("p", { class: "vault-file-lead", text: `Creating it writes ${shown} with ${examples}, and the schema file beside it. Only you can read the new file.` }),
      h("footer", {}, busyButton({ label: "Create this vault file", glyph: "plus", tone: "primary" }, () => actions.create(file))),
    );
  }
  return h(
    "article",
    { class: `vault-file-card ${standing.tone}`, "data-source": file.name },
    head,
    file.finding ? findingBlock(file.finding, activity, file) : checklist({ file, check, activity, actions }),
    h(
      "footer",
      {},
      h("span", { class: "dim", text: `${formatBytes(file.bytes)} · changed ${relativeTime(file.modified)}` }),
      pathChip(file.path),
      h("span", { class: "spacer" }),
      !file.finding && editButton(activity, editTarget(file), { label: "Open the file", small: true }),
    ),
  );
}
