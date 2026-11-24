import { h } from "/assets/scripts/dom.js";
import { avatar, button, highlight, notice, pill, searchInput } from "../../widgets.js";
import { plural } from "../../words.js";
import { haystackOf, valueCount } from "./words.js";

const TAGS_SHOWN = 8;

// The logins of one vault file to choose from: a search over their labels, their most used tags to narrow by, and a tick box on each.
// Only labels are here. `chosen` is the set of the ticked logins' places in the file, kept by the caller; `onChange` hears of every tick.
export function createPickList({ chosen, onChange }) {
  let logins = [];
  let term = "";
  let tag = "";
  const search = searchInput({
    placeholder: "Search by name, account, tag or value name",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const tags = h("div", { class: "vault-copy-tags" });
  const rows = h("div", { class: "vault-copy-rows", role: "group", "aria-label": "Logins to copy" });
  const tally = h("span", { class: "dim" });
  const all = h("input", { class: "vault-copy-check", type: "checkbox", "aria-label": "Tick every login shown", title: "Tick every login shown" });
  const element = h("div", { class: "vault-copy-list" }, h("div", { class: "vault-copy-tools" }, search.element, h("label", { class: "vault-copy-all" }, all, tally)), tags, rows);

  const shown = () => logins.filter((login) => (!term || login.haystack.includes(term)) && (!tag || (login.tags ?? []).includes(tag)));

  function paintTally() {
    const visible = shown();
    const ticked = visible.filter((login) => chosen.has(login.index)).length;
    all.checked = visible.length > 0 && ticked === visible.length;
    all.indeterminate = ticked > 0 && ticked < visible.length;
    all.disabled = visible.length === 0;
    tally.textContent = visible.length === logins.length ? `All ${logins.length}` : `All ${visible.length} shown`;
  }

  all.addEventListener("change", () => {
    for (const login of shown()) {
      if (all.checked) chosen.add(login.index);
      else chosen.delete(login.index);
    }
    paint();
    onChange();
  });

  function row(login) {
    const box = h("input", { class: "vault-copy-check", type: "checkbox" });
    box.checked = chosen.has(login.index);
    box.addEventListener("change", () => {
      if (box.checked) chosen.add(login.index);
      else chosen.delete(login.index);
      paintTally();
      onChange();
    });
    return h(
      "label",
      { class: "vault-copy-row" },
      box,
      avatar(login.name, 34),
      h(
        "span",
        { class: "vault-copy-row-text" },
        h("strong", {}, highlight(login.name, term), login.accountName && h("span", { class: "dim", text: ` · ${login.accountName}` })),
        h("span", { text: login.description ?? login.secrets.map((secret) => secret.name).join(", ") }),
      ),
      h("span", { class: "vault-copy-row-meta" }, (login.tags ?? []).slice(0, 2).map((name) => pill(name)), h("span", { class: "dim", text: `${plural(login.secrets.length, "secret")} · ${plural(valueCount(login), "value")}` })),
    );
  }

  function paint() {
    const counts = new Map();
    for (const name of logins.flatMap((login) => login.tags ?? [])) counts.set(name, (counts.get(name) ?? 0) + 1);
    const top = [...counts].sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0])).slice(0, TAGS_SHOWN);
    tags.replaceChildren(
      ...top.map(([name, count]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(tag === name), title: `Show only the logins tagged ${name}`,
            onclick: () => {
              tag = tag === name ? "" : name;
              paint();
            },
          },
          h("span", { text: name }),
          h("b", { text: String(count) }),
        ),
      ),
    );
    const visible = shown();
    rows.replaceChildren(
      ...(visible.length > 0
        ? visible.map(row)
        : [
            notice({
              glyph: "search", title: "No login matches", body: "Try another word, or take the tag off.",
              action: button({
                label: "Show every login", small: true,
                onclick: () => {
                  term = "";
                  tag = "";
                  search.input.value = "";
                  paint();
                },
              }),
            }),
          ]),
    );
    paintTally();
  }

  return {
    element, search,
    show(given, source) {
      logins = given.map((login) => ({ ...login, haystack: haystackOf(login, source) }));
      if (!logins.some((login) => (login.tags ?? []).includes(tag))) tag = "";
      paint();
    },
  };
}
