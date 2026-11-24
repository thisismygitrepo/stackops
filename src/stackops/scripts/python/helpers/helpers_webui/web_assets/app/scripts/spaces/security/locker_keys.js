import { h } from "/assets/scripts/dom.js";
import { copyChip, pill, searchInput } from "../../widgets.js";
import { KEY_STATES } from "./tools_words.js";

const SEARCH_FROM = 6;
const MAKE_KEY_COMMAND = "gpg --full-generate-key";
// The choice that names no key: GPG then encrypts for the person's own key.
export const OWN_KEY = "";

const day = (seconds) => new Date(seconds * 1000).toLocaleDateString([], { year: "numeric", month: "short", day: "numeric" });
const owner = (key) => [key.name, key.email && `<${key.email}>`].filter(Boolean).join(" ") || "A key without a name";
const facts = (key) => [`ID ${key.id.slice(-8)}`, key.created && `made ${day(key.created)}`, key.expires ? `expires ${day(key.expires)}` : "never expires"].filter(Boolean).join(" · ");

// The keys GPG holds on this machine, as a list to choose the one a file is encrypted for. The first choice names no key, which is what the
// command does by default: GPG encrypts for the person's own key. A key GPG would refuse is greyed out with the reason.
// `picked` is a fingerprint, or OWN_KEY. `onPick` hears the choice.
export function createKeyList({ locker, picked, onPick }) {
  let chosen = picked;
  let term = "";
  const own = locker.keys.find((key) => key.fingerprint === locker.own);
  const others = locker.keys.filter((key) => key !== own);
  const list = h("ul", { class: "sec-keys" });
  const search = searchInput({
    placeholder: "Find a key by name, address or ID",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });

  function row({ value, title, lines, marks, blocked }) {
    return h(
      "li",
      {},
      h(
        "button",
        {
          class: "sec-keys-row", type: "button", "aria-pressed": String(value === chosen), disabled: Boolean(blocked), title: blocked || "",
          onclick: () => {
            chosen = value;
            paint();
            onPick(value);
          },
        },
        h("i", { class: "sec-dot" }),
        h("span", { class: "sec-keys-text" }, h("strong", {}, h("span", { text: title }), marks), lines.map((text) => h("span", { text }))),
      ),
    );
  }

  function paint() {
    const found = others.filter((key) => `${key.name} ${key.email} ${key.id} ${key.fingerprint}`.toLowerCase().includes(term));
    list.replaceChildren(
      row({
        value: OWN_KEY, title: "Your own key", marks: pill("Default", "accent"), blocked: own ? "" : "There is no key of your own on this machine.",
        lines: own ? [owner(own), facts(own)] : ["There is no key of your own on this machine, so a key has to be named."],
      }),
      ...found.map((key) => row({ value: key.fingerprint, title: owner(key), marks: key.mine && pill("Yours"), lines: [facts(key), key.state !== "usable" && KEY_STATES[key.state]].filter(Boolean), blocked: key.state === "usable" ? "" : KEY_STATES[key.state] })),
      ...(others.length > 0 && found.length === 0 ? [h("li", { class: "sec-runs-none", text: "No key matches that." })] : []),
    );
  }

  paint();
  return {
    element: h(
      "div",
      { class: "sec-keys-box" },
      others.length >= SEARCH_FROM && search.element,
      list,
      locker.keys.length === 0 && h("div", { class: "sec-cloud-command" }, h("span", { text: "GPG holds no keys yet. Make one in a terminal with" }), copyChip(MAKE_KEY_COMMAND)),
    ),
    // Whether the choice is one GPG would encrypt for.
    usable: () => (chosen === OWN_KEY ? Boolean(own) : others.some((key) => key.fingerprint === chosen && key.state === "usable")),
    chosen: () => chosen,
  };
}

// For a file that was encrypted for keys: who they belong to, where this machine knows them. `ids` are the IDs the file names.
export function keysNamed(locker, ids) {
  const known = locker.keys.filter((key) => ids.some((id) => key.ids.includes(id)));
  return known.length > 0 ? known.map(owner).join(", ") : "";
}
