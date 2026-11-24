import { h, icon } from "/assets/scripts/dom.js";
import { rise } from "../../../motion.js";
import { button, notice, searchInput, segmented, skeleton } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { deviceRow } from "./device_row.js";
import { arrange } from "./model.js";
import { SORTS, STATES, STATE_ORDER } from "./words.js";

// The first step: every device the command lists, with filters by state, a search and three orders. `render({ picture, picked })` draws it.
export function createDeviceList({ onPick, onRefresh }) {
  let filter = "all";
  let sort = "state";
  let term = "";
  // Whether the devices that cannot be mounted are folded away. Until the person opens or closes the fold, they are when there is something else to look at.
  let folded = null;
  let shown = null;

  const chips = h("div", { class: "chip-row" });
  const count = h("span", { class: "count" });
  const body = h("div", { class: "mount-list" }, skeleton(4, "row"));
  const search = searchInput({
    placeholder: "Find a device",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const order = segmented(SORTS, (id) => {
    sort = id;
    paint();
  });
  const element = h(
    "section",
    { class: "mount-card mount-devices" },
    h("header", { class: "mount-card-head" }, h("b", { class: "mount-step", text: "1" }), h("h2", { text: "Choose a device" }), count),
    h("div", { class: "mount-tools" }, chips, h("span", { class: "spacer" }), order.element, search.element),
    body,
  );

  function clear() {
    filter = "all";
    term = "";
    search.input.value = "";
    paint();
  }

  const rows = (devices) => h("ul", { class: "mount-rows", role: "radiogroup", "aria-label": "Devices" }, devices.map((device) => deviceRow({ device, picture: shown.picture, picked: device.path === shown.picked, term, onPick })));
  const group = (id, devices) => h("section", { class: "mount-group" }, h("h3", {}, STATES[id].group, h("b", { text: String(devices.length) })), rows(devices));

  function grouped(listed, all) {
    const of = (id) => listed.filter((device) => device.state === id);
    const [ready, mounted, blocked] = STATE_ORDER.map(of);
    const waiting = all.some((device) => device.state === "ready");
    const idle =
      !waiting && term === "" && filter !== "mounted" && filter !== "blocked" &&
      notice({ glyph: "plug", title: "Nothing is waiting to be mounted", body: "Everything attached is mounted already or cannot be mounted here. Plug a device in, then refresh.", action: button({ label: "Refresh", glyph: "refresh", small: true, onclick: onRefresh }) });
    const open = filter === "blocked" || term !== "" || !(folded ?? (ready.length > 0 || mounted.length > 0));
    // The click is heard before the fold moves, so what it reads is the state being left.
    const summary = h("summary", { onclick: () => (folded = quiet.open) }, icon("chevron", 14), h("span", { text: STATES.blocked.group }), h("b", { text: String(blocked.length) }));
    const quiet = blocked.length > 0 && h("details", { class: "fold mount-quiet", open }, summary, rows(blocked));
    return [idle, ready.length > 0 && group("ready", ready), mounted.length > 0 && group("mounted", mounted), quiet];
  }

  function paint() {
    if (!shown) return;
    const { devices } = shown.picture;
    const tally = (id) => (id === "all" ? devices.length : devices.filter((device) => device.state === id).length);
    chips.replaceChildren(
      ...[["all", "Everything"], ...STATE_ORDER.map((id) => [id, STATES[id].group])].map(([id, label]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(filter === id),
            onclick: () => {
              filter = id;
              paint();
            },
          },
          h("span", { text: label }), h("b", { text: String(tally(id)) }),
        ),
      ),
    );
    order.set(sort);
    const listed = arrange(devices, { filter, sort, term });
    count.textContent = devices.length === 0 ? "" : listed.length === devices.length ? plural(devices.length, "device") : `${listed.length} of ${plural(devices.length, "device")}`;
    if (devices.length === 0) {
      body.replaceChildren(notice({ glyph: "database", title: "No storage devices found", body: "This machine lists no disks at all. Plug one in, then refresh.", action: button({ label: "Refresh", glyph: "refresh", small: true, onclick: onRefresh }) }));
    } else if (listed.length === 0) {
      body.replaceChildren(notice({ glyph: "search", title: "Nothing matches", body: "No device fits the filter and the search.", action: button({ label: "Show everything", small: true, onclick: clear }) }));
    } else {
      body.replaceChildren(...(sort === "state" ? grouped(listed, devices) : [rows(listed)]).filter(Boolean));
    }
  }

  return {
    element,
    render(next) {
      const first = shown === null;
      shown = next;
      paint();
      if (first) rise(body, ".mount-row");
    },
    // The filters are let go, so a device the view was opened for is in sight whatever was set before.
    showAll: clear,
  };
}
