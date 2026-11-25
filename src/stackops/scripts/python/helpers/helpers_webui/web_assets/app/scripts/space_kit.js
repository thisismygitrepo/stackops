import { h, icon, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { replay } from "./motion.js";
import { button, emojiTile } from "./widgets.js";
import { blurbOf, titleOf } from "./words.js";

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

// The way back from one of a page's views to the page itself, above that view's title. Every view draws it with this, so it is the same
// button everywhere.
export function backLink(href, label) {
  return aimBackLink(h("a", { class: "part-back" }, icon("back", 18), h("span")), href, label);
}

// For a view that is reached from more than one place: where its link leads is set again on each arrival. "Back" is the label for a place
// that has no name of its own.
export function aimBackLink(link, href, label) {
  link.href = href;
  link.lastElementChild.textContent = label;
  link.title = label === "Back" ? "Back to the page you came from" : `Back to ${label}`;
  return link;
}

export function viewHead({ title, lede, actions }) {
  return h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { text: title }), h("p", { text: lede })), actions && h("div", { class: "view-actions" }, actions));
}

export function createView({ title, lede, actions = [] }, ...content) {
  return h("section", { class: "view", hidden: true }, viewHead({ title, lede, actions }), ...content);
}

// A page's further views, each at an address of its own under the page's (`#/machine/cleanup`) and shown in place of its overview. `built` holds
// the views made with the page, the overview under ""; `loaders` holds the ones fetched and made on their first visit (features.js). A view is
// `{ element, show(rest) }`, as a page is. Returns the page's `show(route)`. An address that names no view shows the overview.
export function createParts({ element, built, loaders, context }) {
  const parts = new Map(Object.entries(built));
  for (const [name, part] of parts) {
    part.element.classList.add("space-part");
    part.element.hidden = name !== "";
  }
  let asked = 0;
  let shown = null;
  return async function show(route) {
    const name = parts.has(route[0]) || Object.hasOwn(loaders, route[0] ?? "") ? route[0] : "";
    const mine = (asked += 1);
    if (!parts.has(name)) {
      const part = (await loaders[name]()).createPart(context);
      // Two visits can be waiting for the same view at once; the first one back keeps its copy.
      if (!parts.has(name)) {
        part.element.classList.add("space-part");
        part.element.hidden = true;
        element.append(part.element);
        parts.set(name, part);
      }
      // The page moved on to another address while this view was on its way.
      if (mine !== asked) return;
    }
    const part = parts.get(name);
    for (const other of parts.values()) other.element.hidden = other !== part;
    if (shown && shown !== part) {
      replay(part.element, "swap");
      element.closest(".stage")?.scrollTo(0, 0);
    }
    shown = part;
    part.show(route.slice(1));
  };
}

export function toolButton(tools, path, { label, glyph, tone, preset = {} } = {}) {
  const node = state.nodes.get(path);
  return node && button({ label: label ?? titleOf(node), glyph, tone, title: blurbOf(node), onclick: () => tools.open(path, { preset }) });
}

const cardParts = (emoji, name, title, blurb) => [emojiTile(emoji, name, 40), h("span", { class: "tool-card-text" }, h("strong", { text: title }), h("span", { text: blurb })), icon("arrow", 14)];

export function toolCard(tools, node, label) {
  return h("button", { class: "tool-card lit", type: "button", onclick: () => tools.open(node.path) }, cardParts(node.icon || "✨", node.path, label ?? titleOf(node), blurbOf(node)));
}

// The same card for somewhere to go instead of a tool to open. `name` only picks the tile's colour.
export function linkCard({ href, emoji, name, title, blurb }) {
  return h("a", { class: "tool-card lit", href }, cardParts(emoji, name, title, blurb));
}

export function toolGrid(tools, paths) {
  return h("div", { class: "tool-grid" }, paths.filter((path) => state.nodes.has(path)).map((path) => toolCard(tools, state.nodes.get(path))));
}
