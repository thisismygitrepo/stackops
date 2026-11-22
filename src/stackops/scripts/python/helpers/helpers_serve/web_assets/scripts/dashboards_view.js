import { formatClock, h, icon, shellQuote } from "./dom.js";
import { DASHBOARDS } from "./presets.js";
import { nodeHash, on, state } from "./state.js";

export function createDashboardsView({ dock }) {
  const boards = new Map();
  const strip = h("div", { class: "panel-tabs", role: "tablist" });
  const bar = h("div", { class: "panel-bar" });
  const body = h("div", { class: "panel-body" });
  const element = h("section", { class: "panel" }, strip, bar, body);
  let currentId = DASHBOARDS[0].id;
  let adHocCount = 0;

  function addBoard(definition, closable) {
    const board = {
      ...definition,
      status: "idle", stamp: null, runId: null, problem: "",
      frame: h("iframe", { class: "report-frame", sandbox: "allow-scripts", allow: "clipboard-write", title: definition.title, hidden: true }),
      overlay: h("div", { class: "panel-state", hidden: true }),
      tab: h("a", { class: "panel-tab", role: "tab", href: `#/d/${definition.id}` }, h("span", { text: definition.icon }), h("span", { text: definition.title })),
    };
    boards.set(board.id, board);
    strip.append(board.tab);
    body.append(board.frame, board.overlay);
    if (closable) {
      const closer = h("button", { class: "panel-tab-close", title: "Close this report", "aria-label": "Close this report" }, icon("close", 12));
      closer.addEventListener("click", () => {
        board.tab.remove();
        closer.remove();
        board.frame.remove();
        board.overlay.remove();
        boards.delete(board.id);
        if (board.runId) dock.close(board.runId);
        if (currentId === board.id) currentId = DASHBOARDS[0].id;
        location.hash = "#/d";
        paint();
      });
      board.tab.classList.add("closable");
      strip.append(closer);
    }
    return board;
  }

  async function generate(board) {
    if (board.runId) dock.close(board.runId);
    board.runId = null;
    board.status = "running";
    paint();
    try {
      const folder = state.settings.workingDirectory;
      const run = await dock.start({ arguments: board.arguments, interactive: false, reveal: false });
      board.runId = run.id;
      const outcome = await run.done;
      // The working folder changed while this was being built, so what was built belongs to the old folder: build it again for the new one.
      if (folder !== state.settings.workingDirectory) return generate(board);
      // The run lists every report written while it was going, whoever wrote it, so a board that knows its file takes that file or none.
      const file = board.file ? outcome.reports.find((name) => name === board.file) : outcome.reports[0];
      if (outcome.exit_code === 0 && file) {
        const url = `/reports/${encodeURIComponent(file)}?generated=${Date.now()}`;
        // A frame that already holds a report has it replaced: assigning `src` again would add a Back-button step that changes nothing.
        if (board.frame.dataset.loaded) board.frame.contentWindow.location.replace(url);
        else board.frame.src = url;
        board.frame.dataset.loaded = "true";
        board.status = "ready";
        board.stamp = Date.now() / 1000;
        board.runId = null;
        dock.close(run.id);
      } else {
        board.status = "failed";
        board.problem = outcome.exit_code === 0 ? "The command finished without writing a report." : `The report command exited with code ${outcome.exit_code}.`;
      }
    } catch (error) {
      board.status = "failed";
      board.problem = error.message;
    }
    if (boards.has(board.id)) paint();
  }

  function paint() {
    const current = boards.get(currentId);
    for (const board of boards.values()) {
      const shown = board === current;
      const loaded = board.frame.dataset.loaded === "true";
      board.tab.setAttribute("aria-selected", String(shown));
      board.frame.hidden = !shown || !loaded;
      board.frame.classList.toggle("stale", board.status !== "ready");
      board.overlay.hidden = !shown || board.status === "ready" || board.status === "idle";
      board.overlay.classList.toggle("over", board.status === "running" && loaded);
      if (board.status === "running" && loaded) {
        board.overlay.replaceChildren(h("div", { class: "pill" }, h("span", { class: "spinner" }), "Refreshing the report…"));
      } else if (board.status === "running") {
        board.overlay.replaceChildren(
          h("span", { class: "spinner large" }),
          h("h2", { text: "Generating the report…" }),
          h("code", { text: ["stackops", ...board.arguments].map(shellQuote).join(" ") }),
        );
      } else if (board.status === "failed") {
        board.overlay.replaceChildren(
          h("h2", { text: "The report could not be generated" }),
          h("p", { text: board.problem }),
          h(
            "div",
            { class: "row" },
            board.runId && h("button", { class: "button", onclick: () => dock.focus(board.runId) }, icon("terminal", 14), "Show the output"),
            h("button", { class: "button primary", onclick: () => generate(board) }, icon("refresh", 14), "Try again"),
          ),
        );
      }
    }
    bar.replaceChildren(
      h("div", { class: "about" }, h("strong", { text: current.title }), h("span", { text: current.blurb })),
      current.stamp && h("span", { class: "stamp", text: `Generated ${formatClock(current.stamp)}` }),
      ...current.actions
        .filter((action) => state.nodes.has(action.path))
        .map((action) => h("a", { class: "button small", href: nodeHash(state.nodes.get(action.path)), title: `stackops ${action.path}`, text: action.label })),
      h("button", { class: "button small", disabled: current.status === "running", onclick: () => generate(current) }, icon("refresh", 13), "Refresh"),
    );
  }

  for (const definition of DASHBOARDS) addBoard(definition, false);
  // Some reports depend on the working folder, so a change of folder makes every built one due again; the one on show is rebuilt at once.
  on("workingDirectory", () => {
    for (const board of boards.values()) if (board.status === "ready") board.status = "idle";
    const current = boards.get(currentId);
    if (current.status === "idle" && !element.hidden) generate(current);
  });

  function show(route) {
    const board = boards.get(route.id) ?? boards.get(currentId);
    currentId = board.id;
    if (board.status === "idle") generate(board);
    else paint();
    return [{ label: "Dashboards", href: "#/d" }, { label: board.title }];
  }

  function openAdHoc({ title, icon: emoji, blurb, arguments: reportArguments }) {
    adHocCount += 1;
    const board = addBoard({ id: `report-${adHocCount}`, icon: emoji || "📄", title, blurb, arguments: reportArguments, file: null, actions: [] }, true);
    location.hash = `#/d/${board.id}`;
  }

  return { element, show, openAdHoc };
}
