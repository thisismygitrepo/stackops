import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { REPORTS } from "../catalog.js";
import { replay, rise } from "../motion.js";
import { button, glyphTile, notice } from "../widgets.js";

export function createReportsSpace({ activity }) {
  const boards = new Map();
  const gallery = h("div", { class: "report-grid" });
  const frames = h("div", { class: "report-frames" });
  const overlay = h("div", { class: "report-overlay", hidden: true });
  const barTitle = h("div", { class: "report-title" });
  const stamp = h("span", { class: "dim" });
  const refresh = button({ label: "Refresh", glyph: "refresh", small: true, onclick: () => generate(boards.get(currentId)) });
  const viewer = h("div", { class: "report-viewer", hidden: true }, h("div", { class: "report-bar" }, h("a", { class: "btn small ghost", href: "#/reports" }, icon("back", 14), h("span", { text: "All reports" })), barTitle, h("span", { class: "spacer" }), stamp, refresh), h("div", { class: "report-body" }, frames, overlay));
  const list = h("div", {}, h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { text: "Reports" }), h("p", { text: "Rich, browsable snapshots of this machine. Each one is built fresh when you open it." }))), gallery);
  const element = h("section", { class: "view reports", hidden: true }, list, viewer);
  let currentId = null;
  let adHocCount = 0;

  function addBoard(definition) {
    const board = { ...definition, status: definition.file && !definition.arguments ? "ready" : "idle", stamp: null, runId: null, problem: "", frame: h("iframe", { class: "report-frame", sandbox: "allow-scripts", title: definition.title, hidden: true }) };
    if (board.status === "ready") board.frame.src = `/reports/${encodeURIComponent(definition.file)}?opened=${Date.now()}`;
    boards.set(board.id, board);
    frames.append(board.frame);
    return board;
  }

  function paintGallery() {
    gallery.replaceChildren(
      ...[...boards.values()].map((board) =>
        h(
          "a",
          { class: "report-card lit", href: `#/reports/${board.id}` },
          h("div", { class: "report-art", "aria-hidden": "true" }, h("i"), h("i"), h("i"), h("i")),
          glyphTile(board.glyph, board.hue, 44),
          h("strong", { text: board.title }),
          h("span", { text: board.blurb }),
          h("em", {}, board.stamp ? `Built ${formatClock(board.stamp)}` : "Open", icon("arrow", 13)),
        ),
      ),
    );
    rise(gallery);
  }

  async function generate(board) {
    if (!board.arguments) return;
    if (board.runId) activity.remove(board.runId);
    board.runId = null;
    board.status = "running";
    paintViewer();
    try {
      const run = await activity.start({ title: `${board.title} report`, emoji: "📊", arguments: board.arguments, interactive: false, reveal: false });
      board.runId = run.id;
      const outcome = await run.done;
      const file = outcome.reports.includes(board.file) ? board.file : outcome.reports[0];
      // A check that found something to report exits non-zero and still writes its report, so the report itself is what counts.
      if (file) {
        board.frame.src = `/reports/${encodeURIComponent(file)}?generated=${Date.now()}`;
        board.status = "ready";
        board.stamp = Date.now() / 1000;
        board.runId = null;
        activity.remove(run.id);
      } else {
        board.status = "failed";
        board.problem = outcome.exit_code === 0 ? "It finished without producing a report." : "It stopped before the report was ready.";
      }
    } catch (error) {
      board.status = "failed";
      board.problem = error.message;
    }
    if (boards.has(board.id)) paintViewer();
  }

  function paintViewer() {
    const board = boards.get(currentId);
    if (!board) return;
    for (const other of boards.values()) other.frame.hidden = other !== board || !other.frame.src;
    board.frame.classList.toggle("stale", board.status !== "ready");
    barTitle.replaceChildren(glyphTile(board.glyph, board.hue, 30), h("strong", { text: board.title }));
    stamp.textContent = board.stamp ? `Built ${formatClock(board.stamp)}` : "";
    refresh.hidden = !board.arguments;
    refresh.disabled = board.status === "running";
    overlay.hidden = board.status === "ready";
    if (board.status === "running") {
      overlay.replaceChildren(h("div", { class: "loader", "aria-hidden": "true" }, h("i"), h("i"), h("i")), h("h2", { text: board.frame.src ? "Refreshing…" : "Building your report…" }), h("p", { text: "Gathering the latest from this machine." }));
    } else if (board.status === "failed") {
      overlay.replaceChildren(
        notice({
          glyph: "alert", tone: "bad", title: "The report could not be built", body: board.problem,
          action: h("div", { class: "dialog-actions" }, board.runId && button({ label: "Show what happened", small: true, onclick: () => activity.reveal(board.runId) }), button({ label: "Try again", glyph: "refresh", small: true, tone: "primary", onclick: () => generate(board) })),
        }),
      );
    }
  }

  REPORTS.forEach((report, index) => addBoard({ ...report, hue: [252, 20, 340, 165, 200][index % 5] }));
  paintGallery();

  function show(route) {
    const board = boards.get(route[0]);
    list.hidden = Boolean(board);
    viewer.hidden = !board;
    element.classList.toggle("viewing", Boolean(board));
    if (!board) return paintGallery();
    if (currentId !== board.id) replay(viewer, "enter");
    currentId = board.id;
    if (board.status === "idle") generate(board);
    else paintViewer();
  }

  function openAdHoc({ title, blurb, arguments: reportArguments, file }) {
    adHocCount += 1;
    const board = addBoard({ id: `custom-${adHocCount}`, glyph: "report", hue: 290, title, blurb: blurb || "Opened from a tool.", arguments: reportArguments, file: file ?? null });
    location.hash = `#/reports/${board.id}`;
  }

  return { element, show, openAdHoc };
}
