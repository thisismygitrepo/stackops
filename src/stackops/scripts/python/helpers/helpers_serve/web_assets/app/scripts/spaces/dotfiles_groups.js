import { h, icon } from "/assets/scripts/dom.js";
import { dataTable, toneOf } from "../result_view.js";
import { button, pill } from "../widgets.js";

// The verdicts the collect command acts on; every other one is already handled or deliberately left alone.
export const COLLECT_WORDS = { collect: "Not collected yet", linked: "Linked, not on your list", stored: "Stored, not on this machine" };

// One fold per group, because a group is what the sync and collect commands take. Folded on arrival: the head already says where a group stands.
// `opened` holds the names of the groups left open, so the list can be drawn again, after a refresh or a keystroke in the filter, as it was.
function fold(name, pills, actions, rows, opened) {
  return h(
    "details",
    { class: "fold", open: opened.has(name), ontoggle: (event) => opened[event.target.open ? "add" : "delete"](name) },
    h("summary", {}, icon("chevron", 13), h("span", { text: name }), h("b", { text: String(rows.length) }), pills, h("span", { class: "spacer" }), actions),
    dataTable(rows),
  );
}

export function managedGroups(entries, onSync, opened) {
  return [...Map.groupBy(entries, (entry) => entry.program)].map(([name, files]) =>
    fold(
      name,
      [...new Set(files.map((file) => file.status))].map((status) => pill(status, toneOf(status))),
      [
        button({ label: "Save", glyph: "up", small: true, title: "Save this group from this machine", onclick: () => onSync("up", name) }),
        button({ label: "Apply", glyph: "download", small: true, title: "Apply this group to this machine", onclick: () => onSync("down", name) }),
      ],
      files.map((file) => ({ file: file.file_name, status: file.status, method: file.method, location: file.default_path, stored_at: file.managed_path })),
      opened,
    ),
  );
}

export function foundGroups(plans, onCollect, opened) {
  return [...Map.groupBy(plans, (plan) => plan.group)].map(([name, files]) =>
    fold(
      name,
      [],
      button({ label: "Collect", glyph: "plus", small: true, title: "Keep this group's files in your dotfiles folder", onclick: () => onCollect(name) }),
      files.map((file) => ({ file: file.name, status: COLLECT_WORDS[file.verdict], location: file.original_path, will_be_kept_at: file.managed_path })),
      opened,
    ),
  );
}
