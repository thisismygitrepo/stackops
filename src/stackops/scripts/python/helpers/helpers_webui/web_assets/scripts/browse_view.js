import { createCommandForm } from "./command_form.js";
import { h, icon, shellQuote, toast } from "./dom.js";
import { api, lineage, nodeHash, state } from "./state.js";

const REPORT_FLAG = "--as-html";

function card(node) {
  const isGroup = node.kind !== "command";
  return h(
    "a",
    { class: "card", href: nodeHash(node) },
    h("span", { class: "emoji", text: node.icon || (isGroup ? "🗂️" : "▫️") }),
    h(
      "span",
      { class: "title" },
      h("span", { class: "name", text: node.name }),
      h("span", { class: "tail" }, isGroup ? `${node.leaves} command${node.leaves === 1 ? "" : "s"}` : h("kbd", { text: node.short_path })),
    ),
    h("span", { class: "blurb", text: node.summary }),
  );
}

export function createBrowseView({ dock, openReport }) {
  const element = h("section", { class: "view" });
  const details = new Map();
  const drafts = new Map();
  let shownPath = null;
  let runShown = () => {};

  function head(node, title, titleClass) {
    return h(
      "header",
      { class: "view-head" },
      h("span", { class: "glyph", text: node.icon || (node.kind === "command" ? "▫️" : "🗂️") }),
      h("div", {}, h("h1", { class: titleClass, text: title }), h("p", { class: "lede", text: node.summary })),
      node.short_path && node.short_path !== node.path && h("div", { class: "aside" }, h("span", { class: "chip outline mono", title: "Short alias", text: `stackops ${node.short_path}` })),
    );
  }

  function renderGroup(node) {
    const groups = node.children.filter((child) => child.kind !== "command");
    const commands = node.children.filter((child) => child.kind === "command");
    const section = (title, items) =>
      items.length > 0 &&
      h(
        "section",
        { class: "section" },
        h("div", { class: "section-head" }, h("h2", { text: title }), h("span", { class: "count", text: String(items.length) })),
        h("div", { class: "cards" }, items.map(card)),
      );
    const description = node.description.trim();
    element.replaceChildren(
      ...[
        head(node, node.kind === "root" ? "All commands" : `stackops ${node.path}`, node.kind === "root" ? "" : "mono"),
        description !== node.summary && description.includes("\n") && h("pre", { class: "long-help", text: description }),
        section("Groups", groups),
        section("Commands", commands),
      ].filter(Boolean),
    );
    runShown = () => {};
  }

  async function renderCommand(node) {
    const pathTokens = node.path.split(" ");
    const description = node.description.trim();
    const body = h("div", {}, h("p", { class: "form-note", text: "Reading this command's options…" }));
    const preview = h("code");
    const problem = h("span", { class: "problem" });
    const runButton = h("button", { class: "button primary", title: "Run in the terminal dock (Ctrl/⌘ + Enter)" }, icon("play", 14), "Run");
    const reportButton = h("button", { class: "button", hidden: true, title: "Run with --as-html and show the report here" }, icon("report", 14), "Open report");
    const resetButton = h("button", { class: "button ghost", text: "Reset" });
    const copyButton = h("button", { class: "icon-button", title: "Copy command", "aria-label": "Copy command" }, icon("copy", 15));
    const runbar = h(
      "div",
      { class: "runbar" },
      h("div", { class: "preview" }, h("span", { class: "prompt", text: "$" }), preview, copyButton),
      problem,
      resetButton,
      reportButton,
      runButton,
    );
    element.replaceChildren(
      ...[
        head(node, `stackops ${node.path}`, "mono"),
        description !== node.summary && description.includes("\n") && h("pre", { class: "long-help", text: description }),
        body,
        runbar,
      ].filter(Boolean),
    );
    runShown = () => {};

    if (!details.has(node.path)) details.set(node.path, api.command(node.path));
    let parameters;
    try {
      ({ parameters } = await details.get(node.path));
    } catch (error) {
      details.delete(node.path);
      if (shownPath !== node.path) return;
      runbar.remove();
      body.replaceChildren(
        h(
          "div",
          { class: "form-note retry" },
          h("span", { text: `This command's options could not be read: ${error.message}` }),
          h("button", { class: "button small", onclick: () => renderCommand(node) }, icon("refresh", 13), "Try again"),
        ),
      );
      return;
    }
    if (shownPath !== node.path) return;
    if (!drafts.has(node.path)) drafts.set(node.path, new Map());
    let current = { tokens: [], problems: [] };
    const refresh = () => {
      current = form.collect();
      preview.textContent = ["stackops", ...pathTokens, ...current.tokens].map(shellQuote).join(" ");
      problem.textContent = current.problems[0] ?? "";
      runButton.disabled = reportButton.disabled = current.problems.length > 0;
    };
    const form = createCommandForm(parameters, drafts.get(node.path), () => refresh());
    body.replaceChildren(form.element);
    reportButton.hidden = !form.hasFlag(REPORT_FLAG);
    refresh();

    const run = async () => {
      if (current.problems.length) return;
      try {
        await dock.start({ arguments: [...pathTokens, ...current.tokens], interactive: true, reveal: true });
      } catch (error) {
        toast(error.message);
      }
    };
    runShown = run;
    runButton.addEventListener("click", run);
    resetButton.addEventListener("click", () => form.reset());
    reportButton.addEventListener("click", () =>
      openReport({
        title: node.path, icon: node.icon, blurb: node.summary,
        arguments: [...pathTokens, ...(current.tokens.includes(REPORT_FLAG) ? [] : [REPORT_FLAG]), ...current.tokens],
      }),
    );
    copyButton.addEventListener("click", async () => {
      if (!navigator.clipboard) return toast("The browser only allows copying on localhost or HTTPS. Select the command text instead.");
      await navigator.clipboard.writeText(preview.textContent);
      toast("Command copied.", "info");
    });
  }

  element.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey) && !event.repeat) runShown();
  });

  function show(route) {
    const node = state.nodes.get(route.path);
    shownPath = route.path;
    if (!node) {
      element.replaceChildren(h("p", { class: "empty", text: `There is no command at “${route.path}”. It may have been renamed.` }));
      return [{ label: "Commands", href: "#/c" }, { label: "Not found" }];
    }
    if (node.kind === "command") renderCommand(node);
    else renderGroup(node);
    return [{ label: "Commands", href: "#/c" }, ...lineage(node).map((item) => ({ label: item.name, href: nodeHash(item) }))];
  }

  return { element, show };
}
