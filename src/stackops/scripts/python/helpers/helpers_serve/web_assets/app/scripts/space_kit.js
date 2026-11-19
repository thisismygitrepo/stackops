import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { button, emojiTile } from "./widgets.js";
import { friendlyText, titleOf } from "./words.js";

export function createView({ title, lede, actions = [] }, ...content) {
  return h(
    "section",
    { class: "view", hidden: true },
    h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { text: title }), h("p", { text: lede })), h("div", { class: "view-actions" }, actions)),
    ...content,
  );
}

export function toolButton(tools, path, { label, glyph, tone, preset = {} } = {}) {
  const node = state.nodes.get(path);
  return node && button({ label: label ?? titleOf(node), glyph, tone, title: friendlyText(node.summary), onclick: () => tools.open(path, { preset }) });
}

export function toolCard(tools, node, label) {
  return h(
    "button",
    { class: "tool-card lit", type: "button", onclick: () => tools.open(node.path) },
    emojiTile(node.icon || "✨", node.path, 40),
    h("span", { class: "tool-card-text" }, h("strong", { text: label ?? titleOf(node) }), h("span", { text: friendlyText(node.summary) })),
    icon("arrow", 14),
  );
}

export function toolGrid(tools, paths) {
  return h("div", { class: "tool-grid" }, paths.filter((path) => state.nodes.has(path)).map((path) => toolCard(tools, state.nodes.get(path))));
}
