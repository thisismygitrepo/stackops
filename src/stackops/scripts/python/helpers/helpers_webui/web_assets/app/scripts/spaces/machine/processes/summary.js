import { h, icon } from "/assets/scripts/dom.js";
import { countUp } from "../../../motion.js";
import { formatBytes } from "../../../words.js";
import { FLAGS, topGroups } from "./model.js";
import { createTrend } from "./trend.js";
import { cpuText, memoryText, processCount } from "./words.js";

const TOP_COUNT = 4;
const TREND_LIMIT = 40;
// A few ended processes waiting to be collected are normal. This many is worth a sentence.
const ENDED_NOTICE = 20;
const LEVELS = { cpu: [70, 90], memory: [80, 92] };

function gauge(label, [warnAt, badAt]) {
  const fill = h("i");
  const element = h("div", { class: "procs-gauge", role: "meter", "aria-label": label, "aria-valuemin": "0", "aria-valuemax": "100" }, fill);
  return {
    element,
    set(percent) {
      fill.style.setProperty("--share", String(Math.min(percent, 100) / 100));
      element.dataset.level = percent >= badAt ? "bad" : percent >= warnAt ? "warn" : "";
      element.setAttribute("aria-valuenow", String(Math.round(percent)));
    },
  };
}

// The groups that use the most of one thing, as bars measured against the largest. The rows are made once and filled in again at every reading,
// so a row being clicked is never swapped for a new one under the pointer.
function topList({ field, format, onReveal }) {
  const empty = h("li", { class: "procs-top-empty dim" });
  const rows = Array.from({ length: TOP_COUNT }, () => {
    const name = h("span", { class: "procs-top-name" });
    const size = h("b");
    const figure = h("span", { class: "num" });
    const bar = h("i", { class: "procs-bar" });
    const row = { process: null, name, size, figure, bar };
    row.element = h("li", {}, h("button", { class: "procs-top-row", type: "button", onclick: () => onReveal(row.process) }, name, size, figure, bar));
    return row;
  });
  return {
    element: h("ol", { class: "procs-top" }, rows.map((row) => row.element), empty),
    paint(model, emptyText) {
      const groups = topGroups(model, field, TOP_COUNT);
      rows.forEach((row, index) => {
        const process = groups[index];
        row.element.hidden = !process;
        if (!process) return;
        row.process = process;
        row.name.textContent = process.name;
        row.size.hidden = process.groupSize === 0;
        row.size.textContent = String(process.groupSize + 1);
        row.figure.textContent = format(process[field]);
        row.bar.style.setProperty("--share", String(process[field] / groups[0][field]));
        row.element.firstChild.title = process.groupSize ? `${process.name} and the ${processCount(process.groupSize)} it started. Show them in the list.` : `Show ${process.name} in the list.`;
      });
      empty.hidden = groups.length > 0;
      empty.textContent = emptyText;
    },
  };
}

function factLine(glyph, onclick) {
  const text = h("span");
  const element = h("button", { class: "procs-fact", type: "button", onclick }, icon(glyph, 15), text, icon("arrow", 13));
  return { element, text };
}

// The top of the page: how busy the processor and the memory are, what uses the most of each, and what stands out in the list.
export function createSummary({ onReveal, onFilter }) {
  const cpuFigure = h("strong", { class: "procs-figure", text: "—" });
  const cpuNote = h("span", { class: "procs-figure-note" });
  const cpuGauge = gauge("CPU in use", LEVELS.cpu);
  const cpuTrend = createTrend({ label: "CPU in use", limit: TREND_LIMIT });
  const cpuTop = topList({ field: "groupCpu", format: cpuText, onReveal });
  const memoryFigure = h("strong", { class: "procs-figure", text: "—" });
  const memoryNote = h("span", { class: "procs-figure-note" });
  const memoryGauge = gauge("Memory in use", LEVELS.memory);
  const memoryTop = topList({ field: "groupMemory", format: memoryText, onReveal });
  const countFigure = h("strong", { class: "procs-figure", text: "—" });
  const countNote = h("span", { class: "procs-figure-note" });
  // What stands out in the list, each line a way to see just those.
  const facts = [
    { ...factLine("bolt", () => onFilter({ scope: "all", flags: ["cpu"], status: "" })), count: (processes) => processes.filter(FLAGS.cpu).length, words: "heavy on CPU" },
    { ...factLine("layers", () => onFilter({ scope: "all", flags: ["memory"], status: "" })), count: (processes) => processes.filter(FLAGS.memory).length, words: "heavy on memory" },
    { ...factLine("plug", () => onFilter({ scope: "all", flags: ["ports"], status: "" })), count: (processes) => processes.filter(FLAGS.ports).length, words: "listening on a port" },
    { ...factLine("clock", () => onFilter({ scope: "all", flags: [], status: "stopped" })), count: (processes) => processes.filter((process) => process.status === "stopped").length, words: "paused" },
    { ...factLine("check", () => onFilter({ scope: "all", flags: [], status: "zombie" })), count: (processes) => processes.filter((process) => process.status === "zombie").length, words: "ended, still listed" },
  ];
  const starter = h("button", { class: "link", type: "button" });
  const starterTail = h("span");
  const endedNote = h("p", { class: "procs-aside" }, "An ended process stays listed until the program that started it collects it. It uses no memory and no CPU. ", starter, starterTail);
  const hidden = h("p", { class: "procs-aside" });
  const history = [];
  let endedParent = null;
  starter.addEventListener("click", () => onReveal(endedParent));

  const card = (title, ...content) => h("section", { class: "procs-card" }, h("span", { class: "overline", text: title }), ...content);
  const element = h(
    "div",
    { class: "procs-cards" },
    card("CPU", h("div", { class: "procs-headline" }, cpuFigure, cpuNote, h("span", { class: "spacer" }), cpuTrend.element), cpuGauge.element, h("h3", { text: "Using the most" }), cpuTop.element),
    card("Memory", h("div", { class: "procs-headline" }, memoryFigure, memoryNote), memoryGauge.element, h("h3", { text: "Using the most" }), memoryTop.element),
    card("Processes", h("div", { class: "procs-headline" }, countFigure, countNote), h("div", { class: "procs-facts" }, facts.map((fact) => fact.element)), endedNote, hidden),
  );

  function paint(model) {
    const { machine, processes } = model;
    if (machine.cpu !== null && history.at(-1)?.at !== model.taken_at) history.push({ at: model.taken_at, value: machine.cpu });
    if (history.length > TREND_LIMIT) history.shift();
    cpuFigure.textContent = machine.cpu === null ? "—" : `${Math.round(machine.cpu)}%`;
    cpuNote.textContent = machine.cpu === null ? "Measuring" : `of ${machine.cores} cores`;
    cpuGauge.set(machine.cpu ?? 0);
    cpuTrend.paint(history.map((reading) => reading.value));
    cpuTop.paint(model, machine.cpu === null ? "The first figures take a moment." : "Nothing is working hard right now.");
    memoryFigure.textContent = formatBytes(machine.memory_used);
    memoryNote.textContent = `of ${formatBytes(machine.memory_total)} in use`;
    memoryGauge.set((machine.memory_used / machine.memory_total) * 100);
    memoryTop.paint(model, "No memory figures can be read.");
    countUp(countFigure, processes.length);
    countNote.textContent = `${processes.filter((process) => process.mine).length.toLocaleString()} yours`;

    for (const fact of facts) {
      const count = fact.count(processes);
      fact.element.hidden = count === 0;
      fact.text.textContent = `${count.toLocaleString()} ${fact.words}`;
    }
    const gone = processes.filter((process) => process.status === "zombie");
    const starters = new Map();
    for (const process of gone) starters.set(process.parent, (starters.get(process.parent) ?? 0) + 1);
    const [parentPid, started] = [...starters].sort((left, right) => right[1] - left[1])[0] ?? [0, 0];
    endedParent = model.byPid.get(parentPid) ?? null;
    endedNote.hidden = gone.length < ENDED_NOTICE;
    starter.hidden = starterTail.hidden = !endedParent;
    starter.textContent = endedParent ? `${endedParent.name}, ID ${endedParent.pid},` : "";
    starterTail.textContent = ` started ${started === gone.length ? "all" : started.toLocaleString()} of them.`;
    const unread = processes.filter((process) => process.memory === null && process.status !== "zombie").length;
    hidden.hidden = unread === 0;
    hidden.textContent = `${unread === 1 ? "One process belongs" : `${unread.toLocaleString()} processes belong`} to the system or another account. ${unread === 1 ? "Its" : "Their"} CPU and memory cannot be read unless StackOps runs as an administrator.`;
  }

  return { element, paint };
}
