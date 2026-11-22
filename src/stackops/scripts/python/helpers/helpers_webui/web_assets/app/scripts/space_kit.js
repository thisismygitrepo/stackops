import { h, icon, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { button, emojiTile } from "./widgets.js";
import { friendlyText, titleOf } from "./words.js";

const FILE_EDITORS = { script: ["devops", "scripts", "edit"], file: ["utils", "file", "edit"] };

// How a page offers Edit for a file the CLI knows how to check: the CLI's own edit command in the activity console. It creates a missing file and
// checks it when the editor closes, and pages refresh when the run ends. It needs the CLI's editor on the serving machine. The one exception is the
// file window in Agents › Health, which reads and saves a file as plain text through /api/file.
export function editFile(activity, { title, kind, path }) {
  const editArguments = FILE_EDITORS[kind] ? [...FILE_EDITORS[kind], path] : ["devops", "config", "edit", kind, ...(path ? ["--custom-path", path] : [])];
  return activity.start({ title: `Edit ${title}`, emoji: "📝", arguments: editArguments, interactive: true, reveal: true, wide: true }).catch((error) => toast(error.message));
}

export function editButton(activity, target, { label = "Edit", small = false } = {}) {
  return button({ label, glyph: "terminal", small, title: "Opens the file in a text editor inside the activity panel. It is checked when you close the editor.", onclick: () => editFile(activity, target) });
}

export function viewHead({ title, lede, actions }) {
  return h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { text: title }), h("p", { text: lede })), actions && h("div", { class: "view-actions" }, actions));
}

export function createView({ title, lede, actions = [] }, ...content) {
  return h("section", { class: "view", hidden: true }, viewHead({ title, lede, actions }), ...content);
}

export function toolButton(tools, path, { label, glyph, tone, preset = {} } = {}) {
  const node = state.nodes.get(path);
  return node && button({ label: label ?? titleOf(node), glyph, tone, title: friendlyText(node.summary), onclick: () => tools.open(path, { preset }) });
}

const cardParts = (emoji, name, title, blurb) => [emojiTile(emoji, name, 40), h("span", { class: "tool-card-text" }, h("strong", { text: title }), h("span", { text: blurb })), icon("arrow", 14)];

export function toolCard(tools, node, label) {
  return h("button", { class: "tool-card lit", type: "button", onclick: () => tools.open(node.path) }, cardParts(node.icon || "✨", node.path, label ?? titleOf(node), friendlyText(node.summary)));
}

// The same card for somewhere to go instead of a tool to open. `name` only picks the tile's colour.
export function linkCard({ href, emoji, name, title, blurb }) {
  return h("a", { class: "tool-card lit", href }, cardParts(emoji, name, title, blurb));
}

export function toolGrid(tools, paths) {
  return h("div", { class: "tool-grid" }, paths.filter((path) => state.nodes.has(path)).map((path) => toolCard(tools, state.nodes.get(path))));
}
