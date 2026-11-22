import { h, icon, toast } from "/assets/scripts/dom.js";
import { countUp } from "./motion.js";
import { hueOf, initialsOf } from "./words.js";

export function button({ label, glyph, tone = "plain", small = false, title, onclick }) {
  return h("button", { class: `btn ${tone}${small ? " small" : ""}`, type: "button", title, onclick }, glyph && icon(glyph, small ? 14 : 16), label && h("span", { text: label }));
}

export const iconButton = (glyph, label, onclick) => h("button", { class: "icon-btn", type: "button", title: label, "aria-label": label, onclick }, icon(glyph, 16));
export const pill = (text, tone = "") => h("span", { class: `pill ${tone}`, text });
export const avatar = (name, size = 44) => h("span", { class: "avatar", style: `--hue:${hueOf(name)};--size:${size}px`, text: initialsOf(name) });
export const glyphTile = (glyph, hue, size = 44) => h("span", { class: "tile", style: `--hue:${hue};--size:${size}px` }, icon(glyph, Math.round(size * 0.46)));
export const emojiTile = (emoji, name, size = 44) => h("span", { class: "tile emoji", style: `--hue:${hueOf(name)};--size:${size}px`, text: emoji });
export const skeleton = (count, shape) => Array.from({ length: count }, (_, index) => h("div", { class: `skeleton ${shape}`, style: `--i:${index}` }));

export function notice({ glyph, title, body, action, tone = "" }) {
  return h("div", { class: `notice ${tone}` }, h("span", { class: "notice-glyph" }, icon(glyph, 22)), h("h3", { text: title }), body && h("p", { text: body }), action);
}

export function sectionHead(title, ...tail) {
  return h("div", { class: "section-head" }, h("h2", { text: title }), ...tail);
}

export function highlight(text, term) {
  const index = term ? text.toLowerCase().indexOf(term.toLowerCase()) : -1;
  if (index < 0) return [text];
  return [text.slice(0, index), h("mark", { text: text.slice(index, index + term.length) }), text.slice(index + term.length)];
}

export function searchInput({ placeholder, oninput }) {
  const input = h("input", { type: "search", placeholder, spellcheck: "false", autocomplete: "off", "aria-label": placeholder, oninput: () => oninput(input.value) });
  return { element: h("label", { class: "search-input" }, icon("search", 15), input), input };
}

export function segmented(options, onPick) {
  const buttons = options.map(([value, label]) => h("button", { type: "button", text: label, onclick: () => onPick(value) }));
  const thumb = h("i", { class: "segmented-thumb" });
  const element = h("div", { class: "segmented", role: "group" }, thumb, buttons);
  let index = -1;
  const place = () => {
    const chosen = buttons[index];
    if (chosen) thumb.style.cssText = `width:${chosen.offsetWidth}px;transform:translateX(${chosen.offsetLeft}px)`;
  };
  // A control can be set before it is on the page (a panel's remembered options), where a button has no width yet. So the highlight is also placed whenever the control gets or changes its size.
  new ResizeObserver(place).observe(element);
  function set(value) {
    index = options.findIndex(([candidate]) => candidate === value);
    buttons.forEach((item, position) => item.setAttribute("aria-pressed", String(position === index)));
    element.classList.toggle("unset", index < 0);
    requestAnimationFrame(place);
  }
  return { element, set };
}

export function stat({ glyph, hue, label, href }) {
  const number = h("strong", { text: "—" });
  const hint = h("span", { class: "stat-hint" });
  const element = h(href ? "a" : "div", { class: "stat lit", href }, glyphTile(glyph, hue, 38), h("div", { class: "stat-text" }, h("span", { class: "stat-label", text: label }), number, hint));
  return {
    element,
    set(value, note) {
      if (typeof value === "number") countUp(number, value);
      else number.textContent = value;
      hint.textContent = note ?? "";
      element.classList.add("ready");
    },
  };
}

export function copyChip(text, label = text) {
  const element = h("button", { class: "copy-chip", type: "button", title: "Copy" }, h("span", { text: label }), icon("copy", 13));
  element.addEventListener("click", async (event) => {
    event.stopPropagation();
    if (!navigator.clipboard) return toast("The browser only allows copying on localhost or HTTPS.");
    await navigator.clipboard.writeText(text);
    element.classList.add("copied");
    setTimeout(() => element.classList.remove("copied"), 1200);
  });
  return element;
}

// Copy and Save for any text output; `read` is called at click time. Save is there because browsers only allow copying on localhost or HTTPS.
export function outputActions(read, name) {
  const copy = iconButton("copy", "Copy the output", async () => {
    if (!navigator.clipboard) return toast("The browser only allows copying on localhost or HTTPS. Save the output instead.");
    await navigator.clipboard.writeText(read());
    copy.replaceChildren(icon("check", 16));
    setTimeout(() => copy.replaceChildren(icon("copy", 16)), 1200);
  });
  const save = iconButton("download", "Save the output as a file", () => {
    const address = URL.createObjectURL(new Blob([read()], { type: "text/plain" }));
    h("a", { href: address, download: `${name}.txt` }).click();
    setTimeout(() => URL.revokeObjectURL(address), 1000);
  });
  return [copy, save];
}

export function keyValue(pairs) {
  return h("dl", { class: "facts" }, pairs.filter(([, value]) => value !== null && value !== undefined && value !== "").flatMap(([key, value]) => [h("dt", { text: key }), h("dd", {}, value)]));
}
