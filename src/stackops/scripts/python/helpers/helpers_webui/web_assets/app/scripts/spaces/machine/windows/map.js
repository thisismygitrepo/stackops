import { h } from "/assets/scripts/dom.js";
import { hueOf, initialsOf } from "../../../words.js";
import { sizeText, titleOf } from "./words.js";

const share = (value) => `${(value * 100).toFixed(3)}%`;

// The desktop drawn to scale: every display where it sits beside the others, and on them the windows that are showing, each in its app's colour.
// Under it, a shelf with the windows that are put away. A window here is a button that ticks its row in the list; pointing at one lights that row.
// A design choice: big windows are drawn first and small ones over them, not in the order they are stacked on the real screen. The real order
// would hide every window behind a maximized one, and the point of the map is to see and reach them all.
export function createScreenMap(view) {
  const desk = h("div", { class: "windows-desk" });
  const shelf = h("div", { class: "windows-shelf" });
  const element = h("div", { class: "windows-map" }, desk, shelf);
  const marks = new Map();

  function mark(entry, node) {
    marks.set(entry.id, node);
    node.addEventListener("click", () => view.toggle(entry.id, !view.picked.has(entry.id)));
    node.addEventListener("pointerenter", () => view.hover(entry.id));
    node.addEventListener("pointerleave", () => view.hover(null));
    return node;
  }

  function render(model) {
    marks.clear();
    const left = Math.min(...model.screens.map((screen) => screen.x));
    const top = Math.min(...model.screens.map((screen) => screen.y));
    const width = Math.max(...model.screens.map((screen) => screen.x + screen.width)) - left;
    const height = Math.max(...model.screens.map((screen) => screen.y + screen.height)) - top;
    // A window that reaches past the last display is cut at the desktop's edge, so nothing is drawn outside the map.
    const place = (frame) => {
      const x = Math.max(frame.x, left);
      const y = Math.max(frame.y, top);
      const right = Math.min(frame.x + frame.width, left + width);
      const bottom = Math.min(frame.y + frame.height, top + height);
      return `left:${share((x - left) / width)};top:${share((y - top) / height)};width:${share(Math.max(right - x, 0) / width)};height:${share(Math.max(bottom - y, 0) / height)}`;
    };
    const several = model.screens.length > 1;
    const screens = model.screens.map((screen) => h("div", { class: "windows-screen", style: place(screen) }, h("span", { class: "windows-screen-tag", text: several ? `${screen.name} · ${sizeText(screen)}` : sizeText(screen) })));
    const panes = model.windows
      .filter((entry) => entry.showing && entry.screen !== null)
      .sort((first, second) => second.area - first.area)
      .map((entry) => mark(entry, h("button", { class: "windows-pane", type: "button", style: `${place(entry.frame)};--hue:${hueOf(entry.app)}`, title: `${entry.app} · ${titleOf(entry)}`, "aria-label": `${entry.app}, ${titleOf(entry)}` }, h("span", { text: entry.app }))));
    desk.style.setProperty("--ratio", String(width / height));
    desk.replaceChildren(...screens, ...panes);
    const away = model.windows.filter((entry) => !entry.showing);
    shelf.hidden = away.length === 0;
    shelf.replaceChildren(
      h("span", { text: away.every((entry) => entry.minimized) ? "Minimized" : "Minimized or hidden" }),
      ...away.map((entry) => mark(entry, h("button", { class: "windows-chip", type: "button", style: `--hue:${hueOf(entry.app)}`, title: `${entry.app} · ${titleOf(entry)}`, "aria-label": `${entry.app}, ${titleOf(entry)}`, text: initialsOf(entry.app) }))),
    );
    sync();
  }

  // What changes without the windows changing: which are ticked, which the filters leave out, and which one the pointer is on in the list.
  function sync() {
    for (const [id, node] of marks) {
      node.classList.toggle("picked", view.picked.has(id));
      node.classList.toggle("faded", !view.shown.has(id));
      node.classList.toggle("lit-up", view.hovered === id);
      node.setAttribute("aria-pressed", String(view.picked.has(id)));
    }
  }

  return { element, render, sync };
}
