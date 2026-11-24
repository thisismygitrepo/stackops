import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { staleKeeper } from "../../data.js";
import { recall, remember } from "../../memory.js";
import { toolButton } from "../../space_kit.js";
import { button, notice, searchInput, segmented, skeleton } from "../../widgets.js";
import { createDeviceActions } from "./devices/actions.js";
import { createDeviceList } from "./devices/list.js";
import { groupsOf, rowsOf } from "./devices/model.js";
import { hideTip } from "./devices/space_map.js";
import { createDeviceSummary } from "./devices/summary.js";
import { DEVICES_HASH, LIST_COMMAND, MOUNT_COMMAND, ORDERS, PLACES, PLACE_ORDER, STATES } from "./devices/words.js";

const MEMORY_ID = "machine devices";
const WATCH_MILLISECONDS = 4000;
const ALWAYS_OFFERED = ["internal", "external"];

export function open() {
  location.hash = DEVICES_HASH;
}

// Storage devices: every disk of this machine with what is on it, read on arrival and again whenever a disk comes, goes, or is mounted.
export function createPart({ tools }) {
  const remembered = recall(MEMORY_ID);
  const view = {
    place: "all", state: "all", term: "", order: ORDERS.some(([id]) => id === remembered.get("order")) ? remembered.get("order") : "disk", parts: remembered.get("parts") === "on",
    open: new Set(), busy: new Set(),
  };
  let picture = null;
  let problem = null;
  let ticket = 0;
  let entered = false;
  let watching = false;

  const keep = () => remember(MEMORY_ID, new Map([["order", view.order], ...(view.parts ? [["parts", "on"]] : [])]));
  const summary = createDeviceSummary();
  const chips = h("div", { class: "chip-row" });
  const search = searchInput({
    placeholder: "Find a disk or volume",
    oninput: (value) => {
      view.term = value;
      paint();
    },
  });
  const statePick = segmented(STATES, (id) => {
    view.state = id;
    paint();
  });
  const orderPick = segmented(ORDERS, (id) => {
    view.order = id;
    keep();
    paint();
  });
  const partsSwitch = h("button", { class: "mini-toggle", type: "button", role: "switch", title: "Also list what the system keeps for itself, such as start-up files, recovery and extra memory", onclick: () => setParts(!view.parts) }, h("i", { class: "switch" }), h("span", { text: "System parts" }));
  const toolbar = h("div", { class: "devices-tools" }, h("div", {}, chips, partsSwitch, h("span", { class: "spacer" }), search.element), h("div", {}, statePick.element, h("span", { class: "spacer" }), orderPick.element));
  const stamp = h("span", { class: "devices-stamp" });
  const refresh = button({ label: "Refresh", glyph: "refresh", onclick: () => keeper.load() });
  const problemHolder = h("div");

  function setParts(on) {
    view.parts = on;
    keep();
    paint();
  }

  const handlers = {
    ...createDeviceActions({ tools, view, repaint: () => paint(), reload: () => keeper.load() }),
    showParts: () => setParts(true),
    toggle(volume) {
      if (!view.open.delete(volume.id)) view.open.add(volume.id);
      paint();
    },
    clearFilters() {
      Object.assign(view, { place: "all", state: "all", term: "" });
      search.input.value = "";
      paint();
    },
  };
  const list = createDeviceList(view, handlers);

  function paintChips() {
    const rows = rowsOf(groupsOf(picture)).filter(({ volume }) => view.parts || !volume.helper);
    const count = (place) => rows.filter(({ group }) => group.place === place).length;
    const offered = PLACE_ORDER.filter((place) => ALWAYS_OFFERED.includes(place) || count(place) > 0 || view.place === place);
    chips.replaceChildren(
      ...[["all", "Everything", rows.length], ...offered.map((place) => [place, PLACES[place].label, count(place)])].map(([id, label, amount]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(view.place === id),
            onclick: () => {
              view.place = id;
              paint();
            },
          },
          h("span", { text: label }),
          h("b", { text: String(amount) }),
        ),
      ),
    );
  }

  function paintProblem() {
    const again = button({ label: "Try again", glyph: "refresh", small: true, onclick: () => keeper.load() });
    const plain = button({ label: "Open the plain list", glyph: "terminal", small: true, onclick: () => tools.open(LIST_COMMAND, { plain: true }) });
    if (problem.kind === "unavailable") {
      // Nothing the command prints would work either, so the way forward is in the words, and Try again is there for after it was followed.
      const missing = problem.reason === "tool_missing";
      return notice({ glyph: "database", title: missing ? "A program this page needs is not installed" : "Disks cannot be listed on this system", body: `${problem.message}${missing ? " Install it, then try again." : ""}`, action: again });
    }
    return notice({ glyph: "alert", tone: "bad", title: "The disks could not be read", body: `${problem.message.replace(/[.\s]*$/, "")}. If StackOps was just updated, restart it and open this page again.`, action: h("div", { class: "dialog-actions" }, plain, again) });
  }

  function paint(entering = false) {
    hideTip();
    const ready = picture !== null;
    summary.element.hidden = problem !== null;
    toolbar.hidden = !ready;
    problemHolder.replaceChildren(...(problem ? [paintProblem()] : []));
    list.element.hidden = problem !== null;
    stamp.textContent = ready ? `Read at ${formatClock(picture.readAt / 1000)}` : "";
    if (!ready) {
      if (!problem) list.element.replaceChildren(h("div", { class: "devices-loading" }, skeleton(3, "card")));
      return;
    }
    toolbar.hidden = picture.disks.length + picture.shares.length === 0;
    statePick.set(view.state);
    orderPick.set(view.order);
    partsSwitch.setAttribute("aria-checked", String(view.parts));
    summary.paint(picture);
    paintChips();
    list.render(picture, state.boot.platform, entering);
  }

  // `quiet` is for the read the page starts by itself. A disk on its way out can be gone halfway through a read; that read fails, the list stays
  // as it was, and the next check a few seconds later reads again. A read someone asked for shows its failure.
  async function load(quiet = false) {
    const mine = (ticket += 1);
    refresh.disabled = true;
    try {
      const answer = await request("GET", "/api/machine/devices");
      if (mine !== ticket) return;
      picture = answer.unavailable ? null : { ...answer, readAt: Date.now() };
      problem = answer.unavailable ? { kind: "unavailable", ...answer.unavailable } : null;
    } catch (error) {
      if (mine !== ticket) return;
      if (!quiet || picture === null) {
        picture = null;
        problem = { kind: "failed", message: error.message };
        keeper.spoil();
      }
    }
    refresh.disabled = false;
    paint(!entered && picture !== null);
    entered = entered || picture !== null;
  }

  // The cheap check behind the page keeping itself current. It only runs while the page is in view and nothing is being worked on.
  // A check that gets no answer is left to the next one: a server that is gone is reported by whatever the person does next.
  async function watch() {
    if (watching || picture === null || view.busy.size > 0 || document.hidden || !element.isConnected || element.closest("[hidden]")) return;
    watching = true;
    const answer = await request("GET", "/api/machine/devices/mark").catch(() => null);
    if (answer && picture !== null && answer.mark !== picture.mark) await keeper.load(true);
    watching = false;
  }

  const element = h(
    "div",
    { class: "devices", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "devices-back", href: "#/machine" }, icon("back", 14), h("span", { text: "Machine" })), h("h1", { text: "Storage devices" }), h("p", { text: "Every disk in this computer or plugged into it, what is on each one, and how much room is left." })),
      h("div", { class: "view-actions" }, stamp, button({ label: "Plain list", glyph: "terminal", title: "The same devices the way the command line lists them", onclick: () => tools.open(LIST_COMMAND, { plain: true }) }), toolButton(tools, MOUNT_COMMAND, { label: "Mount a device", glyph: "plug" }), refresh),
    ),
    summary.element,
    toolbar,
    problemHolder,
    list.element,
  );
  const keeper = staleKeeper(element, load);
  setInterval(watch, WATCH_MILLISECONDS);
  paint();
  return {
    element,
    show() {
      keeper.ensure();
      watch();
    },
  };
}
