import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { button, glyphTile, iconButton } from "../../../widgets.js";
import { OUTCOMES, cpuText, memoryText, processCount } from "./words.js";

// What the last stop did, process by process: a banner above the list, and a line under each process that is still listed and did not stop.
// `onForce` is handed the processes to force, by key; it asks before doing anything.
export function createOutcome({ onForce, onChange }) {
  const element = h("div", { class: "procs-outcome-holder" });
  let report = null;
  let notes = new Map();

  function noteFor(entry) {
    if (entry.outcome === "still_running") {
      return {
        tone: "warn", text: `${report.force ? "Forced to stop" : "Asked to quit"} at ${formatClock(report.at)} and still running.`,
        action: report.force ? null : { label: "Force stop", run: () => onForce([entry.key]) },
      };
    }
    if (entry.outcome === "not_allowed") return { tone: "bad", text: "The system did not let StackOps stop it.", action: null };
    if (entry.outcome === "failed") return { tone: "bad", text: `It could not be stopped. ${entry.error ?? ""}`.trim(), action: null };
    return null;
  }

  function paint() {
    notes = new Map((report?.entries ?? []).map((entry) => [entry.key, noteFor(entry)]).filter(([, note]) => note));
    if (!report) return element.replaceChildren();
    const { entries } = report;
    const stopped = entries.filter((entry) => entry.outcome === "stopped");
    const lingering = entries.filter((entry) => entry.outcome === "still_running");
    const settled = entries.every((entry) => entry.outcome === "stopped" || entry.outcome === "already_gone");
    const one = entries.length === 1;
    const title = settled
      ? stopped.length > 0 ? `Stopped ${stopped.length === 1 ? stopped[0].name : processCount(stopped.length)}` : `${one ? entries[0].name : "They"} had already ended`
      : stopped.length === 0 ? "Nothing was stopped" : `Stopped ${stopped.length} of ${processCount(entries.length)}`;
    const them = lingering.length === 1 ? "it" : "them";
    const waiting = lingering.length === 0 ? "" : report.force
      ? `${lingering.length === 1 ? "One" : lingering.length} did not end even when forced.`
      : `${one ? "It" : lingering.length === 1 ? "One" : lingering.length} did not quit when asked. Give ${them} a moment, or force ${them}.`;
    element.replaceChildren(
      h(
        "section",
        { class: `procs-banner ${settled ? "good" : "warn"}` },
        h("span", { class: `task-mark ${settled ? "done" : "failed"}` }, icon(settled ? "check" : "alert", 22)),
        h(
          "div",
          { class: "procs-banner-text" },
          h("h2", { text: title }),
          waiting && h("p", { text: waiting }),
          h(
            "ul",
            { class: "procs-outcome" },
            entries.map((entry) =>
              h(
                "li",
                { class: OUTCOMES[entry.outcome].tone },
                icon(OUTCOMES[entry.outcome].tone === "good" || entry.outcome === "already_gone" ? "check" : "alert", 13),
                h("span", { text: `${entry.name}, ID ${entry.pid}` }),
                h("b", { text: `${OUTCOMES[entry.outcome].text}${entry.late ? " a moment later" : ""}` }),
              ),
            ),
          ),
          h("small", { class: "dim", text: `${report.force ? "Forced" : "Asked"} at ${formatClock(report.at)}` }),
        ),
        lingering.length > 0 && !report.force && button({ label: lingering.length === 1 ? `Force stop ${lingering[0].name}` : `Force stop the ${lingering.length} still running`, glyph: "stop", small: true, onclick: () => onForce(lingering.map((entry) => entry.key)) }),
        iconButton("close", "Dismiss", () => clear()),
      ),
    );
  }

  // `entries` name each process as it was when it was stopped: `{ key, name, pid, outcome, error }`.
  function show({ force, entries }) {
    report = { force, at: Date.now() / 1000, entries: entries.map((entry) => ({ ...entry, late: false })) };
    paint();
  }

  function clear() {
    report = null;
    paint();
    onChange();
  }

  // A process that was still running when the answer came may end a moment later. The banner follows it.
  function follow(model) {
    const ended = (report?.entries ?? []).filter((entry) => entry.outcome === "still_running" && (model.byKey.get(entry.key)?.status ?? "zombie") === "zombie");
    for (const entry of ended) Object.assign(entry, { outcome: "stopped", late: true });
    if (ended.length > 0) paint();
  }

  return { element, show, clear, follow, noteOf: (key) => notes.get(key) ?? null };
}

// The bar that stays in view while something is selected: how many, what they use together, and the two ways to stop them.
export function createTray({ onClear, onStop }) {
  const title = h("strong");
  const note = h("span");
  const clear = button({ label: "Clear", tone: "ghost", onclick: onClear });
  const quit = button({ label: "Stop", glyph: "stop", tone: "primary", title: "Ask them to quit, so they can save their work first", onclick: () => onStop(false) });
  const force = button({ label: "Force stop", title: "End them at once, without a chance to save", onclick: () => onStop(true) });
  const element = h("div", { class: "tray procs-tray", hidden: true }, glyphTile("stop", 350, 38), h("div", { class: "procs-tray-text" }, title, note), h("span", { class: "spacer" }), clear, force, quit);
  return {
    element,
    paint({ processes, busy }) {
      element.hidden = processes.length === 0;
      const memory = processes.reduce((sum, process) => sum + (process.memory ?? 0), 0);
      const cpu = processes.reduce((sum, process) => sum + (process.cpu ?? 0), 0);
      title.textContent = busy ? "Stopping" : `${processCount(processes.length)} selected`;
      note.textContent = busy ? "Waiting to see them go." : `${processes.length === 1 ? "It uses" : "Together they use"} ${memoryText(memory)} of memory and ${cpuText(cpu)} CPU.`;
      for (const control of [clear, quit, force]) control.disabled = busy;
    },
  };
}
