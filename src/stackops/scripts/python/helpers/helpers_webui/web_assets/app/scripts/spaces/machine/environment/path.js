import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { copyText, iconButton, pill } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { PROGRAM_LIMIT, UNUSABLE } from "./words.js";

// The Program search path tab: the folders in lookup order. A folder opens to list its programs, and a search for a program shows the folders
// that hold a match with the matches under them, so it answers where a command comes from.
export function pathTab({ entries, winner }, repaint) {
  const opened = new Set();
  const unusable = entries.filter((entry) => entry.state !== "directory").length;
  const duplicates = entries.filter((entry) => entry.duplicateOf !== null).length;
  const shadowing = entries.filter((entry) => entry.duplicateOf === null && entry.shadowed.size > 0);
  const shadowedTotal = shadowing.reduce((sum, entry) => sum + entry.shadowed.size, 0);
  const positionOf = (index) => index + 1;

  function programPill(entry, command) {
    if (!entry.shadowed.has(command)) return h("span", { class: "env-program", title: "This folder is where the name is found", text: command });
    const first = entries[winner.get(command)];
    return h("span", { class: "env-program shadowed", title: `Not reached. Folder ${positionOf(first.index)} comes first and holds the same name: ${first.path}` }, h("span", { text: command }), h("b", { text: `→ ${positionOf(first.index)}` }));
  }

  function entryRow(entry, terms) {
    const matching = terms.length > 0 ? entry.commands.filter((command) => terms.every((term) => command.toLowerCase().includes(term))) : [];
    const open = opened.has(entry.index);
    const shown = matching.length > 0 ? matching : open ? entry.commands : [];
    const shadowedCount = entry.duplicateOf === null ? entry.shadowed.size : 0;
    const standing =
      entry.duplicateOf !== null ? pill(`Same as ${positionOf(entry.duplicateOf)}`, "warn") : entry.state !== "directory" ? pill(UNUSABLE[entry.state], "warn") : null;
    const copy = iconButton("copy", "Copy the folder's path", async () => {
      if (!(await copyText(entry.path))) return;
      copy.replaceChildren(icon("check", 16));
      setTimeout(() => copy.replaceChildren(icon("copy", 16)), 1200);
    });
    const toggle = h(
      "button",
      {
        class: "env-entry-toggle", type: "button", "aria-expanded": String(open), disabled: entry.commands.length === 0,
        title: entry.commands.length === 0 ? "There are no programs to list here" : open ? "Hide its programs" : "List its programs",
        onclick: () => {
          if (!opened.delete(entry.index)) opened.add(entry.index);
          repaint();
        },
      },
      h("span", { class: "env-order", text: String(positionOf(entry.index)) }),
      h("code", { title: entry.path, text: tildify(entry.path, state.boot.home) }),
      standing,
      h("span", { class: "spacer" }),
      h("span", { class: "env-entry-count", text: [plural(entry.commands.length, "program"), shadowedCount > 0 && `${shadowedCount.toLocaleString()} shadowed`].filter(Boolean).join(" · ") }),
      icon("chevron", 13),
    );
    return h(
      "li",
      { class: `env-entry${open ? " open" : ""}${entry.duplicateOf !== null || entry.state !== "directory" ? " unusable" : ""}` },
      h("div", { class: "env-entry-head" }, toggle, copy),
      shown.length > 0 &&
        h(
          "div",
          { class: "env-programs" },
          shown.slice(0, PROGRAM_LIMIT).map((command) => programPill(entry, command)),
          shown.length > PROGRAM_LIMIT && h("span", { class: "dim", text: `and ${(shown.length - PROGRAM_LIMIT).toLocaleString()} more. Search to narrow them.` }),
        ),
    );
  }

  return {
    unit: "folder",
    total: entries.length,
    placeholder: "Find a program or a folder",
    emptyText: "No folder or program matches",
    tiles: [
      { glyph: "folder", hue: 252, label: "Folders", value: entries.length, note: "searched from the top" },
      { glyph: "terminal", hue: 165, label: "Programs", value: winner.size, note: "names that can be run" },
      { glyph: "eye", hue: 290, label: "Shadowed", value: shadowedTotal, note: shadowedTotal > 0 ? "an earlier folder has the name" : "no name is hidden" },
      { glyph: "alert", hue: 20, label: "Not usable", value: unusable + duplicates, note: unusable + duplicates > 0 ? `${unusable} cannot be searched · ${duplicates} listed twice` : "every folder counts" },
    ],
    chips: [
      { key: ":unusable", label: "Cannot be searched", count: unusable },
      { key: ":duplicate", label: "Listed twice", count: duplicates },
      { key: ":shadowing", label: "Has shadowed programs", count: shadowing.length },
    ].filter((chip) => chip.count > 0),
    note: [h("span", { text: "Folders are searched from the top, and the first one that holds a program wins. Open a folder to list its programs, or search for a program to see which folder it comes from." })],
    rows(terms, active) {
      return entries
        .filter(
          (entry) =>
            (!active.has(":unusable") || entry.state !== "directory") &&
            (!active.has(":duplicate") || entry.duplicateOf !== null) &&
            (!active.has(":shadowing") || (entry.duplicateOf === null && entry.shadowed.size > 0)) &&
            (terms.every((term) => entry.pathText.includes(term)) || entry.commands.some((command) => terms.every((term) => command.toLowerCase().includes(term)))),
        )
        .map((entry) => entryRow(entry, terms));
    },
  };
}
