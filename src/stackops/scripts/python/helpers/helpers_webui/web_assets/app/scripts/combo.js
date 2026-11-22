import { h, icon } from "/assets/scripts/dom.js";
import { highlight } from "./widgets.js";

const LIST_GAP = 6;
const LIST_MAX_HEIGHT = 340;

// One input with a floating suggestion list: a dropdown when `suggest` returns fixed options, a search box with autofill when it filters as you type.
export function createCombo({ value = "", placeholder = "", glyph, label, suggest, onInput, onPick, large = false, readOnly = false, emptyText = "Nothing matches" }) {
  const input = h("input", {
    class: "combo-input", type: "text", spellcheck: "false", autocomplete: "off", placeholder, value, "aria-label": label, role: "combobox", "aria-expanded": "false",
    readonly: readOnly,
  });
  const list = h("div", { class: "combo-list", role: "listbox" });
  const element = h("div", { class: `combo${large ? " large" : ""}${readOnly ? " pick-only" : ""}` }, glyph && icon(glyph, large ? 20 : 15), input, h("span", { class: "combo-caret" }, icon("down", 14)));
  let options = [];
  let active = -1;
  let ticket = 0;
  let shown = false;

  function place() {
    const box = element.getBoundingClientRect();
    const below = window.innerHeight - box.bottom;
    const above = below < 220 && box.top > below;
    list.classList.toggle("above", above);
    list.style.left = `${box.left}px`;
    list.style.width = `${box.width}px`;
    list.style.top = above ? "auto" : `${box.bottom + LIST_GAP}px`;
    list.style.bottom = above ? `${window.innerHeight - box.top + LIST_GAP}px` : "auto";
    list.style.maxHeight = `${Math.min(LIST_MAX_HEIGHT, (above ? box.top : below) - 16)}px`;
  }

  function show() {
    if (shown) return;
    shown = true;
    document.body.append(list);
    place();
    element.classList.add("open");
    input.setAttribute("aria-expanded", "true");
    window.addEventListener("scroll", place, true);
    window.addEventListener("resize", place);
  }

  function hide() {
    if (!shown) return;
    shown = false;
    list.remove();
    element.classList.remove("open");
    input.setAttribute("aria-expanded", "false");
    window.removeEventListener("scroll", place, true);
    window.removeEventListener("resize", place);
  }

  function mark() {
    [...list.children].forEach((row, index) => row.setAttribute("aria-selected", String(index === active)));
    list.children[active]?.scrollIntoView({ block: "nearest" });
  }

  function pick(option) {
    if (option.fill !== false) input.value = option.value;
    onPick?.(option);
    if (option.keepOpen) refresh(false);
    else hide();
  }

  // Only typing pre-selects the first suggestion, and not once the text ends in a slash: a finished folder name is not a prefix to complete. Then, as on focus or after a folder was just picked, Enter and Tab belong to the form, not to the list.
  async function refresh(preselect) {
    const mine = (ticket += 1);
    const term = readOnly ? "" : input.value;
    const found = await suggest(term);
    if (mine !== ticket || document.activeElement !== input) return;
    options = found;
    active = preselect && options.length && term && !/[\\/]$/.test(term) ? 0 : -1;
    list.replaceChildren(
      ...(options.length
        ? options.map((option, index) =>
            h(
              "div",
              {
                class: "combo-option", role: "option", style: `--i:${Math.min(index, 10)}`,
                onmousedown: (event) => {
                  event.preventDefault();
                  pick(option);
                },
                onmousemove: () => {
                  if (active === index) return;
                  active = index;
                  mark();
                },
              },
              option.lead,
              h("div", { class: "combo-text" }, h("span", { class: "combo-label" }, highlight(option.label ?? option.value, term)), option.hint && h("span", { class: "combo-hint", text: option.hint })),
              option.trail,
            ),
          )
        : [h("p", { class: "combo-empty", text: emptyText })]),
    );
    show();
    place();
    mark();
  }

  input.addEventListener("focus", () => refresh(false));
  input.addEventListener("click", () => !shown && refresh(false));
  input.addEventListener("blur", hide);
  input.addEventListener("input", () => {
    onInput?.(input.value);
    refresh(true);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (!shown) return void refresh(false);
      active = (active + (event.key === "ArrowDown" ? 1 : options.length - 1) + (active < 0 && event.key === "ArrowUp" ? 1 : 0)) % Math.max(options.length, 1);
      mark();
    } else if ((event.key === "Enter" || event.key === "Tab") && shown && options[active]) {
      event.preventDefault();
      pick(options[active]);
    } else if (event.key === "Escape" && shown) {
      event.preventDefault();
      event.stopPropagation();
      hide();
    }
  });

  return {
    element, input,
    setValue(next) {
      input.value = next;
    },
  };
}
