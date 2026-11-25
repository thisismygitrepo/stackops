import { h, icon, toast } from "/assets/scripts/dom.js";
import { lineage, state } from "/assets/scripts/state.js";
import { collectionLoader } from "../features.js";
import { rise } from "../motion.js";
import { toolCard } from "../space_kit.js";
import { emojiTile, notice, searchInput, sectionHead } from "../widgets.js";
import { friendlyText, plural, titleOf, trailOf } from "../words.js";

const hashOf = (node) => (node.path === "" ? "#/tools" : `#/tools/${node.path.split(" ").map(encodeURIComponent).join("/")}`);

export function createToolboxSpace(context) {
  const { tools } = context;
  const crumbs = h("nav", { class: "crumbs", "aria-label": "Breadcrumb" });
  const title = h("h1");
  const lede = h("p");
  const content = h("div", { class: "toolbox-content" });
  // A collection with a page of its own shows that page here, in place of its tool cards (features.js lists them).
  const pageHolder = h("div", { class: "toolbox-page", hidden: true });
  const pages = new Map();
  let asked = 0;
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

  function showCards() {
    pageHolder.hidden = true;
    content.hidden = false;
    filter.element.hidden = false;
    paint();
  }

  // `rest` is the part of the address past the collection's own, which belongs to its page.
  async function showPage(node, rest) {
    const mine = (asked += 1);
    content.hidden = true;
    filter.element.hidden = true;
    pageHolder.hidden = false;
    for (const [path, page] of pages) page.element.hidden = path !== node.path;
    if (!pages.has(node.path)) {
      try {
        const page = (await collectionLoader(node.path)()).createPart(context);
        // Two visits can be waiting for the same page at once; the first one back keeps its copy.
        if (!pages.has(node.path)) {
          pages.set(node.path, page);
          pageHolder.append(page.element);
        }
      } catch (error) {
        // The page did not load, so the collection shows its tool cards, which still open every command.
        if (mine === asked && current === node) showCards();
        toast(`The page for ${titleOf(node)} did not load. ${error.message}`);
        return;
      }
      pages.get(node.path).element.hidden = mine !== asked || current !== node;
      // The Toolbox moved on to another address while this page was on its way.
      if (mine !== asked) return;
    }
    pages.get(node.path).show(rest);
  }

  function show(route) {
    let node = state.nodes.get(route.join(" "));
    let rest = [];
    // An address that goes on past a collection with a page of its own belongs to that page.
    for (let length = route.length - 1; !node && length > 0; length -= 1) {
      const candidate = state.nodes.get(route.slice(0, length).join(" "));
      if (candidate && candidate.kind !== "command" && collectionLoader(candidate.path)) {
        node = candidate;
        rest = route.slice(length);
      }
    }
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
    asked += 1;
    if (current.kind !== "root" && collectionLoader(current.path)) showPage(current, rest);
    else showCards();
  }

  const element = h("section", { class: "view toolbox", hidden: true }, crumbs, h("header", { class: "view-head" }, h("div", { class: "view-title" }, title, lede), h("div", { class: "view-actions" }, filter.element)), content, pageHolder);
  return { element, show };
}
