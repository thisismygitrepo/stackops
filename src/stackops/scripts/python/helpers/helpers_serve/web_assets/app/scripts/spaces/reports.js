import { h, icon } from "/assets/scripts/dom.js";
import { on } from "/assets/scripts/state.js";
import { REPORTS } from "../catalog.js";
import { replay, rise } from "../motion.js";
import { button, glyphTile, notice } from "../widgets.js";
import { relativeTime } from "../words.js";

const fileUrl = (file) => `/reports/${encodeURIComponent(file)}?at=${Date.now()}`;

export function createReportsSpace({ activity }) {
  const boards = new Map();
  const gallery = h("div", { class: "report-grid" });
  const frames = h("div", { class: "report-frames" });
  const overlay = h("div", { class: "report-overlay", hidden: true });
  const barTitle = h("div", { class: "report-title" });
  const stamp = h("span", { class: "dim" });
  const refresh = button({ label: "Refresh", glyph: "refresh", small: true, onclick: () => generate(boards.get(currentId)) });
  const viewer = h("div", { class: "report-viewer", hidden: true }, h("div", { class: "report-bar" }, h("a", { class: "btn small ghost", href: "#/reports" }, icon("back", 14), h("span", { text: "All reports" })), barTitle, h("span", { class: "spacer" }), stamp, refresh), h("div", { class: "report-body" }, frames, overlay));
  const list = h("div", {}, h("header", { class: "view-head" }, h("div", { class: "view-title" }, h("h1", { text: "Reports" }), h("p", { text: "Rich, browsable snapshots of this machine. Each one opens on its last build and brings itself up to date." }))), gallery);
  const element = h("section", { class: "view reports", hidden: true }, list, viewer);
  let currentId = null;
  let adHocCount = 0;
  const built = (board) => `Built ${relativeTime(board.stamp)}`;

  function addBoard(definition) {
    const board = { ...definition, status: definition.file && !definition.arguments ? "ready" : "idle", stamp: null, runId: null, problem: "", frame: h("iframe", { class: "report-frame", sandbox: "allow-scripts", title: definition.title, hidden: true }) };
    if (board.status === "ready") board.frame.src = fileUrl(definition.file);
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
          h("em", {}, board.stamp ? built(board) : "Open", icon("arrow", 13)),
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
      // A design choice: the last build on disk is shown at once and rebuilt behind it. The report swaps, and scrolls back to its top, when the fresh one lands.
      if (board.file && !board.frame.src) {
        const lastBuild = await fetch(fileUrl(board.file), { method: "HEAD" });
        if (lastBuild.ok) {
          board.frame.src = fileUrl(board.file);
          board.stamp = Date.parse(lastBuild.headers.get("Last-Modified")) / 1000;
          paintViewer();
        }
      }
      const run = await activity.start({ title: `${board.title} report`, emoji: "📊", arguments: board.arguments, interactive: false, reveal: false });
      board.runId = run.id;
      const outcome = await run.done;
      const file = outcome.reports.includes(board.file) ? board.file : outcome.reports[0];
      // A check that found something to report exits non-zero and still writes its report, so the report itself is what counts.
      if (file) {
        board.frame.src = fileUrl(file);
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
    const refreshing = board.status === "running" && Boolean(board.frame.src);
    for (const other of boards.values()) other.frame.hidden = other !== board || !other.frame.src;
    // A report being rebuilt stays readable with nothing moving over it; only a failed rebuild dims it, under its notice.
    board.frame.classList.toggle("stale", board.status === "failed");
    barTitle.replaceChildren(glyphTile(board.glyph, board.hue, 30), h("strong", { text: board.title }));
    stamp.textContent = [board.stamp && built(board), refreshing && "Refreshing…"].filter(Boolean).join(" · ");
    refresh.hidden = !board.arguments;
    refresh.disabled = board.status === "running";
    overlay.hidden = board.status === "ready" || refreshing;
    if (board.status === "running") {
      overlay.replaceChildren(h("div", { class: "loader", "aria-hidden": "true" }, h("i"), h("i"), h("i")), h("h2", { text: "Building your report…" }), h("p", { text: "Gathering the latest from this machine." }));
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

  // The same report asked for again goes back to its board and is rebuilt there, so repeats do not pile up cards and loaded pages.
  function openAdHoc({ title, blurb, arguments: reportArguments, file }) {
    const wanted = reportArguments?.join(" ") ?? file;
    let board = [...boards.values()].find((other) => (other.arguments?.join(" ") ?? other.file) === wanted);
    if (!board) {
      adHocCount += 1;
      board = addBoard({ id: `custom-${adHocCount}`, glyph: "report", hue: 290, title, blurb: blurb || "Opened from a tool.", arguments: reportArguments, file: file ?? null });
    } else if (!board.arguments) board.frame.src = fileUrl(file);
    else if (board.status === "ready" || board.status === "failed") generate(board);
    location.hash = `#/reports/${board.id}`;
  }

  // Some reports depend on the working folder, so a change of folder makes every built one due again; the one on show is rebuilt at once.
  on("workingDirectory", () => {
    for (const board of boards.values()) if (board.arguments && board.status === "ready") board.status = "idle";
    const current = boards.get(currentId);
    if (current?.status === "idle" && !element.hidden && !viewer.hidden) generate(current);
  });

  return { element, show, openAdHoc };
}
