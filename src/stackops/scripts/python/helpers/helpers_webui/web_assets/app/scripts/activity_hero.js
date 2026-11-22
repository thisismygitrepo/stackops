import { formatDuration, h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { CONFIRMED_RUNS } from "./catalog.js";
import { consoleText } from "./console_session.js";
import { button, notice, outputActions } from "./widgets.js";

// "stopped" is a task the user ended (Stop, or removing it while it ran); the server remembers that it was asked to, so it is not shown as a failure.
export const statusOf = (summary) => (summary.exit_code === null ? "running" : summary.exit_code === 0 ? "done" : summary.stopped ? "stopped" : "failed");
const MARK_GLYPHS = { done: "check", stopped: "stop", failed: "alert" };

function lineOf(summary) {
  const status = statusOf(summary);
  const elapsed = formatDuration((summary.finished_at ?? Date.now() / 1000) - summary.started_at);
  if (status === "running") return `Running for ${elapsed} in ${tildify(summary.working_directory, state.boot.home)}`;
  if (status === "done") return `Finished in ${elapsed}`;
  return status === "stopped" ? `Stopped after ${elapsed}` : `Stopped after ${elapsed} with a problem (code ${summary.exit_code})`;
}

// The header of the Activity panel: what the selected task is, how it is going, and what can be done with it.
export function createHero({ openReport, runAgain }) {
  const element = h("div", { class: "task-hero" });
  let shown = null;
  let line = null;

  function paint(task) {
    shown = task ?? null;
    if (!task) {
      element.replaceChildren(notice({ glyph: "bolt", title: "Nothing running", body: "Whatever you start shows up here, live." }));
      return;
    }
    const { summary } = task;
    const status = statusOf(summary);
    const confirmed = CONFIRMED_RUNS.some((entry) => entry.split(" ").every((word, index) => (word.startsWith("--") ? summary.arguments.includes(word) : summary.arguments[index] === word)));
    const repeatable = status !== "running" && !confirmed;
    line = h("p", { text: lineOf(summary) });
    element.replaceChildren(
      h("span", { class: `task-mark ${status}` }, status === "running" ? h("i", { class: "ring" }) : icon(MARK_GLYPHS[status], 22)),
      h("div", { class: "task-text" }, h("h3", { text: task.title }), line),
      h(
        "div",
        { class: "task-actions" },
        outputActions(() => consoleText(task.terminal), task.title),
        // Several reports are told apart by their file names: a long task is credited with every report written while it ran (see `_finish_run`).
        summary.reports.map((name) => button({ label: summary.reports.length === 1 ? "View report" : name.replace(/\.html$/, "").replaceAll("_", " "), glyph: "report", small: true, onclick: () => openReport({ title: task.title, blurb: "", file: name }) })),
        status === "running" && button({ label: "Stop", glyph: "stop", small: true, tone: "danger", onclick: () => api.stopRun(task.id).catch((error) => toast(error.message)) }),
        repeatable && button({ label: "Run again", glyph: "refresh", small: true, onclick: () => runAgain(task) }),
      ),
    );
  }

  // The once-a-second update while a task runs: only the sentence changes, so the Stop button and the spinner stay the same elements.
  function tick() {
    if (shown?.summary.exit_code === null) line.textContent = lineOf(shown.summary);
  }

  return { element, paint, tick };
}
