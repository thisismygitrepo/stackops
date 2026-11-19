import { h, icon } from "/assets/scripts/dom.js";
import { button } from "./widgets.js";

const CLOSE_MILLISECONDS = 220;
const stack = [];

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape" || stack.length === 0) return;
  event.preventDefault();
  stack.at(-1).close();
});

export function closeAll() {
  for (const layer of [...stack]) layer.close();
}

function mount(backdrop, panel, dismissOnBackdrop) {
  let settle;
  const closed = new Promise((resolve) => (settle = resolve));
  // A popover would paint above the new backdrop, so it does not outlive the dialog or sheet that opens over it.
  for (const open of [...stack]) if (open.popover) open.close();
  const previousFocus = document.activeElement;
  const layer = {
    close(result) {
      const index = stack.indexOf(layer);
      if (index < 0) return;
      stack.splice(index, 1);
      backdrop.classList.add("closing");
      setTimeout(() => {
        // Focus goes back only if nothing newer took it: an overlay opened straight after this one keeps the focus.
        const focused = document.activeElement;
        const kept = focused === document.body || backdrop.contains(focused);
        backdrop.remove();
        if (kept && previousFocus instanceof HTMLElement && previousFocus.isConnected) previousFocus.focus({ preventScroll: true });
        settle(result);
      }, CLOSE_MILLISECONDS);
    },
  };
  if (dismissOnBackdrop) backdrop.addEventListener("pointerdown", (event) => event.target === backdrop && layer.close());
  stack.push(layer);
  document.body.append(backdrop);
  panel.tabIndex = -1;
  panel.focus({ preventScroll: true });
  return { close: layer.close, closed };
}

export function openSheet({ label, wide = false }) {
  const body = h("div", { class: "sheet-body" });
  const foot = h("div", { class: "sheet-foot", hidden: true });
  const panel = h("aside", { class: `sheet${wide ? " wide" : ""}`, role: "dialog", "aria-label": label }, body, foot);
  const backdrop = h("div", { class: "backdrop side" }, panel);
  const layer = mount(backdrop, panel, true);
  panel.prepend(h("button", { class: "icon-btn sheet-close", type: "button", "aria-label": "Close", onclick: () => layer.close() }, icon("close", 16)));
  return { body, foot, panel, ...layer };
}

export function openDialog({ label, size = "" }) {
  const body = h("div", { class: "dialog-body" });
  const panel = h("div", { class: `dialog ${size}`, role: "dialog", "aria-label": label, "aria-modal": "true" }, body);
  const backdrop = h("div", { class: "backdrop center" }, panel);
  return { body, panel, ...mount(backdrop, panel, true) };
}

export function confirmAction({ title, body, confirm, tone = "primary" }) {
  const dialog = openDialog({ label: title, size: "small" });
  dialog.body.append(
    h("h2", { text: title }),
    h("p", { text: body }),
    h("div", { class: "dialog-actions" }, button({ label: "Cancel", onclick: () => dialog.close(false) }), button({ label: confirm, tone, onclick: () => dialog.close(true) })),
  );
  return dialog.closed.then((answer) => answer === true);
}

export function openPopover(anchor, content, { align = "end" } = {}) {
  const panel = h("div", { class: "popover", role: "dialog" }, content);
  document.body.append(panel);
  const place = () => {
    const box = anchor.getBoundingClientRect();
    const width = panel.offsetWidth;
    const left = align === "end" ? box.right - width : box.left;
    panel.style.left = `${Math.max(12, Math.min(left, window.innerWidth - width - 12))}px`;
    const below = window.innerHeight - box.bottom;
    if (below < panel.offsetHeight + 24 && box.top > below) {
      panel.style.top = "auto";
      panel.style.bottom = `${window.innerHeight - box.top + 8}px`;
      panel.classList.add("above");
    } else {
      panel.style.top = `${box.bottom + 8}px`;
      panel.style.bottom = "auto";
    }
  };
  place();
  const outside = (event) => {
    if (!(event.target instanceof Element) || panel.contains(event.target) || anchor.contains(event.target) || event.target.closest(".combo-list")) return;
    layer.close();
  };
  const layer = {
    popover: true,
    close() {
      const index = stack.indexOf(layer);
      if (index < 0) return;
      stack.splice(index, 1);
      document.removeEventListener("pointerdown", outside, true);
      window.removeEventListener("resize", place);
      panel.classList.add("closing");
      anchor.classList.remove("open");
      setTimeout(() => panel.remove(), CLOSE_MILLISECONDS);
    },
  };
  stack.push(layer);
  anchor.classList.add("open");
  document.addEventListener("pointerdown", outside, true);
  window.addEventListener("resize", place);
  return { close: layer.close, place };
}
