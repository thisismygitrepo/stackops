import { h } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { staleKeeper } from "../../data.js";
import { backLink } from "../../space_kit.js";
import { button, notice, searchInput, segmented, skeleton, stat } from "../../widgets.js";
import { plural } from "../../words.js";
import { prepare } from "./environment/model.js";
import { pathTab } from "./environment/path.js";
import { variablesTab } from "./environment/variables.js";
import { ADDRESS, ENVIRONMENT_HASH, PATH_HASH, TABS, TOOL_PATH } from "./environment/words.js";

// This page's stylesheet comes with the page, on its first visit, the way its script does: the app's start does not grow with it. The page
// waits for it, so it is never drawn bare.
const STYLES = "/assets/app/styles/machine_environment.css";
if (!document.querySelector(`link[href="${STYLES}"]`)) await new Promise((resolve) => document.head.append(h("link", { rel: "stylesheet", href: STYLES, onload: resolve, onerror: resolve })));

// Whoever opens the tool with the search path named lands on that tab.
export function open(_context, { preset }) {
  location.hash = ["PATH", "p"].includes(preset?.which) ? PATH_HASH : ENVIRONMENT_HASH;
}

// Machine › Environment, at #/machine/environment and #/machine/environment/path: the variables a task started from the web UI gets, and the
// folders it searches for programs. A page and not a sheet: a hundred-odd variables and thousands of programs to search and filter.
// The command behind it (`utils machine environment`) is a picker for a terminal, so the page reads the server instead (ADDRESS).
export function createPart({ activity }) {
  let tabs = null;
  let shown = "variables";
  let typed = "";
  const active = { variables: new Set(), path: new Set() };

  const picker = segmented(TABS, (id) => (location.hash = id === "path" ? PATH_HASH : ENVIRONMENT_HASH));
  const search = searchInput({
    placeholder: "Search",
    oninput: (value) => {
      typed = value;
      paintRows();
    },
  });
  const count = h("span", { class: "count" });
  const tiles = h("div", { class: "stats env-tiles" });
  const chips = h("div", { class: "chip-row env-chips" });
  const note = h("p", { class: "env-note" });
  const body = h("div", { class: "env-body" }, skeleton(6, "row"));
  const again = button({ label: "Read again", glyph: "refresh", title: "Read the variables and the folders again", onclick: () => keeper.load() });
  const element = h(
    "div",
    { class: "machine-environment", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, backLink("#/machine", "Machine"), h("h1", { text: "Environment" }), h("p", { text: "What a task started from here runs with: its variables, and the folders it searches for programs, in order." })),
      h("div", { class: "view-actions" }, agentButton(activity, { commands: [TOOL_PATH], ideas: ["Where is this variable set, and how do I change it?"] }), again),
    ),
    h("div", { class: "table-bar env-bar" }, picker.element, search.element, h("span", { class: "spacer" }), count),
    tiles,
    chips,
    note,
    body,
  );

  // The rows alone: what changes while someone types, presses a filter or opens a row.
  function paintRows() {
    if (!tabs) return;
    const tab = tabs[shown];
    const rows = tab.rows(typed.toLowerCase().split(/\s+/).filter(Boolean), active[shown]);
    count.textContent = rows.length === tab.total ? plural(tab.total, tab.unit) : `${rows.length.toLocaleString()} of ${plural(tab.total, tab.unit)}`;
    if (rows.length > 0) return body.replaceChildren(h("ul", { class: "env-list" }, rows));
    const clear = button({
      label: "Show everything", small: true,
      onclick: () => {
        typed = search.input.value = "";
        active[shown].clear();
        paintFrame();
      },
    });
    body.replaceChildren(notice({ glyph: "search", title: tab.emptyText, body: "Nothing fits what is typed and the filters that are on.", action: clear }));
  }

  // Everything a tab shows around its rows. Drawn when the tab changes and when a reading arrives, not on every keystroke.
  function paintFrame() {
    picker.set(shown);
    if (!tabs) return;
    const tab = tabs[shown];
    search.input.placeholder = tab.placeholder;
    search.input.setAttribute("aria-label", tab.placeholder);
    tiles.hidden = false;
    tiles.replaceChildren(
      ...tab.tiles.map((tile) => {
        const item = stat(tile);
        item.set(tile.value, tile.note);
        return item.element;
      }),
    );
    chips.replaceChildren(
      ...tab.chips.map((chip) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(active[shown].has(chip.key)),
            onclick: (event) => {
              if (!active[shown].delete(chip.key)) active[shown].add(chip.key);
              event.currentTarget.setAttribute("aria-pressed", String(active[shown].has(chip.key)));
              paintRows();
            },
          },
          h("span", { text: chip.label }),
          h("b", { text: chip.count.toLocaleString() }),
        ),
      ),
    );
    chips.hidden = tab.chips.length === 0;
    note.replaceChildren(...tab.note);
    note.hidden = tab.note.length === 0;
    paintRows();
  }

  async function load() {
    element.classList.add("loading");
    try {
      const data = prepare(await request("GET", ADDRESS));
      // A filter that names a prefix the new reading no longer has would hide every row with nothing on the page to switch it off.
      const offered = new Set(data.prefixes.map(([prefix]) => prefix));
      for (const key of [...active.variables]) if (!key.startsWith(":") && !offered.has(key)) active.variables.delete(key);
      tabs = { variables: variablesTab(data, paintRows), path: pathTab(data, paintRows) };
      paintFrame();
    } catch (error) {
      keeper.spoil();
      tabs = null;
      for (const part of [tiles, chips, note]) part.hidden = true;
      count.textContent = "";
      // A server started before this page existed has no answer for it, and says so with a 404 that only a restart clears up.
      const reason = error.status === 404 ? "The StackOps server that is running is older than this page. Restart it, then open this page again." : error.message;
      body.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The environment could not be read", body: reason, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => keeper.load() }) }));
    }
    element.classList.remove("loading");
  }

  const keeper = staleKeeper(element, load);
  return {
    element,
    show(rest) {
      shown = rest[0] === "path" ? "path" : "variables";
      paintFrame();
      keeper.ensure();
    },
  };
}
