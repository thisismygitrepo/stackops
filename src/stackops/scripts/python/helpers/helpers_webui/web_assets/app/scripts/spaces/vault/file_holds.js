import { h } from "/assets/scripts/dom.js";
import { rise } from "../../motion.js";
import { button, sectionHead, segmented, stat } from "../../widgets.js";
import { plural } from "../../words.js";
import { createDueList } from "./file_due.js";
import { DESCRIBED, LABEL_KINDS } from "./file_words.js";
import { meter } from "./tools_kit.js";
import { EVERYWHERE, placeLabel } from "./words.js";

const BARS_AT_FIRST = 8;
const COUNTS = ["logins", "secrets", "values", "value_names"];

// Several files' counts as one: numbers added up, labels merged, and each secret's rotation record tagged with the file it is in.
function together(files) {
  const held = files.map((file) => file.holds);
  const labels = (kind) => {
    const counts = new Map();
    for (const { label, count } of held.flatMap((one) => one[kind])) counts.set(label, (counts.get(label) ?? 0) + count);
    return [...counts].map(([label, count]) => ({ label, count })).sort((left, right) => right.count - left.count || left.label.localeCompare(right.label));
  };
  return {
    ...Object.fromEntries(COUNTS.map((key) => [key, held.reduce((total, one) => total + one[key], 0)])),
    ...Object.fromEntries(LABEL_KINDS.map(([kind]) => [kind, labels(kind)])),
    described: Object.fromEntries(DESCRIBED.map(([key]) => [key, held.reduce((total, one) => total + one.described[key], 0)])),
    rotation: files.flatMap((file) => file.holds.rotation.map((row) => ({ ...row, source: file.name }))),
  };
}

// What the vault holds, as a picture: how much, what is due for replacement, how it is labelled, and how well it is described.
// `onLabel` goes to the list of logins narrowed to a tag or scope; `onShow` and `onReplace` are the due list's.
export function createHolds({ onLabel, onShow, onReplace }) {
  const tiles = [
    stat({ glyph: "key", hue: 252, label: "Logins" }),
    stat({ glyph: "lock", hue: 200, label: "Secrets" }),
    stat({ glyph: "code", hue: 150, label: "Values" }),
    stat({ glyph: "clock", hue: 30, label: "Due for replacement" }),
  ];
  const places = h("div", { class: "vault-holds-places" });
  const due = createDueList({ onShow, onReplace });
  const bars = h("div", { class: "vault-holds-bars" });
  const kinds = h("div");
  const described = h("ul", { class: "vault-holds-described" });
  const dueSection = h("section", { class: "vault-holds-block", id: "vault-file-due" }, h("h3", { text: "Due for replacement" }), due.element);
  const element = h(
    "section",
    { class: "block vault-holds", hidden: true },
    sectionHead("What the vault holds", h("span", { class: "spacer" }), places),
    h("div", { class: "vault-holds-stats" }, tiles.map((tile) => tile.element)),
    dueSection,
    h("div", { class: "vault-holds-pair" }, h("section", { class: "vault-holds-block" }, h("h3", { text: "How it is labelled" }), kinds, bars), h("section", { class: "vault-holds-block" }, h("h3", { text: "How well it is described" }), described)),
  );
  let files = [];
  let place = EVERYWHERE;
  let kind = LABEL_KINDS[0][0];
  let allBars = false;
  let risen = false;

  function paintBars(held) {
    const filled = LABEL_KINDS.filter(([id]) => held[id].length > 0);
    if (!filled.some(([id]) => id === kind)) kind = filled[0]?.[0] ?? kind;
    const picker = segmented(filled.map(([id, label]) => [id, `${label} · ${held[id].length}`]), (value) => {
      kind = value;
      allBars = false;
      paintBars(held);
    });
    picker.set(kind);
    kinds.replaceChildren(...(filled.length > 1 ? [picker.element] : []));
    const rows = held[kind];
    const top = rows[0]?.count ?? 1;
    bars.replaceChildren(
      ...(rows.length === 0
        ? [h("p", { class: "dim", text: "No login or secret carries a tag or a scope yet. They are what a search and a load pick secrets by." })]
        : (allBars ? rows : rows.slice(0, BARS_AT_FIRST)).map((item) =>
            h("button", { class: "vault-holds-bar", type: "button", title: `Show the logins that carry ${item.label}`, onclick: () => onLabel(item.label) }, h("span", { text: item.label }), meter(item.count / top, "accent"), h("b", { class: "num", text: String(item.count) })),
          )),
      rows.length > BARS_AT_FIRST && !allBars
        ? button({
            label: `Show all ${rows.length}`, small: true, tone: "ghost",
            onclick: () => {
              allBars = true;
              paintBars(held);
            },
          })
        : "",
    );
  }

  function paint() {
    const filled = files.filter((file) => file.holds);
    element.hidden = filled.length === 0;
    if (filled.length === 0) return;
    if (!filled.some((file) => file.name === place)) place = EVERYWHERE;
    const picker = segmented([[EVERYWHERE, "All"], ...filled.map((file) => [file.name, `${placeLabel(file.name)} · ${file.holds.logins}`])], (value) => {
      place = value;
      paint();
    });
    picker.set(place);
    places.replaceChildren(...(filled.length > 1 ? [picker.element] : []));
    const chosen = place === EVERYWHERE ? filled : filled.filter((file) => file.name === place);
    const held = together(chosen);
    const overdue = held.rotation.filter((row) => row.state === "due").length;
    tiles[0].set(held.logins, chosen.length > 1 ? `in ${plural(chosen.length, "file")}` : "");
    tiles[1].set(held.secrets, held.logins > 0 ? `${(held.secrets / held.logins).toFixed(1)} a login` : "");
    tiles[2].set(held.values, `${plural(held.value_names, "different name")}`);
    tiles[3].set(overdue, held.rotation.length > 0 ? `of ${held.rotation.length} that keep a date` : "none keeps a date");
    tiles[3].element.classList.toggle("alarm", overdue > 0);
    due.paint(held.rotation, chosen.length > 1);
    paintBars(held);
    described.replaceChildren(
      ...DESCRIBED.map(([key, of, label]) => h("li", {}, h("span", { text: label }), meter(held[of] ? held.described[key] / held[of] : 0, "accent"), h("b", { class: "num", text: `${held.described[key]} of ${held[of]}` }))),
    );
    if (!risen) rise(element.querySelector(".vault-holds-stats"));
    risen = true;
  }

  return {
    element, dueSection,
    paint(given) {
      files = given;
      paint();
    },
  };
}
