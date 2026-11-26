import { h, icon } from "/assets/scripts/dom.js";
import { button, copyChip, copyText, glyphTile, pathChip, pill } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { SHELLS, STANDINGS, fileName, loginLabel, manualText, shortPath, standingOf, standingText } from "./words.js";

// A shell's badge: the sign its prompt ends in.
const shellTile = (shell, size) => h("span", { class: "tile shellprof-sign", style: `--hue:${SHELLS[shell.id].hue};--size:${size}px`, text: SHELLS[shell.id].sign });

// How many parts of the setup have a program to run them. A part that needs no program always counts.
const readyExtras = (shell) => shell.extras.filter((extra) => extra.programs.length === 0 || extra.programs.some((program) => program.installed)).length;

const fact = (tone, glyph, text) => h("span", { class: `shellprof-fact ${tone}` }, icon(glyph, 13), h("span", { text }));

function fileFact(file) {
  if (file.problem) return fact("bad", "alert", "Can't be read");
  if (file.line_present) return fact("good", "check", "Has StackOps' line");
  if (file.old_line_present) return fact("warn", "alert", "Has an old StackOps line");
  return file.exists ? fact("", "close", "No StackOps line") : fact("", "plus", "Not created yet");
}

async function copied(control, text) {
  if (!(await copyText(text, "Select the line under the card and copy it by hand."))) return;
  const label = control.querySelector("span");
  label.textContent = "Copied";
  setTimeout(() => (label.textContent = "Copy the line"), 1400);
}

// A small drawing of the profile: the person's own lines, which are never read, and the one line StackOps adds at the end.
function sheet(shell) {
  const lines = shell.files.filter((file) => file.line_present).length;
  const kind = lines === shell.files.length ? "has-line" : shell.files.some((file) => file.exists) ? "no-line" : "no-file";
  return h("span", { class: `shellprof-sheet ${kind}`, "aria-hidden": "true" }, h("i"), h("i"), h("i"), h("i", { class: "mine" }));
}

function chain(shell) {
  const linked = shell.files.every((file) => file.line_present);
  const setupFact = !shell.setup_in_place ? fact(linked ? "bad" : "", linked ? "alert" : "plus", linked ? "Missing" : "Not copied yet") : shell.setup_current ? fact("good", "check", "In place") : fact("warn", "alert", "Not the shipped one");
  const ready = readyExtras(shell);
  const arrow = (label, on) => h("span", { class: `shellprof-arrow${on ? " on" : ""}`, "aria-hidden": "true" }, h("em", { text: label }), icon("arrow", 15));
  return h(
    "div",
    { class: "shellprof-chain" },
    h(
      "div",
      { class: "shellprof-step" },
      sheet(shell),
      h("div", { class: "shellprof-step-text" }, h("span", { class: "overline", text: shell.files.length > 1 ? "Its profile files" : "Its profile" }), shell.files.flatMap((file) => [pathChip(file.path), fileFact(file), file.link_target && h("span", { class: "shellprof-link dim" }, "A link to ", pathChip(file.link_target))])),
    ),
    arrow("loads", linked),
    h(
      "div",
      { class: "shellprof-step" },
      glyphTile("report", 252, 40),
      h("div", { class: "shellprof-step-text" }, h("span", { class: "overline", text: shell.files.length > 1 ? "StackOps' setup files" : "StackOps' setup file" }), shell.files.map((file) => pathChip(file.loads)), setupFact),
    ),
    arrow("gives", linked && shell.setup_in_place),
    h(
      "div",
      { class: "shellprof-step" },
      glyphTile("terminal", 165, 40),
      h(
        "div",
        { class: "shellprof-step-text" },
        h("span", { class: "overline", text: "A terminal" }),
        h("strong", { text: plural(shell.aliases.length, "short command") }),
        ready === shell.extras.length ? fact("good", "check", `All ${shell.extras.length} extras are ready`) : fact("warn", "alert", `${ready} of ${shell.extras.length} extras are ready`),
      ),
    ),
  );
}

// One shell that can be set up on this machine: where it stands, the chain from its profile to what a terminal gets, and what can be done.
// `actions` is `{ setUp(shell), copyFiles(shell), openFile(file), askAbout(file), busy }`; `loginName` is what the login shell is called, for a shell the
// command does not act on.
export function shellCard(shell, { featured, loginName, actions }) {
  const standing = standingOf(shell);
  const { label, tone, due } = STANDINGS[standing];
  const manual = shell.route === "manual";
  const setUp = !manual && standing !== "unreadable" && button({ label: due ? "Set up" : "Set up again", glyph: due ? "play" : "refresh", tone: due ? "primary" : "plain", title: due ? undefined : "Puts a fresh copy of StackOps' settings and scripts in place", onclick: () => actions.setUp(shell) });
  if (setUp) setUp.disabled = actions.busy;
  // A shell the command does not act on gets its line by hand, so the line is one press away from the clipboard.
  const copyLine = manual && !shell.files[0].line_present && button({ label: "Copy the line", glyph: "copy", onclick: () => copied(copyLine, shell.files[0].line) });
  const copyFiles =
    manual && (!shell.setup_in_place || !shell.setup_current || standing === "old") &&
    button({ label: "Copy StackOps' files", glyph: "download", title: "Puts a fresh copy of StackOps' settings and scripts in place, and adds no line to a profile", onclick: () => actions.copyFiles(shell) });
  if (copyFiles) copyFiles.disabled = actions.busy;
  const openers = shell.files.flatMap((file) => [
    actions.askAbout(file),
    button({ label: shell.files.length > 1 ? `Open ${fileName(file.path)}` : "Open in editor", glyph: "pencil", title: `Opens ${shortPath(file.path)} in a text editor inside the activity panel`, onclick: () => actions.openFile(file) }),
  ]);
  return h(
    "article",
    { class: `shellprof-card ${tone}${featured ? " featured" : ""}`, "data-shell": shell.id },
    h(
      "header",
      { class: "shellprof-head" },
      shellTile(shell, featured ? 56 : 44),
      h(
        "div",
        { class: "shellprof-title" },
        h("h2", {}, h("span", { text: SHELLS[shell.id].name }), shell.login && pill(loginLabel(), "accent"), pill(label, tone)),
        h("p", { text: standingText(shell, standing) }),
      ),
      h("div", { class: "shellprof-actions" }, setUp, copyLine, copyFiles, openers),
    ),
    manual && h("p", { class: "shellprof-manual" }, icon("info", 15), h("span", { text: manualText(shell, loginName) })),
    chain(shell),
    h(
      "footer",
      { class: "shellprof-foot" },
      h("div", {}, h("span", { class: "overline", text: shell.files.length > 1 ? "The lines" : "The line" }), shell.files.map((file) => copyChip(file.line))),
      shell.reload_command && h("div", {}, h("span", { class: "overline", text: "To load it in a terminal that is already open" }), copyChip(shell.reload_command)),
    ),
  );
}

// A shell that cannot be set up here, greyed out with the reason and, where the catalog has it, the way to get it.
export function blockedRow(shell, { install }) {
  const standing = standingOf(shell);
  const { name, app } = SHELLS[shell.id];
  return h(
    "div",
    { class: "shellprof-row", "data-shell": shell.id },
    shellTile(shell, 38),
    h("div", { class: "shellprof-title" }, h("h3", {}, h("span", { text: name }), pill(STANDINGS[standing].label, "")), h("p", { text: standingText(shell, standing) })),
    standing === "not_installed" && app && button({ label: `Install ${name}`, glyph: "download", small: true, onclick: () => install(app, name) }),
  );
}
