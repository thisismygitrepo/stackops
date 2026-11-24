import { h, icon } from "/assets/scripts/dom.js";
import { button, notice, pill, searchInput, segmented } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { card, cardHead, reason, signalBars } from "../kit.js";

const FILTERS = [
  ["all", "All", () => true],
  ["near", "In range", (network) => network.nearby !== null],
  ["saved", "Saved in the vault", (network) => network.saved !== ""],
  ["remembered", "Known to this machine", (network) => network.remembered],
];
const SORTS = [["signal", "Strongest first"], ["name", "By name"]];
const FILTER_FROM = 6;
// The CLI joins a network with a password, from the vault or typed, or one the system already knows. An open network that is neither
// has no way in from here.
const OPEN_REASON = "StackOps joins a network with its password. Join an open one from the system's own Wi-Fi menu first, and it will be known here.";
const isOpenStranger = (network) => network.nearby !== null && network.nearby.security === "" && network.saved === "" && !network.remembered;

// One list from three places: networks whose password is in the vault, networks the system has joined before, and (where the system lists
// them without asking for anything) networks in range. A network is one row however many of the three know it.
function merge({ saved, remembered, current }, nearby) {
  const rows = new Map();
  const row = (name) => rows.get(name) ?? rows.set(name, { name, saved: "", remembered: false, nearby: null, inUse: current.connected && current.name === name }).get(name);
  for (const network of saved) row(network.ssid).saved = network.name;
  for (const name of remembered) row(name).remembered = true;
  for (const network of nearby ?? []) Object.assign(row(network.name), { nearby: network, inUse: network.in_use });
  return [...rows.values()];
}

export function createNetworksCard({ onJoin, onLookAgain }) {
  let rows = [];
  let overview = null;
  let filter = "all";
  let sort = "signal";
  let term = "";
  let busy = "";
  const count = h("span", { class: "count" });
  const search = searchInput({
    placeholder: "Filter networks",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paintRows();
    },
  });
  const sorter = segmented(SORTS, (id) => {
    sort = id;
    sorter.set(id);
    paintRows();
  });
  sorter.set(sort);
  const chips = h("div", { class: "chip-row" });
  const tools = h("div", { class: "network-toolbar", hidden: true }, chips, h("span", { class: "spacer" }), sorter.element, search.element);
  const notes = h("div", { class: "network-notes" });
  const list = h("ul", { class: "network-wifi-list" });
  const look = button({ label: "Look again", glyph: "refresh", small: true, title: "Asks the adapter to look for networks afresh, which takes a few seconds", onclick: () => onLookAgain() });
  const another = button({ label: "Join another network", glyph: "plus", small: true, onclick: () => onJoin({ kind: "new", name: "" }) });

  // How a row is joined: with the vault's password, by the system's own memory of it, or with a password asked for now.
  const wayOf = (network) => (network.saved ? { kind: "saved", name: network.saved } : network.remembered ? { kind: "remembered", name: network.name } : { kind: "new", name: network.name });

  const rowOf = (network) =>
    h(
      "li",
      { class: `network-wifi-row${network.inUse ? " current" : ""}` },
      // Where the networks in range are not listed, unlit bars would say "no signal" about every row, so there are none.
      overview.nearby_blocker === "" && signalBars(network.nearby ? network.nearby.percent : null),
      h(
        "div",
        { class: "network-wifi-text" },
        h("strong", {}, network.name, network.nearby?.security && h("span", { class: "network-wifi-lock", title: `Secured with ${network.nearby.security}` }, icon("lock", 13))),
        h(
          "div",
          { class: "network-key-facts" },
          network.inUse && pill("Connected", "good"),
          network.nearby ? pill(`In range, ${network.nearby.percent}%`, "") : overview.nearby_blocker === "" && pill("Out of range", ""),
          network.nearby && !network.nearby.security && pill("Open, no password", "warn"),
          network.saved && pill("Password in the vault", "accent"),
          network.remembered && pill("Known to this machine", ""),
        ),
      ),
      !network.inUse &&
        h(
          "span",
          { class: "network-wifi-join", "data-open": String(isOpenStranger(network)), title: overview.connect_blocker || (isOpenStranger(network) ? OPEN_REASON : wayOf(network).kind === "new" ? "Asks for the password first" : "Joins at once") },
          button({ label: busy === network.name ? "Joining…" : "Join", small: true, tone: network.nearby && !isOpenStranger(network) ? "primary" : "plain", onclick: () => onJoin(wayOf(network)) }),
        ),
    );

  function paintRows() {
    const accepts = FILTERS.find(([id]) => id === filter)[2];
    const found = rows.filter((network) => accepts(network) && network.name.toLowerCase().includes(term));
    const strength = (network) => (network.inUse ? 200 : (network.nearby?.percent ?? -1));
    found.sort((left, right) => (sort === "signal" ? strength(right) - strength(left) : 0) || left.name.localeCompare(right.name));
    list.replaceChildren(...(found.length ? found.map(rowOf) : [h("li", {}, notice({ glyph: "search", title: "No network matches", body: "Try another word, or show all of them." }))]));
    for (const control of list.querySelectorAll(".network-wifi-join .btn")) control.disabled = overview.connect_blocker !== "" || busy !== "" || control.parentElement.dataset.open === "true";
  }

  function paint(next, nearby) {
    overview = next;
    rows = merge(overview, nearby);
    count.textContent = rows.length ? plural(rows.length, "network") : "";
    tools.hidden = rows.length < FILTER_FROM;
    look.hidden = overview.nearby_blocker !== "";
    another.disabled = overview.connect_blocker !== "" || busy !== "";
    another.title = overview.connect_blocker;
    chips.replaceChildren(
      ...FILTERS.filter(([id]) => id !== "near" || overview.nearby_blocker === "").map(([id, label, accepts]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(id === filter),
            onclick: () => {
              filter = id;
              paint(overview, nearby);
            },
          },
          h("span", { text: label }),
          h("b", { text: String(rows.filter(accepts).length) }),
        ),
      ),
    );
    notes.replaceChildren(...[overview.connect_blocker, overview.nearby_blocker !== overview.connect_blocker && overview.nearby_blocker, overview.saved_problem].filter(Boolean).map(reason));
    if (rows.length === 0) {
      list.replaceChildren(
        h(
          "li",
          {},
          notice({
            glyph: "globe", title: "No network to pick from yet",
            body: "A network saved in the Vault shows up here and joins at one click: a login tagged wifi, with the keys ssid and password.",
            action: h("a", { class: "btn small", href: "#/vault" }, icon("lock", 14), h("span", { text: "Open the Vault" })),
          }),
        ),
      );
    } else paintRows();
  }

  return {
    element: card({ class: "network-wifi-networks" }, cardHead("Networks", count, h("span", { class: "spacer" }), look, another), notes, tools, list),
    paint,
    seek(name) {
      term = name.toLowerCase();
      search.input.value = name;
      tools.hidden = false;
      if (overview) paintRows();
    },
    setBusy(name) {
      busy = name;
      if (overview) paintRows();
      another.disabled = !overview || overview.connect_blocker !== "" || busy !== "";
    },
  };
}
