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
  let frame = 0;
  // Where the box was when the list was last put under it, so a frame in which nothing moved writes nothing.
  let placedFor = "";

  function place() {
    const box = element.getBoundingClientRect();
    const spot = [box.left, box.top, box.width, box.height, window.innerHeight].join();
    if (spot === placedFor) return;
    placedFor = spot;
    const below = window.innerHeight - box.bottom;
    const above = below < 220 && box.top > below;
    list.classList.toggle("above", above);
    list.style.left = `${box.left}px`;
    list.style.width = `${box.width}px`;
    list.style.top = above ? "auto" : `${box.bottom + LIST_GAP}px`;
    list.style.bottom = above ? `${window.innerHeight - box.top + LIST_GAP}px` : "auto";
    list.style.maxHeight = `${Math.min(LIST_MAX_HEIGHT, (above ? box.top : below) - 16)}px`;
  }

  // The list hangs off the body, so nothing moves it along with its box, and the box does move: the popover or dialog it sits in is still
  // growing into place when the list opens, the page scrolls, the window changes size. So the list is put under the box again on every frame
  // while it is open, which costs one measurement when nothing moved. A box taken off the page takes its list with it.
  function follow() {
    if (!element.isConnected) return hide();
    place();
    frame = requestAnimationFrame(follow);
  }

  function show() {
    if (shown) return;
    shown = true;
    document.body.append(list);
    element.classList.add("open");
    input.setAttribute("aria-expanded", "true");
    placedFor = "";
    follow();
  }

  function hide() {
    if (!shown) return;
    shown = false;
    cancelAnimationFrame(frame);
    list.remove();
    element.classList.remove("open");
    input.setAttribute("aria-expanded", "false");
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
