import { formatDuration, h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { closeEditor } from "./activity_editor.js";
import { CONFIRMED_RUNS } from "./catalog.js";
import { consoleText } from "./console_session.js";
import { button, notice, outputActions } from "./widgets.js";

// "stopped" is a task the user ended (Stop, or removing it while it ran); the server remembers that it was asked to, so it is not shown as a failure.
export const statusOf = (summary) => (summary.exit_code === null ? "running" : summary.exit_code === 0 ? "done" : summary.stopped ? "stopped" : "failed");
const MARK_GLYPHS = { done: "check", stopped: "stop", failed: "alert" };
// Whether a run is one of `entries` (catalog.js): the words each begins with, then any switch it must also carry, wherever that sits.
export const isOneOf = (entries, runArguments) => entries.some((entry) => entry.split(" ").every((word, index) => (word.startsWith("--") ? runArguments.includes(word) : runArguments[index] === word)));

function lineOf(summary) {
  const status = statusOf(summary);
  const elapsed = formatDuration((summary.finished_at ?? Date.now() / 1000) - summary.started_at);
  if (status === "running") return `Running for ${elapsed} in ${tildify(summary.working_directory, state.boot.home)}`;
  if (status === "done") return `Finished in ${elapsed}`;
  return status === "stopped" ? `Stopped after ${elapsed}` : `Stopped after ${elapsed} with a problem (code ${summary.exit_code})`;
}

// The header of the Activity panel: what the selected task is, how it is going, and what can be done with it.
export function createHero({ runAgain }) {
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
    const repeatable = status !== "running" && !isOneOf(CONFIRMED_RUNS, summary.arguments);
    line = h("p", { text: lineOf(summary) });
    element.replaceChildren(
      h("span", { class: `task-mark ${status}` }, status === "running" ? h("i", { class: "ring" }) : icon(MARK_GLYPHS[status], 22)),
      h("div", { class: "task-text" }, h("h3", { text: task.title }), line),
      h(
        "div",
        { class: "task-actions" },
        outputActions(() => consoleText(task.terminal), task.title),
        // Stop ends a run where it stands. An editor would lose what is unsaved that way, so it gets a button that closes it the editor's own way.
        status === "running" && !task.editor && button({ label: "Stop", glyph: "stop", small: true, tone: "danger", onclick: () => api.stopRun(task.id).catch((error) => toast(error.message)) }),
        status === "running" && task.editor && button({ label: "Close editor", glyph: "close", small: true, title: "Closes the editor. If something is not saved, you are asked what to do with it.", onclick: () => closeEditor(task) }),
        repeatable && button({ label: task.editor ? "Open again" : "Run again", glyph: "refresh", small: true, onclick: () => runAgain(task) }),
      ),
    );
  }

  // The once-a-second update while a task runs: only the sentence changes, so the Stop button and the spinner stay the same elements.
  function tick() {
    if (shown?.summary.exit_code === null) line.textContent = lineOf(shown.summary);
  }

  return { element, paint, tick };
}
