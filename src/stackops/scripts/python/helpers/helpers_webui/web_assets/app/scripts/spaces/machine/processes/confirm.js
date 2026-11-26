import { h } from "/assets/scripts/dom.js";
import { openDialog } from "../../../overlays.js";
import { button, glyphTile, pill, segmented } from "../../../widgets.js";
import { ancestors, descendants } from "./model.js";
import { ROLES, memoryText, processCount } from "./words.js";

const WAYS = {
  quit: {
    verb: "Stop",
    one: "It is asked to quit, so it can save its work and close. It is free to ignore the request.",
    many: "Each one is asked to quit, so it can save its work and close. A process is free to ignore the request.",
  },
  force: { verb: "Force stop", one: "It is ended at once and saves nothing. Use this when asking did not work.", many: "Each one is ended at once and saves nothing. Use this when asking did not work." },
};

// The last stop before anything is ended: every process by name, what stopping it costs, and the way it will be stopped.
// Resolves to null when the person backs out, or to `{ processes, force }` with the processes in the order they will be stopped.
export function confirmStop({ processes, force, ask }) {
  const dialog = openDialog({ label: "Stop processes", size: "procs-confirm" });
  const chosen = new Set(processes);
  // What the chosen ones started and would leave running: stopping a process does not stop these with it.
  const started = [...new Set(processes.flatMap(descendants))].filter((process) => !chosen.has(process) && process.lock === "");
  let way = force ? "force" : "quit";
  let withStarted = false;

  const title = h("h2");
  const lede = h("p");
  const list = h("ul", { class: "procs-confirm-list" });
  const go = button({ label: "Stop", glyph: "stop", tone: "danger", onclick: () => dialog.close({ processes: targets(), force: way === "force" }) });
  const agree = h("input", { class: "procs-check", type: "checkbox", onchange: () => paint() });
  const agreeText = h("span");
  const agreeRow = h("label", { class: "procs-ack" }, agree, agreeText);
  const family = h("input", {
    class: "procs-check", type: "checkbox",
    onchange: () => {
      withStarted = family.checked;
      paint();
    },
  });
  const familyRow = h("label", { class: "procs-family", hidden: started.length === 0 }, family, h("span", { text: `Also stop the ${processCount(started.length)} ${processes.length === 1 ? "it" : "they"} started` }));
  const wayPick = segmented([["quit", "Ask to quit"], ["force", "Force stop"]], (picked) => {
    way = picked;
    paint();
  });

  // A process goes before what it started, so a program that restarts its helpers is gone before they are.
  const targets = () => [...processes, ...(withStarted ? started : [])].map((process) => ({ process, depth: ancestors(process).length })).sort((left, right) => left.depth - right.depth).map((item) => item.process);

  function paint() {
    const all = targets();
    const subject = all.length === 1 ? all[0].name : processCount(all.length);
    const risky = all.filter((process) => ROLES[process.role]?.risky);
    const hosts = risky.some((process) => process.role !== "system");
    wayPick.set(way);
    title.textContent = `${WAYS[way].verb} ${subject}?`;
    lede.textContent = WAYS[way][all.length === 1 ? "one" : "many"];
    go.lastChild.textContent = `${WAYS[way].verb} ${subject}`;
    list.replaceChildren(
      ...all.map((process) => {
        const role = ROLES[process.role];
        return h(
          "li",
          {},
          h("strong", { text: process.name }),
          h("span", { class: "dim", text: `ID ${process.pid} · ${process.user}${chosen.has(process) ? "" : ` · started by ${process.parentRef.name}`}` }),
          role ? pill(role.label, role.risky ? "bad" : "accent") : h("span"),
          h("b", { class: "num", text: memoryText(process.memory) }),
          role && h("p", { text: role.warning }),
        );
      }),
    );
    agreeRow.hidden = risky.length === 0;
    agreeText.textContent = hosts ? "I understand that this page can stop working." : "I understand that this can disturb the system.";
    go.disabled = risky.length > 0 && !agree.checked;
  }

  dialog.body.append(
    h("header", { class: "procs-confirm-head" }, glyphTile("stop", 350, 46), h("div", {}, title, lede)),
    wayPick.element,
    list,
    familyRow,
    agreeRow,
    h("div", { class: "dialog-actions" }, ask, button({ label: processes.length === 1 ? "Keep it running" : "Keep them running", onclick: () => dialog.close(null) }), go),
  );
  paint();
  return dialog.closed.then((answer) => answer ?? null);
}
