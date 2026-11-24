import { formatDuration, h, icon, toast } from "/assets/scripts/dom.js";
import { api } from "/assets/scripts/state.js";
import { consoleText } from "../../console_session.js";
import { button } from "../../widgets.js";

// The console draws what arrives a moment after it arrives, so what a finished run printed is read this long after its end is known.
const CONSOLE_SETTLE_MILLISECONDS = 80;

// Starts a command as a task that stays out of the Activity panel while a sheet watches it. None of these commands asks anything, so the run
// is told not to. `ended` resolves when it is over, with whether it worked and everything it printed. `show` brings the task into the panel.
export async function startWatched(activity, { title, emoji, arguments: runArguments }) {
  const task = await activity.start({ title, emoji, arguments: runArguments, interactive: false, reveal: false });
  const text = () => consoleText(task.terminal);
  const ended = task.done.then(async (summary) => {
    await new Promise((resolve) => setTimeout(resolve, CONSOLE_SETTLE_MILLISECONDS));
    return { ok: summary.exit_code === 0, stopped: Boolean(summary.stopped), text: text() };
  });
  return { id: task.id, startedAt: task.summary.started_at, ended, text, stop: () => api.stopRun(task.id).catch((error) => toast(error.message)), show: () => activity.reveal(task.id) };
}

// A sheet that watches a run keeps it out of the Activity panel. When the sheet goes while the run is still on, the run is shown there, so
// nothing keeps running where nobody can see it. `current()` is the run on its way, or null.
export function showRunWhenClosed(sheet, current) {
  let open = true;
  sheet.closed.then(() => {
    open = false;
    current()?.show();
  });
  return () => open;
}

// Brings a run's card, or how it ended, into view: it stands under everything else in the sheet, which is often below the fold.
export function bringIntoView(element) {
  requestAnimationFrame(() => element.scrollIntoView({ block: "nearest", behavior: "smooth" }));
}

// The run on its way, as a card: what is happening, how long it has taken, how far it is when the command says so, and the two ways out.
// `onShow` closes the sheet, which brings the task into the Activity panel.
export function runCard({ title, onStop, onShow }) {
  const note = h("span", { class: "sec-run-note" });
  const clock = h("span", { class: "sec-run-clock num" });
  const bar = h("i");
  const meter = h("span", { class: "sec-run-meter", hidden: true }, bar);
  const started = Date.now();
  const tick = () => (clock.textContent = formatDuration((Date.now() - started) / 1000));
  const timer = setInterval(tick, 1000);
  tick();
  const element = h(
    "div",
    { class: "sec-run", role: "status" },
    h("i", { class: "ring" }),
    h("div", { class: "sec-run-text" }, h("strong", { text: title }), note, meter),
    clock,
    h("div", { class: "sec-run-actions" }, button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", title: "Closes this and opens the task in the Activity panel", onclick: onShow }), button({ label: "Stop", glyph: "stop", small: true, onclick: onStop })),
  );
  return {
    element,
    say: (text) => (note.textContent = text),
    share(fraction) {
      meter.hidden = fraction === null;
      bar.style.setProperty("--share", String(fraction ?? 0));
    },
    end: () => clearInterval(timer),
  };
}

// How a run ended, as a card: a mark in a tone, a title, a sentence, then whatever the view adds (a link, a path, a list) and its buttons.
export function outcomeCard({ tone, title, body, extra = [], actions = [] }) {
  return h(
    "div",
    { class: `sec-outcome ${tone}`, role: "status" },
    h("span", { class: "sec-outcome-mark" }, icon(tone === "good" ? "check" : "alert", 20)),
    h("div", { class: "sec-outcome-text" }, h("h3", { text: title }), body && h("p", { text: body }), extra),
    actions.filter(Boolean).length > 0 && h("div", { class: "sec-outcome-actions" }, actions),
  );
}
