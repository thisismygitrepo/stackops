import { h, icon } from "/assets/scripts/dom.js";
import { lineage, state } from "/assets/scripts/state.js";
import { rise } from "../motion.js";
import { toolCard } from "../space_kit.js";
import { emojiTile, notice, searchInput, sectionHead } from "../widgets.js";
import { friendlyText, plural, titleOf, trailOf } from "../words.js";

const hashOf = (node) => (node.path === "" ? "#/tools" : `#/tools/${node.path.split(" ").map(encodeURIComponent).join("/")}`);

export function createToolboxSpace({ tools }) {
  const crumbs = h("nav", { class: "crumbs", "aria-label": "Breadcrumb" });
  const title = h("h1");
  const lede = h("p");
  const content = h("div", { class: "toolbox-content" });
  let current = state.boot.tree;
  let term = "";
  const filter = searchInput({
    placeholder: "Filter these tools",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });

  const groupCard = (node) =>
    h(
      "a",
      { class: "group-card lit", href: hashOf(node) },
      emojiTile(node.icon || "🗂️", node.path, 48),
      h("strong", { text: titleOf(node) }),
      h("span", { text: friendlyText(node.summary) }),
      h("em", {}, plural(node.leaves, "tool"), icon("arrow", 13)),
    );

  function everyTool(node) {
    return node.kind === "command" ? [node] : node.children.flatMap(everyTool);
  }

  // A design choice: filtered results do not rise and are not cut short. Rising restarted on every keystroke and left the results blank while
  // typing, and every match is drawn so the count in the heading is the number of cards under it.
  function paint() {
    if (term) {
      const found = everyTool(current).filter((node) => `${titleOf(node)} ${trailOf(node)} ${node.summary} ${node.path}`.toLowerCase().includes(term));
      content.replaceChildren(
        found.length
          ? h("section", { class: "block" }, sectionHead(`${plural(found.length, "tool")} found`), h("div", { class: "tool-grid" }, found.map((node) => toolCard(tools, node, `${titleOf(node)}${trailOf(node) ? ` · ${trailOf(node)}` : ""}`))))
          : notice({ glyph: "search", title: "No tool matches", body: "Try a different word." }),
      );
      return;
    }
    const groups = current.children.filter((child) => child.kind !== "command");
    const commands = current.children.filter((child) => child.kind === "command");
    content.replaceChildren(
      ...[
        groups.length > 0 && h("section", { class: "block" }, sectionHead(current.kind === "root" ? "Collections" : "Inside"), rise(h("div", { class: "group-grid" }, groups.map(groupCard)))),
        commands.length > 0 && h("section", { class: "block" }, sectionHead("Tools"), rise(h("div", { class: "tool-grid" }, commands.map((node) => toolCard(tools, node))))),
      ].filter(Boolean),
    );
  }

  function show(route) {
    const node = state.nodes.get(route.join(" "));
    const previous = current;
    if (node?.kind === "command") {
      history.replaceState(null, "", hashOf(state.parents.get(node.path)));
      current = state.parents.get(node.path);
      tools.open(node.path);
    } else current = node ?? state.boot.tree;
    if (current !== previous) element.closest(".stage")?.scrollTo(0, 0);
    term = "";
    filter.input.value = "";
    const chain = current.kind === "root" ? [] : lineage(current);
    crumbs.replaceChildren(
      ...[{ label: "Toolbox", href: "#/tools" }, ...chain.map((item) => ({ label: titleOf(item), href: hashOf(item) }))].flatMap((item, index, all) => [
        index > 0 && icon("chevron", 12),
        index === all.length - 1 ? h("span", { class: "here", text: item.label }) : h("a", { href: item.href, text: item.label }),
      ]).filter(Boolean),
    );
    crumbs.hidden = chain.length === 0;
    title.textContent = current.kind === "root" ? "Toolbox" : titleOf(current);
    lede.textContent = current.kind === "root" ? `Everything StackOps can do — ${plural(current.leaves, "tool")}, grouped so you can browse.` : friendlyText(current.summary);
    paint();
  }

  const element = h("section", { class: "view toolbox", hidden: true }, crumbs, h("header", { class: "view-head" }, h("div", { class: "view-title" }, title, lede), h("div", { class: "view-actions" }, filter.element)), content);
  return { element, show };
}
