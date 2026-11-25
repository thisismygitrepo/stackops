import { h, icon, toast } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { replay } from "../../motion.js";
import { confirmAction } from "../../overlays.js";
import { backLink } from "../../space_kit.js";
import { button, callout, copyChip, emojiTile, notice, outputActions, segmented, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { explainScript } from "./scripts/explain.js";
import { BACK_LABEL, HASH, SCRIPTS, SCRIPTS_HASH, WIZARD_PATH } from "./words.js";

const TOOL_PATH = "devops config init-script";
const COMMAND = TOOL_PATH.split(" ");
const hostsOf = (addresses) => [...new Set(addresses.map((address) => new URL(address).host))].join(" and ");

// Whoever opens the tool with a script named lands on that script.
export function open(_context, { preset }) {
  const id = SCRIPTS.some((script) => script.id === preset?.which) ? preset.which : "";
  location.hash = id ? `${SCRIPTS_HASH}/${id}` : SCRIPTS_HASH;
}

// What a script would do, as a list read off its text (explain.js). Each row is a fact and, where it helps, the things it is about.
function effects(facts, tools) {
  const row = (glyph, title, items, extra) => h("li", {}, h("span", { class: "settings-script-glyph" }, icon(glyph, 15)), h("div", {}, h("strong", { text: title }), items?.length > 0 && h("div", { class: "settings-script-items" }, items), extra));
  const rows = [
    facts.fetched.length > 0 && row("download", `Downloads ${plural(facts.fetched.length, "script")} from ${hostsOf(facts.fetched)} and runs ${facts.fetched.length === 1 ? "it" : "them"}`, facts.fetched.map((address) => copyChip(address))),
    facts.pathFolders > 0 && row("folder", `Adds ${plural(facts.pathFolders, "folder")} to the program search path, where they are not on it already`),
    facts.loaded.length > 0 && row("report", `Loads ${plural(facts.loaded.length, "other file")}`, facts.loaded.map((path) => copyChip(path))),
    facts.commands.length > 0 && row("terminal", `Defines ${plural(facts.commands.length, "command")} for the terminal it runs in`, [h("span", { class: "settings-script-words", text: facts.commands.join("  ") })]),
    facts.switchedOn.length > 0 && row("bolt", `Switches on ${facts.switchedOn.join(", ")}, each where it is installed`),
    facts.endsWith &&
      row(
        "play", facts.startsWizard ? "Ends by starting the setup wizard" : `Ends by running ${facts.endsWith}`, [],
        facts.startsWizard && h("button", { class: "link", type: "button", text: "See what the wizard offers", onclick: () => tools.open(WIZARD_PATH) }),
      ),
  ].filter(Boolean);
  return rows.length > 0 ? h("ul", { class: "settings-script-effects" }, rows) : h("p", { class: "dim", text: "Nothing in this script was recognised. Its text below is what it does." });
}

// Home › Setup scripts, at #/home/scripts: the three scripts `devops config init-script` prints, each with what it would do and its
// whole text, before anything runs. A page and not a sheet: the text is long and is there to be read. Each script is read through the CLI.
export function createPart({ activity, tools }) {
  let chosen = SCRIPTS[0].id;
  let ticket = 0;
  const panel = h("div", { class: "settings-script" });
  const picker = segmented(SCRIPTS.map((script) => [script.id, script.title]), (id) => {
    if (id === chosen) return;
    chosen = id;
    history.replaceState(null, "", `${SCRIPTS_HASH}/${id}`);
    paint(true);
  });

  async function run(script, facts) {
    const sure = await confirmAction({
      title: `Run ${script.title.toLowerCase()}?`, confirm: "Run it",
      body: [
        facts.fetched.length > 0 && `It downloads ${plural(facts.fetched.length, "script")} from ${hostsOf(facts.fetched)} and runs ${facts.fetched.length === 1 ? "it" : "them"}.`,
        facts.commands.length > 0 && `It defines ${plural(facts.commands.length, "command")} for that one run.`,
        facts.startsWizard ? "Then it starts the setup wizard, which changes nothing until you tick what you want." : facts.endsWith && `Then it runs ${facts.endsWith}.`,
        "It runs in the activity panel, where you can watch it and stop it.",
      ].filter(Boolean).join(" "),
    });
    if (sure) activity.start({ title: script.title, emoji: script.emoji, arguments: [...COMMAND, script.id, "--run"], interactive: true, reveal: true, wide: true }).catch((error) => toast(error.message));
  }

  async function paint(moved) {
    const script = SCRIPTS.find((candidate) => candidate.id === chosen);
    const mine = (ticket += 1);
    picker.set(chosen);
    const head = h("header", {}, emojiTile(script.emoji, `${TOOL_PATH} ${script.id}`, 52), h("div", {}, h("h2", { text: script.title }), h("p", { text: script.about })));
    if (moved) panel.replaceChildren(head, ...skeleton(4, "row"));
    let text;
    try {
      ({ text } = await query([...COMMAND, script.id]));
    } catch (error) {
      if (mine !== ticket) return;
      panel.replaceChildren(head, notice({ glyph: "alert", tone: "bad", title: "This script could not be read", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => paint(true) }) }));
      return;
    }
    if (mine !== ticket) return;
    const facts = explainScript(text);
    panel.replaceChildren(
      ...[
        head,
        !script.runnable && callout({ tone: "", title: "A terminal loads this by itself", text: "Once your shell profile has StackOps' line, every new terminal runs this script. Running it from here would only set up a shell that ends with the run. Shell profile is where that line is put in.", href: "#/sessions/shell-profile" }),
        h("section", {}, h("h3", { text: "What it would do" }), effects(facts, tools)),
        h(
          "section",
          {},
          h("div", { class: "settings-script-bar" }, h("h3", { text: `The script · ${plural(facts.lineCount, "line")}` }), h("span", { class: "spacer" }), outputActions(() => text, `stackops-${script.id}`)),
          h("pre", { class: "script-code settings-script-text", tabindex: "0" }, text.replace(/\n$/, "").split("\n").map((line) => h("span", { text: line }))),
        ),
        h(
          "footer",
          {},
          h("span", { class: "dim", text: "From a terminal" }),
          copyChip(`${TOOL_PATH} ${script.id}${script.runnable ? " --run" : ""}`),
          h("span", { class: "spacer" }),
          script.runnable && button({ label: "Run it", glyph: "play", tone: "primary", title: "Asks first, then runs in the activity panel", onclick: () => run(script, facts) }),
        ),
      ].filter(Boolean),
    );
    if (moved) replay(panel, "settings-swap");
  }

  const element = h(
    "div",
    { class: "settings-scripts", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, backLink(HASH, BACK_LABEL), h("h1", { text: "Setup scripts" }), h("p", { text: "Three scripts StackOps ships for a new terminal or a new machine. Read what each would do. Nothing runs until you say so." })),
      h("div", { class: "view-actions" }, button({ label: "All options", glyph: "sliders", title: "The command's own form", onclick: () => tools.open(TOOL_PATH, { plain: true, preset: { which: chosen } }) })),
    ),
    h("div", { class: "table-bar" }, picker.element),
    panel,
  );

  return {
    element,
    show(rest) {
      const asked = SCRIPTS.some((script) => script.id === rest[0]) ? rest[0] : chosen;
      const moved = asked !== chosen || !panel.hasChildNodes();
      chosen = asked;
      paint(moved);
    },
  };
}
