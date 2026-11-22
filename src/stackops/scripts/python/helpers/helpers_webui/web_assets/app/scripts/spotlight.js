import { h, icon } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { QUICK_TASKS, REPORTS, SPACES } from "./catalog.js";
import { software } from "./data.js";
import { closeAll, openDialog } from "./overlays.js";
import { avatar, emojiTile, glyphTile, highlight } from "./widgets.js";
import { friendlyText, fullTitleOf, plainText, trailOf } from "./words.js";

const GROUP_LIMIT = 7;
const GROUP_ORDER = ["Recent", "Suggested", "Pages", "Apps", "Tools", "Collections", "Reports"];
// Written by the tool sheet: the last few command paths opened, newest first.
const RECENT_KEY = "stackops-webui-recent";
// Tools that have a guided page of their own: search lands there instead of on the bare tool.
const GUIDED_TOOLS = { "utils machine clean-drive": "#/machine/cleanup", "devops security status": "#/security", "devops security history": "#/security/scans" };

export function createSpotlight({ tools }) {
  const fixed = [
    ...SPACES.map((space) => ({ group: "Pages", title: space.title, hint: "Go to this page", lead: () => glyphTile(space.glyph, 245, 34), go: () => (location.hash = space.hash) })),
    ...REPORTS.map((report) => ({ group: "Reports", title: report.title, hint: report.blurb, lead: () => glyphTile(report.glyph, 190, 34), go: () => (location.hash = `#/reports/${report.id}`) })),
    ...[...state.nodes.values()]
      .filter((node) => node.kind !== "root")
      .map((node) => ({
        group: node.kind === "command" ? "Tools" : "Collections",
        // The parent is part of the title: a third of the tools share a one-word name (Validate, Status, Edit) with tools elsewhere.
        title: fullTitleOf(node),
        hint: [trailOf(node), friendlyText(node.summary)].filter(Boolean).join(" — "),
        words: node.path,
        lead: () => emojiTile(node.icon || (node.kind === "command" ? "✨" : "🗂️"), node.path, 34),
        go: () => (GUIDED_TOOLS[node.path] ? (location.hash = GUIDED_TOOLS[node.path]) : node.kind === "command" ? tools.open(node.path) : (location.hash = `#/tools/${node.path.split(" ").map(encodeURIComponent).join("/")}`)),
      })),
  ];
  const suggested = QUICK_TASKS.map((task) => ({
    group: "Suggested", title: task.title, hint: task.blurb, lead: () => glyphTile(task.glyph, task.tint, 34),
    go: () => (task.tool ? tools.open(task.tool, { preset: task.preset ?? {} }) : (location.hash = task.hash)),
  }));
  let apps = [];
  let recent = [];
  let dialog = null;

  function entriesFor(text) {
    const terms = text.toLowerCase().split(/\s+/).filter(Boolean);
    if (terms.length === 0) return [...recent, ...suggested, ...fixed.filter((entry) => entry.group === "Pages")];
    // Titles holding more of the typed words come first, then titles that start with the first word, then shorter ones.
    const rank = (entry) => {
      const title = entry.title.toLowerCase();
      return (terms.length - terms.filter((term) => title.includes(term)).length) * 2 + (title.startsWith(terms[0]) ? 0 : 1);
    };
    return [...fixed, ...apps]
      .filter((entry) => terms.every((term) => entry.haystack.includes(term)))
      .map((entry) => ({ entry, rank: rank(entry) }))
      .sort((left, right) => left.rank - right.rank || left.entry.title.length - right.entry.title.length)
      .map(({ entry }) => entry);
  }

  function open(initial = "") {
    if (dialog) return;
    recent = JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]").flatMap((path) => fixed.filter((entry) => entry.group === "Tools" && entry.words === path).map((entry) => ({ ...entry, group: "Recent" })));
    const input = h("input", { type: "text", placeholder: "Search apps, tools, pages, and reports", spellcheck: "false", autocomplete: "off", "aria-label": "Search", value: initial });
    const list = h("div", { class: "spot-list", role: "listbox" });
    let rows = [];
    let selected = 0;
    dialog = openDialog({ label: "Search", size: "spotlight" });
    dialog.closed.then(() => (dialog = null));

    const mark = () => {
      rows.forEach(({ row }, index) => row.setAttribute("aria-selected", String(index === selected)));
      rows[selected]?.row.scrollIntoView({ block: "nearest" });
    };
    const choose = (index) => {
      const entry = rows[index]?.entry;
      if (!entry) return;
      closeAll();
      entry.go();
    };
    const search = () => {
      const found = entriesFor(input.value);
      const term = input.value.trim().split(/\s+/)[0] ?? "";
      rows = [];
      const sections = GROUP_ORDER.map((group) => [group, found.filter((entry) => entry.group === group).slice(0, GROUP_LIMIT)]).filter(([, entries]) => entries.length);
      list.replaceChildren(
        ...(sections.length
          ? sections.flatMap(([group, entries]) => [
              h("div", { class: "spot-group", text: group }),
              ...entries.map((entry) => {
                const index = rows.length;
                const row = h(
                  "div",
                  {
                    class: "spot-item", role: "option", style: `--i:${Math.min(index, 14)}`,
                    onclick: () => choose(index),
                    onmousemove: () => {
                      if (selected === index) return;
                      selected = index;
                      mark();
                    },
                  },
                  entry.lead(),
                  h("div", { class: "spot-text" }, h("strong", {}, highlight(entry.title, term)), h("span", { text: entry.hint })),
                  h("span", { class: "spot-enter" }, icon("arrow", 14)),
                );
                rows.push({ row, entry });
                return row;
              }),
            ])
          : [h("p", { class: "spot-empty", text: "Nothing matches. Try fewer or different words." })]),
      );
      selected = 0;
      mark();
    };

    input.addEventListener("input", search);
    input.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "ArrowUp") {
        event.preventDefault();
        selected = (selected + (event.key === "ArrowDown" ? 1 : rows.length - 1)) % Math.max(rows.length, 1);
        mark();
      } else if (event.key === "Enter") choose(selected);
    });
    dialog.body.append(
      h("div", { class: "spot-field" }, icon("search", 20), input, h("kbd", { text: "Esc" })),
      list,
      h("div", { class: "spot-foot" }, h("span", {}, h("kbd", { text: "↑" }), h("kbd", { text: "↓" }), " to move"), h("span", {}, h("kbd", { text: "↵" }), " to open")),
    );
    search();
    input.focus();
    software()
      .then((catalog) => {
        apps = catalog.apps.map((app) => ({
          group: "Apps", title: app.name, hint: plainText(app.summary), lead: () => avatar(app.name, 34),
          go: () => (location.hash = `#/apps/${encodeURIComponent(app.name)}`),
        }));
        for (const entry of apps) entry.haystack = `${entry.title} ${entry.hint}`.toLowerCase();
        if (dialog && input.value) search();
      })
      .catch(() => {});
  }

  for (const entry of fixed) entry.haystack = `${entry.title} ${entry.hint} ${entry.words ?? ""}`.toLowerCase();
  document.addEventListener("keydown", (event) => {
    const inConsole = event.target instanceof Element && event.target.closest(".xterm") !== null;
    const typing = event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement || event.target instanceof HTMLTextAreaElement;
    const shortcut = event.key.toLowerCase() === "k" && (event.metaKey || (event.ctrlKey && !inConsole));
    if (!shortcut && !(event.key === "/" && !typing && !inConsole)) return;
    event.preventDefault();
    open();
  });

  return { open };
}
