import { h, icon, toast } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { confirmAction, openPopover } from "./overlays.js";
import { iconButton, pill, searchInput } from "./widgets.js";

// The machines opened from this browser before, latest first. They lead the list.
const USED_KEY = "stackops-webui-machines-used";
// A list this long gets a box to find a machine in.
const FILTER_FROM = 8;

// The capsule at the top right that names the machine the page shows. On this machine's own page it lists the machines of the SSH config and
// opens one: the server starts that machine's web UI over SSH and the tab goes to it, so every page is that machine's. A page opened that way
// has `boot.opened_from`, and its capsule offers the way back and nothing else (`other_machines_routes.py` says why).
export function createMachineChip() {
  const { boot } = state;
  const away = boot.opened_from;
  const chip = h(
    "button",
    {
      class: `machine-chip${away ? " away" : ""}`, type: "button",
      title: away ? `This page shows ${away.machine}, opened from ${away.name}. Click to go back.` : "The machine this page shows. Click to open another one.",
    },
    icon(away ? "server" : "monitor", 15),
    h("span", { text: away ? away.machine : boot.host.split(".")[0] }),
  );
  chip.addEventListener("click", () => (away ? showWayBack(chip) : showMachines(chip)));
  return chip;
}

function showWayBack(chip) {
  const { boot } = state;
  const away = boot.opened_from;
  openPopover(
    chip,
    h(
      "div",
      { class: "tune-panel" },
      h("div", { class: "tune-head" }, h("h3", { text: away.machine }), pill("Other machine", "accent")),
      h("p", { class: "dim", text: `You are looking at ${boot.user}@${boot.host}. Tasks you start here run there. The connection belongs to StackOps on ${away.name}. When it disconnects or stops, so does this page.` }),
      // A link and not a call to the server: it still works when the connection is gone.
      h("a", { class: "btn primary", href: away.address }, icon("back", 16), h("span", { text: `Back to ${away.name}` })),
    ),
  );
}

function showMachines(chip) {
  const note = h("p", { class: "dim", text: "Reading your SSH config…" });
  const list = h("div", { class: "machine-list" });
  const find = searchInput({ placeholder: "Find a machine", oninput: () => draw() });
  find.element.hidden = true;
  openPopover(chip, h("div", { class: "tune-panel machine-panel" }, h("div", { class: "tune-head" }, h("h3", { text: "Machines" })), note, find.element, list));
  const used = JSON.parse(localStorage.getItem(USED_KEY) ?? "[]");
  const problems = new Map();
  let answer = null;
  let opening = null;

  const open = async (machine) => {
    opening = machine.name;
    problems.delete(machine.name);
    draw();
    try {
      const { address } = await request("POST", "/api/other-machines/connect", { name: machine.name });
      localStorage.setItem(USED_KEY, JSON.stringify([machine.name, ...used.filter((name) => name !== machine.name)]));
      // The address carries that machine's access token. Its server takes the token and sends the tab on to its first page.
      location.href = address;
    } catch (error) {
      opening = null;
      problems.set(machine.name, error.message);
      draw();
    }
  };

  // Asking closes this popover. A failure after that shows as a message, like any other.
  const disconnect = async (machine) => {
    if (!(await confirmAction({ title: `Disconnect ${machine.name}?`, body: `StackOps on ${machine.name} stops, and so do the tasks it is running.`, confirm: "Disconnect", tone: "danger" }))) return;
    await request("POST", "/api/other-machines/disconnect", { name: machine.name });
    toast(`${machine.name} is disconnected.`, "info");
  };

  const row = (machine) => {
    const busy = opening === machine.name;
    const problem = problems.get(machine.name) ?? machine.problem;
    const detail = machine.there ? `${machine.there.user}@${machine.there.name} · ${machine.there.platform}` : machine.address !== machine.name ? machine.address : "";
    return h(
      "div",
      { class: "machine-entry" },
      h(
        "div",
        { class: "machine-row" },
        h(
          "button",
          { class: `machine-open${busy ? " busy" : ""}`, type: "button", disabled: opening !== null, title: machine.there ? `Go to ${machine.name}` : `Start StackOps on ${machine.name} over SSH and show it in this tab`, onclick: () => open(machine) },
          icon("server", 16),
          h("span", { class: "machine-text" }, h("strong", { text: machine.name }), detail && h("span", { text: detail })),
          busy ? h("i", { class: "ring" }) : machine.there ? pill("Connected", "good") : icon("chevron", 15),
        ),
        machine.there && opening === null && iconButton("power", `Disconnect ${machine.name}`, () => disconnect(machine)),
      ),
      busy && !machine.there && h("p", { class: "machine-note", text: "Signing in over SSH and starting StackOps there…" }),
      problem && h("p", { class: "machine-problem", text: problem }),
    );
  };

  // Connected machines first, then the ones used before, then the rest as the SSH config has them.
  const rank = (machine) => (machine.there ? -1 : used.includes(machine.name) ? used.indexOf(machine.name) : used.length);
  function draw() {
    const term = find.input.value.trim().toLowerCase();
    const shown = answer.machines.filter((machine) => `${machine.name} ${machine.address}`.toLowerCase().includes(term)).sort((first, second) => rank(first) - rank(second));
    list.replaceChildren(
      h(
        "div",
        { class: "machine-row" },
        h("span", { class: "machine-open" }, icon("monitor", 16), h("span", { class: "machine-text" }, h("strong", { text: answer.here.name }), h("span", { text: `${answer.here.user} · ${answer.here.platform}` })), pill("This page", "accent")),
      ),
      ...shown.map(row),
    );
    if (answer.closed === null && shown.length === 0) list.append(h("p", { class: "dim machine-note", text: answer.machines.length ? "No machine matches." : "Your SSH config names no machines." }));
  }

  request("GET", "/api/other-machines").then(
    (result) => {
      answer = result;
      note.textContent = result.closed ?? "Pick a machine from your SSH config. StackOps starts there over SSH, and this tab shows it.";
      find.element.hidden = result.machines.length < FILTER_FROM;
      draw();
      if (!find.element.hidden) find.input.focus();
    },
    (error) => (note.textContent = error.message),
  );
}
