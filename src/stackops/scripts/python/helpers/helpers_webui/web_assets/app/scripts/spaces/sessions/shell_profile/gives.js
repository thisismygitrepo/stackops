import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { button, glyphTile, sectionHead, segmented } from "../../../widgets.js";
import { friendlyText } from "../../../words.js";
import { EXTRAS, SHELLS, listOf } from "./words.js";

// Shells that load the same setup file get the same things, so they are shown as one.
function groupsOf(shells) {
  const groups = new Map();
  for (const shell of shells) {
    const key = shell.files.map((file) => file.loads).join("\n");
    groups.set(key, [...(groups.get(key) ?? []), shell]);
  }
  return [...groups.values()];
}

// The short commands as they would be typed. A command that is one of StackOps' own tools also says what that tool is for.
function terminal(shell, title) {
  const about = (alias) => {
    const node = state.nodes.get(alias.runs);
    return node ? friendlyText(node.summary) : "";
  };
  return h(
    "div",
    { class: "shellprof-term" },
    h("div", { class: "shellprof-term-bar" }, h("span", { class: "shellprof-dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")), h("span", { text: title })),
    h(
      "ul",
      { class: "shellprof-term-body" },
      h("li", { class: "shellprof-term-note", text: "# type the short name, get the command" }),
      shell.aliases.map((alias) => h("li", {}, h("b", { "aria-hidden": "true", text: "❯" }), h("strong", { text: alias.name }), h("code", { text: alias.runs }), h("em", { text: about(alias) }))),
    ),
  );
}

function extraRow(extra, install) {
  const words = EXTRAS[extra.key];
  const used = extra.programs.find((program) => program.installed);
  const names = extra.programs.map((program) => program.name);
  const standing =
    names.length === 0
      ? null
      : used
        ? h("span", { class: "shellprof-fact good" }, icon("check", 13), h("span", { text: `Uses ${used.name}` }))
        : [h("span", { class: "shellprof-fact warn" }, icon("alert", 13), h("span", { text: `Needs ${listOf(names)}, which ${names.length > 1 ? "are" : "is"} not installed` })), button({ label: `Install ${names[0]}`, glyph: "download", small: true, onclick: () => install(names[0], names[0]) })];
  return h("li", { class: "shellprof-extra" }, glyphTile(words.glyph, words.hue, 38), h("div", { class: "shellprof-extra-text" }, h("strong", { text: words.title }), h("p", { text: words.text }), standing && h("div", { class: "shellprof-extra-state" }, standing)));
}

// What a terminal gains from the setup, read from the setup file itself: its short commands, and its parts with the program each one needs.
// With more than one setup on the machine (Nushell beside zsh and bash) a control picks which one to show.
export function createGives({ install }) {
  const element = h("section", { class: "block shellprof-gives", hidden: true });
  let picked = "";

  function paint(shells) {
    const groups = groupsOf(shells);
    element.hidden = groups.length === 0;
    if (groups.length === 0) return;
    const group = groups.find((members) => members[0].id === picked) ?? groups[0];
    const labelOf = (members) => members.map((shell) => SHELLS[shell.id].name).join(" and ");
    const pick = (id) => {
      picked = id;
      paint(shells);
    };
    const picker = groups.length > 1 ? segmented(groups.map((members) => [members[0].id, labelOf(members)]), pick) : null;
    picker?.set(group[0].id);
    const shell = group[0];
    const extras = shell.extras.filter((extra) => EXTRAS[extra.key]);
    element.replaceChildren(
      sectionHead(`What a terminal gains in ${labelOf(group)}`, h("span", { class: "spacer" }), picker?.element),
      h("div", { class: "shellprof-gives-grid" }, shell.aliases.length > 0 && terminal(shell, labelOf(group)), h("ul", { class: "shellprof-extras" }, extras.map((extra) => extraRow(extra, install)))),
    );
  }

  return { element, paint };
}
