import { h } from "/assets/scripts/dom.js";
import { button, highlight, pill } from "../../../widgets.js";
import { hueOf } from "../../../words.js";
import { ACTIONS, sizeText, titleOf } from "./words.js";

const MINI_WIDTH = 46;
const MINI_HEIGHT = 30;
const share = (value) => `${(Math.min(Math.max(value, 0), 1) * 100).toFixed(2)}%`;

// A window's place on its screen, small enough for a row: the screen to scale, and the window on it. A window that is put away keeps its place
// as an outline, which is where it comes back to.
function miniature(entry, screen) {
  if (!entry.frame || !screen) return h("span", { class: "windows-mini" });
  const scale = Math.min(MINI_WIDTH / screen.width, MINI_HEIGHT / screen.height);
  const { x, y, width, height } = entry.frame;
  const spot = `left:${share((x - screen.x) / screen.width)};top:${share((y - screen.y) / screen.height)};right:${share(1 - (x + width - screen.x) / screen.width)};bottom:${share(1 - (y + height - screen.y) / screen.height)}`;
  return h(
    "span",
    { class: `windows-mini${entry.showing ? "" : " away"}`, title: `Where it sits on ${screen.name.toLowerCase()}` },
    h("i", { style: `width:${Math.round(screen.width * scale)}px;height:${Math.round(screen.height * scale)}px` }, h("b", { style: `${spot};--hue:${hueOf(entry.app)}` })),
  );
}

function statePills(entry) {
  const described = (text, tone, title) => Object.assign(pill(text, tone), { title });
  return [
    entry.minimized && described("Minimized", "", "Put away. Restore brings it back."),
    entry.hidden && !entry.minimized && described("Hidden", "", "Its app is hidden as a whole. Bring to front shows it again."),
    entry.full_screen && described("Full screen", "accent", "It fills a screen of its own."),
    entry.stray && described("Off screen", "warn", "It lies outside every screen. Maximize brings it back into view."),
  ];
}

// One of the command's actions as a button on a window's row. An action that cannot work is greyed out and says why when pointed at.
function actionButton(entry, name, { model, view }) {
  const action = ACTIONS[name];
  const blocked = model.blocked[name] ?? (name === "maximize" && entry.full_screen ? "Leave full screen first. Then it can be maximized." : "");
  const node = button({ label: action.label, glyph: action.glyph, tone: "ghost", small: true, title: blocked || action.hint, onclick: () => view.act(name, [entry]) });
  node.classList.add("windows-act", `windows-act-${name}`);
  node.dataset.part = name;
  node.dataset.blocked = blocked ? "yes" : "no";
  return node;
}

// `flat` is the list with every app in one section, where each row says which app its window belongs to.
export function windowRow(entry, { model, view, flat }) {
  const screen = entry.screen === null ? null : model.screens[entry.screen];
  const box = h("input", { class: "windows-check", type: "checkbox", "data-part": "check", "aria-label": `Tick ${titleOf(entry)}, ${entry.app}` });
  box.addEventListener("change", () => view.toggle(entry.id, box.checked));
  const buttons = ["focus", entry.minimized ? "unminimize" : "minimize", "maximize", "close"].map((name) => actionButton(entry, name, { model, view }));
  const facts = [entry.frame && sizeText(entry.frame), screen && model.screens.length > 1 && screen.name].filter(Boolean).join(" · ");
  const main = h(
    "div",
    { class: "windows-main" },
    box,
    model.located && miniature(entry, screen),
    h("div", { class: "windows-text" }, h("strong", { class: entry.title.trim() ? "" : "untitled" }, highlight(titleOf(entry), view.term)), h("span", {}, flat && h("em", { class: "windows-kind" }, highlight(entry.app, view.term)), facts)),
    h("div", { class: "windows-pills" }, statePills(entry)),
    h("div", { class: "windows-actions" }, buttons),
  );
  const row = h("li", { class: "windows-row", "data-key": entry.id }, main);
  main.addEventListener("click", (event) => {
    if (event.target.closest("button, input") || view.busy.has(entry.id)) return;
    view.toggle(entry.id, !box.checked);
  });
  row.addEventListener("pointerenter", () => view.hover(entry.id));
  row.addEventListener("pointerleave", () => view.hover(null));
  return { row, box, buttons };
}
