import { h, icon } from "./dom.js";
import { DASHBOARDS } from "./presets.js";
import { nodeHash, state } from "./state.js";

const RESULT_LIMIT = 60;

export function createPalette() {
  const entries = [
    { emoji: "🏠", path: "Home", summary: "Dashboards, quick actions, and recent runs", href: "#/", kind: "view" },
    { emoji: "🧭", path: "Command map", summary: "Sunburst, treemap, and icicle of every command", href: "#/map", kind: "view" },
    ...DASHBOARDS.map((board) => ({ emoji: board.icon, path: board.title, summary: board.blurb, href: `#/d/${board.id}`, kind: "dashboard" })),
    ...[...state.nodes.values()]
      .filter((node) => node.kind !== "root")
      .map((node) => ({ emoji: node.icon || (node.kind === "command" ? "▫️" : "🗂️"), path: node.path, summary: node.summary, href: nodeHash(node), kind: node.kind, name: node.name })),
  ].map((entry) => ({ ...entry, haystack: `${entry.path} ${entry.summary}`.toLowerCase() }));
  let matches = [];
  let selected = 0;

  const input = h("input", { type: "text", placeholder: "Search commands, groups, and dashboards", spellcheck: "false", autocomplete: "off", "aria-label": "Search" });
  const list = h("div", { class: "palette-list", role: "listbox" });
  const element = h(
    "div",
    { class: "palette-backdrop", hidden: true },
    h(
      "div",
      { class: "palette", role: "dialog", "aria-label": "Search" },
      h("div", { class: "palette-field" }, icon("search", 16), input),
      list,
      h("div", { class: "palette-foot" }, h("span", {}, h("kbd", { text: "↑" }), " ", h("kbd", { text: "↓" }), " move"), h("span", {}, h("kbd", { text: "Enter" }), " open"), h("span", {}, h("kbd", { text: "Esc" }), " close")),
    ),
  );

  function mark() {
    [...list.children].forEach((row, index) => row.setAttribute("aria-selected", String(index === selected)));
    list.children[selected]?.scrollIntoView({ block: "nearest" });
  }

  function search() {
    const terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    const rank = (entry) => (terms.length && (entry.name ?? entry.path).toLowerCase().startsWith(terms[0]) ? 0 : terms.length && entry.path.toLowerCase().includes(terms[0]) ? 1 : 2);
    matches = entries
      .filter((entry) => terms.every((term) => entry.haystack.includes(term)))
      .sort((left, right) => rank(left) - rank(right) || left.path.length - right.path.length)
      .slice(0, RESULT_LIMIT);
    selected = 0;
    list.replaceChildren(
      ...(matches.length
        ? matches.map((entry, index) =>
            h(
              "div",
              {
                class: "palette-item", role: "option",
                onclick: () => choose(index),
                onmousemove: () => {
                  if (selected === index) return;
                  selected = index;
                  mark();
                },
              },
              h("span", { class: "emoji", text: entry.emoji }),
              h("div", {}, h("div", { class: "path", text: entry.path }), h("div", { class: "summary", text: entry.summary })),
              h("span", { class: "badge", text: entry.kind }),
            ),
          )
        : [h("p", { class: "palette-empty", text: "Nothing matches. Try fewer or different words." })]),
    );
    mark();
  }

  function close() {
    element.hidden = true;
  }

  function choose(index) {
    if (!matches[index]) return;
    location.hash = matches[index].href;
    close();
  }

  function open() {
    element.hidden = false;
    input.value = "";
    search();
    input.focus();
  }

  input.addEventListener("input", search);
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      selected = (selected + (event.key === "ArrowDown" ? 1 : matches.length - 1)) % Math.max(matches.length, 1);
      mark();
    } else if (event.key === "Enter") choose(selected);
    else if (event.key === "Escape") close();
  });
  element.addEventListener("mousedown", (event) => event.target === element && close());
  document.addEventListener("keydown", (event) => {
    const inTerminal = event.target instanceof Element && event.target.closest(".xterm") !== null;
    const typing = event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement;
    const shortcut = event.key.toLowerCase() === "k" && (event.metaKey || (event.ctrlKey && !inTerminal));
    if (!shortcut && !(event.key === "/" && !typing && !inTerminal)) return;
    event.preventDefault();
    open();
  });

  return { element, open };
}
