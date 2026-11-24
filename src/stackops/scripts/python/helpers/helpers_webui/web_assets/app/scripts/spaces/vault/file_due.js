import { h } from "/assets/scripts/dom.js";
import { button, notice, pill, segmented } from "../../widgets.js";
import { byUrgency, rotationWords } from "./file_words.js";
import { meter } from "./tools_kit.js";
import { placeLabel } from "./words.js";

const SHOWN_AT_FIRST = 8;

// The secrets that record when they were last replaced, most pressing first, each with how much of its interval is used up.
// `several` says the rows come from more than one file, so each says which. `onShow` goes to the login in the list, `onReplace` to the tool that replaces a secret.
export function createDueList({ onShow, onReplace }) {
  const list = h("ul", { class: "vault-due-list" });
  const more = h("div", { class: "vault-due-more" });
  const pickerHolder = h("div");
  const element = h("div", { class: "vault-due" }, pickerHolder, list, more);
  let rows = [];
  let several = false;
  let filter = "pressing";
  let all = false;

  function row(item) {
    const words = rotationWords(item);
    return h(
      "li",
      { class: `vault-due-row ${words.tone}` },
      h(
        "button",
        { class: "vault-due-name", type: "button", title: "Show this login in the list", onclick: () => onShow(item) },
        h("strong", {}, item.login, item.account && h("span", { class: "dim", text: ` · ${item.account}` })),
        h("span", { text: several ? `${item.secret} · ${placeLabel(item.source)}` : item.secret }),
      ),
      h("div", { class: "vault-due-gauge" }, meter(words.share, words.tone), h("span", { class: "dim", text: words.detail })),
      h("span", { class: "vault-due-state" }, pill(words.text, words.tone), item.owner && h("span", { class: "dim", title: "Who replaces it", text: item.owner })),
      button({ label: "Replace", small: true, title: "Opens the tool that takes the new values and records today's date", onclick: () => onReplace(item) }),
    );
  }

  function paint() {
    const pressing = rows.filter((item) => item.state === "due" || item.state === "soon");
    if (rows.length === 0) {
      pickerHolder.replaceChildren();
      more.replaceChildren();
      list.replaceChildren(
        h("li", {}, notice({ glyph: "clock", title: "No secret records when it was replaced", body: "Give a secret the date it was last replaced and how often that should happen, in its form under Rotation and other details. It then shows here when it is due." })),
      );
      return;
    }
    if (pressing.length === 0 || pressing.length === rows.length) filter = "all";
    const picker = segmented([["pressing", `Due or due soon · ${pressing.length}`], ["all", `All · ${rows.length}`]], (value) => {
      filter = value;
      all = false;
      paint();
    });
    picker.set(filter);
    pickerHolder.replaceChildren(...(pressing.length > 0 && pressing.length < rows.length ? [picker.element] : []));
    const shown = filter === "pressing" ? pressing : rows;
    list.replaceChildren(...(all ? shown : shown.slice(0, SHOWN_AT_FIRST)).map(row));
    more.replaceChildren(
      ...(shown.length > SHOWN_AT_FIRST && !all
        ? [
            button({
              label: `Show all ${shown.length}`, small: true, tone: "ghost",
              onclick: () => {
                all = true;
                paint();
              },
            }),
          ]
        : []),
    );
  }

  return {
    element,
    paint(given, fromSeveral) {
      rows = [...given].sort(byUrgency);
      several = fromSeveral;
      filter = "pressing";
      paint();
    },
  };
}
