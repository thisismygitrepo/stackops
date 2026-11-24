import { h, icon } from "/assets/scripts/dom.js";
import { plural } from "../../../words.js";

// The four ways a packaged file stands against its copy here, in the order the bar draws them.
export const PARTS = [
  ["same", "match", "Matches what StackOps ships"],
  ["changed", "changed here", "Changed on this machine"],
  ["missing", "not copied", "Not copied to this machine yet"],
  ["extra", "only here", "Only on this machine"],
];
export const differsBy = (group) => group.changed + group.missing + group.extra;
export const totalOf = (groups, key) => groups.reduce((sum, group) => sum + group[key], 0);

// A bar split by how the files stand. A part with no files takes no room.
export function standingBar(counts) {
  return h("div", { class: "settings-bar", role: "img", "aria-label": PARTS.filter(([key]) => counts[key] > 0).map(([key, word]) => `${counts[key]} ${word}`).join(", ") }, PARTS.filter(([key]) => counts[key] > 0).map(([key]) => h("i", { class: key, style: `flex-grow:${counts[key]}` })));
}

export const countsLine = (counts) => PARTS.filter(([key]) => key !== "same" && counts[key] > 0).map(([key, word]) => `${counts[key]} ${word}`).join(" · ");

// One folder of the packaged settings. A folder whose copy matches is a plain row; one that differs opens to the files that do, by how they
// differ. The server sends a limited number of names, and the row says how many more there are. `opened` keeps which rows are open.
export function folderRow(group, opened) {
  const name = group.name || "Top level";
  const differs = differsBy(group);
  const head = [
    h("strong", { text: name }),
    standingBar(group),
    h("span", { class: "settings-assets-counts", text: differs === 0 ? `${plural(group.offered, "file")}, all match` : `${plural(group.offered + group.extra, "file")} · ${countsLine(group)}` }),
  ];
  if (differs === 0) return h("div", { class: "settings-assets-row same" }, head, h("span", { class: "settings-assets-caret" }));
  const lists = PARTS.filter(([key]) => key !== "same" && group[key] > 0).map(([key, , title]) => {
    const names = group[`${key}_names`];
    return h(
      "div",
      { class: `settings-assets-names ${key}` },
      h("h4", { text: `${title} · ${group[key]}` }),
      h("ul", {}, names.map((path) => h("li", { text: path })), group[key] > names.length && h("li", { class: "dim", text: `and ${plural(group[key] - names.length, "more file")}` })),
    );
  });
  const row = h("details", { class: "settings-assets-row differs", open: opened.has(group.name) }, h("summary", {}, head, h("span", { class: "settings-assets-caret" }, icon("down", 14))), h("div", { class: "settings-assets-inside" }, lists));
  row.addEventListener("toggle", () => (row.open ? opened.add(group.name) : opened.delete(group.name)));
  return row;
}
