import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { editFile } from "../../../space_kit.js";
import { button, copyChip, glyphTile, notice, pathChip, pill, searchInput, segmented } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { card, cardHead, fill } from "../kit.js";

const SORTS = [["file", "As in the file"], ["name", "By name"], ["kind", "By type"]];
const KIND_HUES = { Ed25519: 150, RSA: 30 };
// An RSA key shorter than this is weaker than what OpenSSH makes today.
const SHORT_RSA_BITS = 3072;
const FILTER_FROM = 6;

const shortPrint = (fingerprint) => `${fingerprint.slice(0, 22)}…`;

export function keyFacts(key) {
  return [
    pill(key.kind === "RSA" ? `RSA ${key.bits}` : key.kind, ""),
    key.kind === "RSA" && key.bits < SHORT_RSA_BITS && pill("Short key", "warn"),
    key.fingerprint && copyChip(key.fingerprint, shortPrint(key.fingerprint)),
  ];
}

// Who can sign in: every key in the file OpenSSH reads, by name, type and fingerprint. Removing one is done in the file itself, which opens
// in the editor: the CLI has a command to add a key and none to take one away.
export function createKeysCard({ activity }) {
  let overview = null;
  let term = "";
  let kind = "";
  let sort = "file";
  const count = h("span", { class: "count" });
  const search = searchInput({
    placeholder: "Filter keys",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paintList();
    },
  });
  const sorter = segmented(SORTS, (id) => {
    sort = id;
    sorter.set(id);
    paintList();
  });
  sorter.set(sort);
  const chips = h("div", { class: "chip-row" });
  const tools = h("div", { class: "network-toolbar", hidden: true }, chips, h("span", { class: "spacer" }), sorter.element, search.element);
  const list = h("ul", { class: "network-key-list" });
  const foot = h("footer", { class: "network-card-foot" });

  const row = (key) =>
    h(
      "li",
      { class: `network-key${key.problem ? " broken" : ""}` },
      glyphTile("key", KIND_HUES[key.kind] ?? 252, 38),
      h(
        "div",
        { class: "network-key-text" },
        h("strong", { text: key.name || "No name" }),
        key.problem ? h("span", { class: "network-key-problem", text: `Line ${key.line}: ${key.problem}` }) : h("div", { class: "network-key-facts" }, keyFacts(key), key.limits.length > 0 && pill(`Limited: ${key.limits.join(", ")}`, "accent")),
      ),
      key.problem && pill("Unusable", "bad"),
    );

  function paintList() {
    const { keys } = overview;
    const found = keys.filter((key) => (kind === "" || key.kind === kind) && `${key.name} ${key.kind} ${key.type} ${key.fingerprint}`.toLowerCase().includes(term));
    // A key without a name, or one that is not usable and so has no type, goes to the end of the order that would have needed it.
    const lacks = (key) => (sort === "name" ? key.name === "" : key.kind === "");
    const ordered = sort === "file" ? found : [...found].sort((left, right) => lacks(left) - lacks(right) || (sort === "kind" && left.kind.localeCompare(right.kind)) || left.name.localeCompare(right.name));
    list.replaceChildren(...(ordered.length ? ordered.map(row) : [h("li", {}, notice({ glyph: "search", title: "No key matches", body: "Try another word, or another type." }))]));
  }

  function paint(next) {
    overview = next;
    const { keys, files, user, problem } = overview;
    const kinds = [...new Set(keys.filter((key) => key.kind).map((key) => key.kind))].sort();
    if (!kinds.includes(kind)) kind = "";
    count.textContent = keys.length ? plural(keys.length, "key") : "";
    tools.hidden = keys.length < FILTER_FROM;
    chips.replaceChildren(
      ...(kinds.length > 1 ? [["", "All"], ...kinds.map((name) => [name, name])] : []).map(([id, label]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(id === kind),
            onclick: () => {
              kind = id;
              paint(overview);
            },
          },
          h("span", { text: label }),
          h("b", { text: String(id === "" ? keys.length : keys.filter((key) => key.kind === id).length) }),
        ),
      ),
    );
    if (problem) list.replaceChildren(h("li", {}, notice({ glyph: "alert", tone: "bad", title: "The list of keys could not be read", body: problem })));
    else if (keys.length === 0) list.replaceChildren(h("li", {}, notice({ glyph: "key", title: "Nobody can sign in with a key yet", body: `A key added here lets its owner sign in as ${user} without a password.` })));
    else paintList();
    const shown = keys.length > 0 ? [...new Set(keys.map((key) => key.file))] : files.slice(0, 1);
    fill(
      foot,
      h("span", { class: "dim", text: keys.length > 0 ? `Whoever holds one of these signs in as ${user}. They are kept in` : "Keys will be kept in" }),
      ...shown.map((file) => pathChip(file)),
      h("span", { class: "spacer" }),
      keys.length > 0 && state.boot.platform !== "Windows" && button({ label: "Edit the file", glyph: "pencil", small: true, title: "Opens the file in a text editor inside the activity panel. Deleting a line takes that key's access away.", onclick: () => editFile(activity, { title: "the allowed keys", kind: "file", path: shown[0] }) }),
    );
  }

  return { element: card({ class: "network-ssh-keys" }, cardHead("Who can sign in", count), tools, list, foot), paint };
}
