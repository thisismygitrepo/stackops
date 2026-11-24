import { h, icon } from "/assets/scripts/dom.js";
import { HEAVY_CPU, HEAVY_MEMORY, LOCKS, ROLES, ageText, cpuText, memoryText, processCount, startedText, statusOf } from "./words.js";

const PORT_LIMIT = 2;
const UNREAD = "Only its owner or an administrator can read this.";

// Written only when it changed, so text a person has selected stays selected from one reading to the next.
function put(node, text) {
  if (node.textContent !== text) node.textContent = text;
}

function measure() {
  const figure = h("span", { class: "num" });
  const bar = h("i", { class: "procs-bar" });
  const cell = h("td", { class: "procs-measure" }, figure, bar);
  return {
    cell,
    set(value, scale, heavyFrom, format) {
      put(figure, format(value));
      bar.hidden = value === null;
      bar.style.setProperty("--share", String(Math.min((value ?? 0) / scale, 1)));
      cell.classList.toggle("heavy", (value ?? 0) >= heavyFrom);
      cell.title = value === null ? UNREAD : "";
    },
  };
}

// One line of the list. It is made once for a process and filled in again at every reading, so the pointer, the focus and a half-made click
// stay on the same element. `view` is the page's: what the scales are, whether the list is a tree, and what to do on each action.
export function createRow(view) {
  const check = h("input", { class: "procs-check", type: "checkbox", "data-part": "check" });
  const twist = h("button", { class: "procs-twist", type: "button", "data-part": "twist" }, icon("chevron", 13));
  const name = h("button", { class: "procs-open", type: "button", "data-part": "open", title: "Show everything about this process" });
  const size = h("b", { class: "procs-size" });
  const role = h("span", { class: "pill procs-role" });
  const id = h("td", { class: "procs-id num" });
  const user = h("td", { class: "procs-user" });
  const cpu = measure();
  const memory = measure();
  const stateText = h("span");
  const state = h("span", { class: "procs-state" }, h("i"), stateText);
  const started = h("td", { class: "procs-started" });
  const ports = h("td", { class: "procs-ports" });
  const command = h("code");
  const stop = h("button", { class: "icon-btn danger", type: "button", "data-part": "stop" }, icon("stop", 14));
  const element = h(
    "tr",
    { class: "procs-row" },
    h("td", { class: "procs-tick" }, check),
    h("td", { class: "procs-name" }, h("div", { class: "procs-name-line" }, twist, name, size, role)),
    id, user, cpu.cell, memory.cell, h("td", { class: "procs-status" }, state), started, ports, h("td", { class: "procs-command" }, command), h("td", { class: "procs-act" }, stop),
  );
  let shown = null;
  let portsShown = "";
  check.addEventListener("change", () => view.onPick(shown.process, check.checked));
  twist.addEventListener("click", () => view.onTwist(shown.process));
  name.addEventListener("click", () => view.onOpen(shown.process));
  stop.addEventListener("click", () => view.onStop(shown.process));
  element.addEventListener("click", (event) => {
    if (event.target instanceof Element && !event.target.closest("button, input")) view.onOpen(shown.process);
  });

  function update(item) {
    shown = item;
    const { process } = item;
    // A closed branch stands for everything under it: its figures are the group's.
    const grouped = item.inside > 0 && !item.expanded;
    const scale = view.scale();
    element.dataset.key = process.key;
    element.style.setProperty("--depth", String(item.depth));
    element.classList.toggle("context", item.context);
    element.classList.toggle("ended", process.lock === "ended");
    twist.hidden = !view.tree();
    twist.classList.toggle("leaf", item.inside === 0);
    twist.disabled = item.inside === 0;
    twist.setAttribute("aria-expanded", String(item.expanded));
    twist.setAttribute("aria-label", `${item.expanded ? "Hide" : "Show"} what ${process.name} started`);
    put(name, process.name);
    size.hidden = !grouped;
    put(size, String(process.groupSize + 1));
    size.title = `${process.name} and the ${processCount(process.groupSize)} it started. The CPU and memory on this line are for all of them.`;
    const marked = ROLES[process.role];
    role.hidden = !marked;
    role.className = `pill procs-role ${marked?.tone ?? ""}`;
    put(role, marked?.label ?? "");
    role.title = marked?.warning ?? "";
    put(id, String(process.pid));
    put(user, process.user);
    cpu.set(grouped ? process.groupCpu : process.cpu, scale.cpu, HEAVY_CPU, cpuText);
    memory.set(grouped ? process.groupMemory : process.memory, scale.memory, HEAVY_MEMORY, memoryText);
    const status = statusOf(process.status);
    state.dataset.tone = status.tone;
    state.title = status.hint;
    put(stateText, status.label);
    put(started, ageText(process.started, view.now()));
    started.title = startedText(process.started);
    if (portsShown !== process.ports.join(",")) {
      portsShown = process.ports.join(",");
      ports.replaceChildren(...process.ports.slice(0, PORT_LIMIT).map((port) => h("span", { class: "procs-port", text: String(port) })), ...(process.ports.length > PORT_LIMIT ? [h("small", { class: "dim", text: `+${process.ports.length - PORT_LIMIT}` })] : []));
      ports.title = process.ports.length > 0 ? `Listening on ${process.ports.join(", ")}` : "";
    }
    put(command, process.command);
    const lock = LOCKS[process.lock] ?? "";
    check.disabled = stop.disabled = lock !== "";
    check.title = lock || "Select it";
    check.setAttribute("aria-label", `Select ${process.name}, ID ${process.pid}`);
    stop.title = lock || `Stop ${process.name}`;
    stop.setAttribute("aria-label", `Stop ${process.name}, ID ${process.pid}`);
    setPicked(view.picked.has(process.key));
  }

  function setPicked(on) {
    check.checked = on;
    element.classList.toggle("picked", on);
  }

  return { element, update, setPicked };
}
