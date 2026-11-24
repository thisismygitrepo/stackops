import { h, toast } from "/assets/scripts/dom.js";
import { button, notice, searchInput, segmented, skeleton } from "../../widgets.js";
import { plural } from "../../words.js";
import { readItems } from "./bitwarden_api.js";
import { itemRow } from "./bitwarden_item.js";
import { KINDS } from "./bitwarden_words.js";
import { busyButton } from "./tools_kit.js";

const ROWS_AT_A_TIME = 100;
const ALL = "all";
const SORTS = [["name", "A to Z"], ["changed", "Newest change first"]];

// Find a login: every item of the Bitwarden vault by its labels, narrowed as the person types. What is typed never leaves the page. A value is
// fetched only when its copy button or its eye is pressed. `actions` are the page's: unlock() and install().
export function createFinder({ actions }) {
  let items = null;
  let saved = false;
  let term = "";
  let kind = ALL;
  let coded = false;
  let sort = "name";
  let limit = ROWS_AT_A_TIME;
  let rows = [];
  let ticket = 0;

  const search = searchInput({
    placeholder: "Search by name, user name or web address",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      limit = ROWS_AT_A_TIME;
      paint();
    },
  });
  const kinds = h("div", { class: "vault-bw-kinds" });
  const codeToggle = h("button", { class: "chip-button", type: "button", "aria-pressed": "false", text: "With a one-time code", onclick: () => ((coded = !coded), paint()) });
  const sorter = segmented(SORTS, (value) => {
    sort = value;
    sorter.set(sort);
    paint();
  });
  sorter.set(sort);
  const count = h("span", { class: "count" });
  const origin = h("span", { class: "dim vault-bw-origin" });
  const refresh = busyButton({ label: "Read the list again", glyph: "refresh", small: true, title: "Asks Bitwarden for the list as it is now. Bitwarden has to be unlocked." }, () => load(true).catch((error) => toast(error.message)));
  const list = h("ul", { class: "vault-bw-items" });
  const more = h("div", { class: "vault-bw-more" });
  const tools = h("div", { class: "vault-bw-tools", hidden: true }, search.element, kinds, codeToggle, h("span", { class: "spacer" }), sorter.element);
  const element = h("section", { class: "block vault-bw-find", id: "vault-bw-find" }, h("div", { class: "section-head" }, h("h2", { text: "Find a login" }), count, origin, h("span", { class: "spacer" }), refresh), tools, list, more);

  const matches = (item) => (kind === ALL || item.kind === kind) && (!coded || item.has_code) && (!term || item.haystack.includes(term));

  function showAll() {
    term = "";
    kind = ALL;
    coded = false;
    search.input.value = "";
    paint();
  }

  function paint() {
    for (const row of rows) row.close();
    rows = [];
    tools.hidden = !items || items.length === 0;
    refresh.hidden = !items;
    more.replaceChildren();
    if (!items) return;
    const present = Object.keys(KINDS).filter((id) => items.some((item) => item.kind === id));
    if (kind !== ALL && !present.includes(kind)) kind = ALL;
    const picker = segmented([[ALL, `All · ${items.length}`], ...present.map((id) => [id, `${KINDS[id]} · ${items.filter((item) => item.kind === id).length}`])], (value) => {
      kind = value;
      limit = ROWS_AT_A_TIME;
      paint();
    });
    picker.set(kind);
    kinds.replaceChildren(...(present.length > 1 ? [picker.element] : []));
    codeToggle.setAttribute("aria-pressed", String(coded));
    codeToggle.hidden = !items.some((item) => item.has_code);
    const found = items.filter(matches).sort(sort === "name" ? (left, right) => left.name.localeCompare(right.name) : (left, right) => right.changed.localeCompare(left.changed));
    count.textContent = found.length === items.length ? plural(items.length, "item") : `${found.length} of ${items.length}`;
    origin.textContent = saved ? "From the copy saved on this machine" : "Read from Bitwarden just now";
    if (items.length === 0) return list.replaceChildren(h("li", {}, notice({ glyph: "lock", title: "Your Bitwarden vault is empty", body: "Nothing is kept in it yet, or the copy on this machine is older than the vault. Sync, then read the list again." })));
    if (found.length === 0) return list.replaceChildren(h("li", {}, notice({ glyph: "search", title: "Nothing matches", body: "Try another word, or take the filters off.", action: button({ label: "Show everything", small: true, onclick: showAll }) })));
    rows = found.slice(0, limit).map((item) => itemRow(item, term));
    list.replaceChildren(...rows.map((row) => row.element));
    if (found.length > limit) {
      more.replaceChildren(
        button({
          label: `Show ${Math.min(ROWS_AT_A_TIME, found.length - limit)} more`, small: true, tone: "ghost",
          onclick: () => {
            limit += ROWS_AT_A_TIME;
            paint();
          },
        }),
      );
    }
  }

  // Why there is no list, with the way forward: `reason` is how Bitwarden stands when that is the cause.
  function explain(error) {
    count.textContent = "";
    origin.textContent = "";
    const blocked = {
      missing: () => notice({ glyph: "download", title: "Bitwarden's command-line program is not installed", body: "Install it, and your logins are listed here.", action: button({ label: "Install it from Apps", glyph: "download", small: true, onclick: actions.install }) }),
      unauthenticated: () => notice({ glyph: "lock", title: "Unlock Bitwarden to see your logins", body: "Bitwarden is signed out, and no copy of the list is saved on this machine.", action: button({ label: "Go to Unlock", glyph: "key", small: true, onclick: actions.unlock }) }),
      locked: () => notice({ glyph: "lock", title: "Unlock Bitwarden to see your logins", body: "Bitwarden is locked, and no copy of the list is saved on this machine.", action: button({ label: "Go to Unlock", glyph: "key", small: true, onclick: actions.unlock }) }),
    }[error.payload?.reason];
    list.replaceChildren(h("li", {}, blocked ? blocked() : notice({ glyph: "alert", tone: "bad", title: "The list didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => load(false) }) })));
  }

  // `fresh` asks Bitwarden itself. When that cannot be done the list on show stays, and the reason is thrown for the caller to say.
  async function load(fresh) {
    const mine = (ticket += 1);
    if (!items) list.replaceChildren(...skeleton(4, "row").map((bone) => h("li", {}, bone)));
    try {
      const answer = await readItems(fresh);
      if (mine !== ticket) return;
      items = answer.items.map((item) => ({ ...item, haystack: [item.name, item.username, ...item.urls].join(" ").toLowerCase() }));
      saved = answer.saved;
      paint();
      return answer;
    } catch (error) {
      if (mine !== ticket) return;
      if (fresh && items) throw error;
      items = null;
      paint();
      explain(error);
      return null;
    }
  }

  return {
    element, load,
    // Nothing is known yet: the list waits for the page to say how Bitwarden stands.
    wait() {
      if (!items) list.replaceChildren(...skeleton(4, "row").map((bone) => h("li", {}, bone)));
    },
    arrive(given) {
      if (given) {
        term = given.toLowerCase();
        search.input.value = given;
        if (items) paint();
      }
      element.scrollIntoView({ behavior: "smooth", block: "start" });
      search.input.focus({ preventScroll: true });
    },
    // Folds every open item, which also covers every value on show: for when the page is left.
    cover: () => rows.forEach((row) => row.close()),
  };
}
