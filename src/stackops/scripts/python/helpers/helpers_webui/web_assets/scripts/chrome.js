import { VIEW_KEY } from "/assets/app/scripts/catalog.js";
import { debounce, h, icon, tildify, toast } from "./dom.js";
import { api, lineage, nodeHash, on, setSetting, state } from "./state.js";

let completionCount = 0;

export function attachPathCompletion(input) {
  const list = h("datalist", { id: `path-completions-${(completionCount += 1)}` });
  input.setAttribute("list", list.id);
  const refresh = debounce(async () => {
    // A design choice: suggestions are a convenience, so when they cannot be fetched the field shows none and says nothing. Whatever is done with the path next reports the problem, once.
    const { entries } = await api.paths(input.value, state.settings.workingDirectory).catch(() => ({ entries: [] }));
    list.replaceChildren(...entries.map((entry) => h("option", { value: entry })));
  }, 120);
  input.addEventListener("input", refresh);
  input.addEventListener("focus", refresh);
  return list;
}

export function createRail({ openPalette }) {
  const { boot } = state;
  const rows = new Map();
  const links = {
    home: h("a", { class: "rail-link", href: "#/" }, icon("home"), "Home"),
    dashboards: h("a", { class: "rail-link", href: "#/d" }, icon("dashboard"), "Dashboards"),
    map: h("a", { class: "rail-link", href: "#/map" }, icon("map"), "Command map"),
  };

  function setExpanded(path, expanded) {
    const entry = rows.get(path);
    if (!entry.list || entry.list.hidden === !expanded) return;
    entry.list.hidden = !expanded;
    entry.toggle.setAttribute("aria-expanded", String(expanded));
    const open = new Set(state.settings.expanded);
    if (expanded) open.add(path);
    else open.delete(path);
    setSetting("expanded", [...open]);
  }

  function branch(node, depth) {
    const isGroup = node.kind !== "command";
    const list = isGroup ? h("ul", { hidden: true }, node.children.map((child) => branch(child, depth + 1))) : null;
    const toggle = h(
      "button",
      { class: `tree-toggle${isGroup ? "" : " leaf"}`, "aria-expanded": "false", "aria-label": `${node.name} commands`, onclick: () => setExpanded(node.path, list.hidden) },
      icon("chevron", 12),
    );
    const row = h(
      "div",
      { class: "tree-row", style: `--depth: ${depth}`, title: node.summary },
      toggle,
      h("a", { class: "tree-link", href: nodeHash(node) }, (isGroup || depth === 0) && h("span", { class: "emoji", text: node.icon || "▫️" }), h("span", { class: "name", text: node.name })),
      isGroup && h("span", { class: "tree-count", text: String(node.leaves) }),
    );
    rows.set(node.path, { row, toggle, list });
    return h("li", {}, row, list);
  }

  const tree = h("ul", { class: "rail-tree" }, boot.tree.children.map((child) => branch(child, 0)));
  for (const path of state.settings.expanded) if (rows.has(path)) setExpanded(path, true);
  const element = h(
    "aside",
    { class: "rail" },
    h("div", { class: "rail-brand" }, h("img", { src: "/assets/favicon.svg", alt: "" }), h("strong", { text: "StackOps" }), h("span", { class: "chip", text: `v${boot.version}` })),
    h("button", { class: "rail-search", onclick: openPalette }, icon("search", 14), h("span", { text: "Search commands" }), h("kbd", { text: navigator.platform.startsWith("Mac") ? "⌘K" : "Ctrl K" })),
    h("nav", { class: "rail-nav", "aria-label": "Views" }, Object.values(links)),
    h("div", { class: "rail-label" }, h("span", { text: "Commands" }), h("a", { href: "#/c", text: `${boot.tree.leaves} total` })),
    tree,
    h(
      "button",
      {
        class: "rail-switch", title: "Switch to the app view: pages, search, and one-click tasks",
        onclick: () => {
          localStorage.setItem(VIEW_KEY, "app");
          location.href = "/";
        },
      },
      icon("sparkle", 14),
      h("span", { text: "Switch to app view" }),
    ),
    h("div", { class: "rail-foot" }, icon("terminal", 14), h("span", { text: `${boot.user}@${boot.host} · ${boot.platform}` })),
  );

  function setActive(route) {
    for (const [name, link] of Object.entries(links)) link.setAttribute("aria-current", String(route.view === name));
    for (const [path, entry] of rows) entry.row.setAttribute("aria-current", String(route.view === "browse" && path === route.path));
    const node = route.view === "browse" ? state.nodes.get(route.path) : null;
    if (!node || node.kind === "root") return;
    for (const ancestor of lineage(node)) if (ancestor.kind !== "command") setExpanded(ancestor.path, true);
    rows.get(node.path).row.scrollIntoView({ block: "nearest" });
  }

  return { element, setActive };
}

export function createTopbar({ dock }) {
  const crumbs = h("nav", { class: "crumbs", "aria-label": "Breadcrumb" });
  const directoryLabel = h("span");
  const directoryButton = h("button", { class: "cwd", title: "Working directory for the commands you run. Click to change." }, icon("folder", 14), directoryLabel);
  const directoryInput = h("input", { class: "input mono cwd-edit", hidden: true, spellcheck: "false", "aria-label": "Working directory" });
  const runLabel = h("span");
  const runGlyph = h("span", { class: "status" });
  const runButton = h("button", { class: "run-indicator", title: "Show or hide the terminal dock", onclick: () => dock.toggle() }, runGlyph, runLabel);

  const showDirectory = () => {
    directoryLabel.textContent = `‎${tildify(state.settings.workingDirectory, state.boot.home)}`;
    directoryInput.hidden = true;
    directoryButton.hidden = false;
  };
  directoryButton.addEventListener("click", () => {
    directoryInput.value = state.settings.workingDirectory;
    directoryButton.hidden = true;
    directoryInput.hidden = false;
    directoryInput.focus();
    directoryInput.select();
  });
  directoryInput.addEventListener("keydown", async (event) => {
    const typed = directoryInput.value.trim();
    if (event.key === "Escape" || (event.key === "Enter" && !typed)) return showDirectory();
    if (event.key !== "Enter") return;
    // The server names the folder the text stands for, so what is kept is a full path to a folder that exists. Anything else stays in the box with the reason.
    try {
      setSetting("workingDirectory", (await api.directory(typed, state.settings.workingDirectory)).path);
      showDirectory();
    } catch (error) {
      toast(error.message);
    }
  });
  directoryInput.addEventListener("blur", showDirectory);

  const showRuns = () => {
    const runs = dock.runs();
    const active = runs.filter((run) => run.exit_code === null).length;
    runGlyph.replaceChildren(active ? h("span", { class: "spinner" }) : icon("terminal", 14));
    runLabel.textContent = active ? `${active} running` : runs.length ? `${runs.length} run${runs.length === 1 ? "" : "s"}` : "Terminal";
  };
  on("runs", showRuns);
  showDirectory();
  showRuns();

  function setCrumbs(items) {
    crumbs.replaceChildren(
      ...items.flatMap((item, index) => [
        index > 0 && h("span", { text: "/" }),
        index === items.length - 1 ? h("span", { class: "here", text: item.label }) : h("a", { href: item.href, text: item.label }),
      ]).filter(Boolean),
    );
  }

  const menuButton = h(
    "button",
    { class: "icon-button menu-button", title: "Show navigation", "aria-label": "Show navigation", onclick: () => document.querySelector(".shell").classList.toggle("rail-open") },
    icon("menu", 16),
  );
  return { element: h("header", { class: "topbar" }, menuButton, crumbs, directoryButton, directoryInput, attachPathCompletion(directoryInput), runButton), setCrumbs };
}
