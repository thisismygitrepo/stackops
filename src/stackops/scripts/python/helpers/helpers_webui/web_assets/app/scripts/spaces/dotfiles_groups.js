import { h, icon } from "/assets/scripts/dom.js";
import { dataTable, toneOf } from "../result_view.js";
import { button, pathChip, pill } from "../widgets.js";

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

// A group with one file listed has nothing to unfold: the row says what the table inside a fold would have.
function single(name, file, status, method, from, to, actions) {
  return h(
    "div",
    { class: "fold-single" },
    h("strong", { text: name }),
    file !== name && h("span", { class: "dim", text: file }),
    pill(status, toneOf(status)),
    method && pill(method),
    h("span", { class: "single-paths" }, pathChip(from), icon("arrow", 12), pathChip(to)),
    h("span", { class: "spacer" }),
    actions,
  );
}

export function managedGroups(entries, onSync, opened) {
  return [...Map.groupBy(entries, (entry) => entry.program)].map(([name, files]) => {
    const actions = [
      button({ label: "Save", glyph: "up", small: true, title: "Save this group from this machine", onclick: () => onSync("up", name) }),
      button({ label: "Apply", glyph: "download", small: true, title: "Apply this group to this machine", onclick: () => onSync("down", name) }),
    ];
    const [only] = files;
    if (files.length === 1) return single(name, only.file_name, only.status, only.method, only.default_path, only.managed_path, actions);
    return fold(
      name,
      [...new Set(files.map((file) => file.status))].map((status) => pill(status, toneOf(status))),
      actions,
      files.map((file) => ({ file: file.file_name, status: file.status, method: file.method, location: file.default_path, stored_at: file.managed_path })),
      opened,
    );
  });
}

export function foundGroups(plans, onCollect, opened) {
  return [...Map.groupBy(plans, (plan) => plan.group)].map(([name, files]) => {
    const action = button({ label: "Collect", glyph: "plus", small: true, title: "Keep this group's files in your dotfiles folder", onclick: () => onCollect(name) });
    const [only] = files;
    if (files.length === 1) return single(name, only.name, COLLECT_WORDS[only.verdict], "", only.original_path, only.managed_path, action);
    return fold(name, [], action, files.map((file) => ({ file: file.name, status: COLLECT_WORDS[file.verdict], location: file.original_path, will_be_kept_at: file.managed_path })), opened);
  });
}
