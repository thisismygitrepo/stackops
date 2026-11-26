import { h, icon } from "/assets/scripts/dom.js";
import { button } from "./widgets.js";

const CLOSE_MILLISECONDS = 220;
const stack = [];
// Everything behind a sheet or dialog lives in here; overlays, suggestion lists and messages are attached to the body.
const app = document.getElementById("app");

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || stack.length === 0) return;
  event.preventDefault();
  stack.at(-1).dismiss();
});

// From the top down, so each layer hands the focus to the one under it.
// A design choice: a layer holding unsaved work is left open and lies over whatever page comes next, until the person saves or discards. Asking here would mean every page change waits for an answer.
export function closeAll() {
  for (const layer of [...stack].reverse()) if (!layer.holdsWork?.()) layer.close();
}

// `canDismiss` is asked when Escape or a click outside would close the layer, so one holding unsaved work can ask first. `close` never asks.
// `holdsWork` says the same without asking anything: it is what `closeAll` reads, and it must have no side effects.
function mount(backdrop, panel, dismissOnBackdrop, canDismiss = () => true, holdsWork = () => false) {
  let settle;
  const closed = new Promise((resolve) => (settle = resolve));
  // A popover would paint above the new backdrop, so it does not outlive the dialog or sheet that opens over it.
  for (const open of [...stack]) if (open.popover) open.close();
  const previousFocus = document.activeElement;
  const layer = {
    holdsWork,
    dismiss: () => canDismiss() && layer.close(),
    // Only the fade waits for the animation. The page, the focus and the answer are handed back straight away, so search reopens and a confirmed action starts without the wait.
    close(result) {
      const index = stack.indexOf(layer);
      if (index < 0) return;
      stack.splice(index, 1);
      backdrop.classList.add("closing");
      app.inert = stack.some((open) => !open.popover);
      setTimeout(() => backdrop.remove(), CLOSE_MILLISECONDS);
      // One turn later and not in this one: an Enter that closes a layer from its keydown would otherwise also press the button the focus lands on.
      setTimeout(() => {
        // Focus goes back unless something outside this layer already took it. A layer that cannot hand it back still lets go of it: a suggestion list closes when its box loses focus, and not every browser says so when the box is removed.
        const focused = document.activeElement;
        if (focused === document.body || backdrop.contains(focused)) {
          if (previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus({ preventScroll: true });
          if (backdrop.contains(document.activeElement)) document.activeElement.blur();
        }
        // After the focus, so a layer opened on this answer finds the focus where it belongs and hands it back there in its turn.
        settle(result);
      });
    },
  };
  if (dismissOnBackdrop) backdrop.addEventListener("pointerdown", (event) => event.target === backdrop && layer.dismiss());
  stack.push(layer);
  document.body.append(backdrop);
  // The dim stops the mouse; this stops the keyboard from working the page behind it.
  app.inert = true;
  panel.tabIndex = -1;
  panel.focus({ preventScroll: true });
  return { close: layer.close, dismiss: layer.dismiss, closed };
}

export function openSheet({ label, wide = false }) {
  const body = h("div", { class: "sheet-body" });
  const foot = h("div", { class: "sheet-foot", hidden: true });
  const panel = h("aside", { class: `sheet${wide ? " wide" : ""}`, role: "dialog", "aria-label": label, "aria-modal": "true" }, body, foot);
  const backdrop = h("div", { class: "backdrop side" }, panel);
  const layer = mount(backdrop, panel, true);
  panel.prepend(h("button", { class: "icon-btn sheet-close", type: "button", "aria-label": "Close", onclick: () => layer.close() }, icon("close", 16)));
  return { body, foot, panel, ...layer };
}

export function openDialog({ label, size = "", canDismiss, holdsWork }) {
  const body = h("div", { class: "dialog-body" });
  const panel = h("div", { class: `dialog ${size}`, role: "dialog", "aria-label": label, "aria-modal": "true" }, body);
  const backdrop = h("div", { class: "backdrop center" }, panel);
  return { body, panel, ...mount(backdrop, panel, true, canDismiss, holdsWork) };
}

// What makes the "Ask an agent" button of a question from its title and body. It is set once when the app starts (main.js), since the
// button's own module is built on this one and cannot be reached from here.
let askMaker = () => null;
export const setQuestionAsk = (maker) => (askMaker = maker);
export const questionAsk = (question) => askMaker(question);

// Every question has an "Ask an agent" button, apart from its answers, so what it would do can be explained before it is answered. One that
// knows more than its own words (which processes, which file) passes its own button as `ask`.
export function confirmAction({ title, body, confirm, tone = "primary", ask = askMaker({ title, body }) }) {
  const dialog = openDialog({ label: title, size: "small" });
  dialog.body.append(
    h("h2", { text: title }),
    h("p", { text: body }),
    h("div", { class: "dialog-actions" }, ask, button({ label: "Cancel", onclick: () => dialog.close(false) }), button({ label: confirm, tone, onclick: () => dialog.close(true) })),
  );
  return dialog.closed.then((answer) => answer === true);
}

// The popover each popover was opened from, for one whose button sits inside another: a press in the inner one is not a press outside the outer.
const openers = new WeakMap();

export function openPopover(anchor, content, { align = "end" } = {}) {
  const panel = h("div", { class: "popover", role: "dialog" }, content);
  openers.set(panel, anchor.closest(".popover"));
  document.body.append(panel);
  // Under the button, or over it when there is more room there, and always inside the window: a panel that fits on neither side lies over its button, and one taller than the window scrolls.
  const place = () => {
    const box = anchor.getBoundingClientRect();
    const width = panel.offsetWidth;
    const height = panel.offsetHeight;
    const left = align === "end" ? box.right - width : box.left;
    panel.style.left = `${Math.max(12, Math.min(left, window.innerWidth - width - 12))}px`;
    const below = window.innerHeight - box.bottom;
    const above = below < height + 24 && box.top > below;
    panel.classList.toggle("above", above);
    panel.style.top = `${Math.max(12, Math.min(above ? box.top - height - 8 : box.bottom + 8, window.innerHeight - height - 12))}px`;
  };
  place();
  // Placed again when its content grows, as when "More options" opens.
  const resized = new ResizeObserver(place);
  resized.observe(panel);
  const outside = (event) => {
    if (!(event.target instanceof Element) || anchor.contains(event.target) || event.target.closest(".combo-list")) return;
    for (let inside = event.target.closest(".popover"); inside; inside = openers.get(inside)) if (inside === panel) return;
    layer.close();
  };
  // The popover follows its button when the page scrolls, and goes when the button leaves the window.
  const follow = (event) => {
    if (event.target instanceof Element && (panel.contains(event.target) || event.target.closest(".combo-list"))) return;
    const box = anchor.getBoundingClientRect();
    if (box.bottom < 0 || box.top > window.innerHeight) layer.close();
    else place();
  };
  // A second press on the button closes the popover. This runs ahead of the button's own handler, which would open another one.
  const toggle = (event) => {
    event.stopImmediatePropagation();
    layer.close();
  };
  const layer = {
    popover: true,
    dismiss: () => layer.close(),
    close() {
      const index = stack.indexOf(layer);
      if (index < 0) return;
      stack.splice(index, 1);
      document.removeEventListener("pointerdown", outside, true);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", follow, true);
      anchor.removeEventListener("click", toggle, true);
      resized.disconnect();
      panel.classList.add("closing");
      anchor.classList.remove("open");
      // Focus held inside goes back to the button, which also closes a suggestion list one of the popover's boxes had open.
      // At once, unlike a sheet or dialog: a dialog opened straight after has to find the focus on the button. A design choice with a known edge: a popover closed from an Enter keydown, which nothing does today, would be opened again by that same key press.
      if (panel.contains(document.activeElement)) anchor.focus({ preventScroll: true });
      if (panel.contains(document.activeElement)) document.activeElement.blur();
      setTimeout(() => panel.remove(), CLOSE_MILLISECONDS);
    },
  };
  stack.push(layer);
  anchor.classList.add("open");
  document.addEventListener("pointerdown", outside, true);
  window.addEventListener("resize", place);
  window.addEventListener("scroll", follow, true);
  anchor.addEventListener("click", toggle, true);
  // The popover is the last thing in the page, so Tab from its button would never reach it: focus starts inside, unless the caller puts it on a control of its own.
  panel.tabIndex = -1;
  panel.focus({ preventScroll: true });
  return { close: layer.close };
}
