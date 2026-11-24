import { h } from "/assets/scripts/dom.js";
import { button, glyphTile } from "../../../widgets.js";
import { plural } from "../../../words.js";

// The bar that comes up once a window is ticked: what is ticked, and the actions that make sense for several windows at once.
export function createWindowsTray({ onMinimize, onRestore, onClose, onClear }) {
  const title = h("strong");
  const note = h("span");
  const clear = button({ label: "Clear", tone: "ghost", title: "Untick every window", onclick: onClear });
  const minimize = button({ label: "Minimize", glyph: "down", onclick: onMinimize });
  const restore = button({ label: "Restore", glyph: "up", title: "Put the ticked windows that are minimized back on the screen", onclick: onRestore });
  const close = button({ label: "Close", glyph: "close", tone: "danger", title: "Close the ticked windows. You are asked first.", onclick: onClose });
  const element = h("div", { class: "tray windows-tray", hidden: true }, glyphTile("layers", 252, 38), h("div", { class: "windows-tray-text" }, title, note), h("span", { class: "spacer" }), clear, minimize, restore, close);

  // `chosen` is the ticked windows, `busy` whether one of them is being changed right now, `blocked` the actions this machine cannot do.
  function paint({ chosen, busy, blocked }) {
    element.hidden = chosen.length === 0;
    if (chosen.length === 0) return;
    const apps = new Set(chosen.map((entry) => entry.app));
    title.textContent = `${plural(chosen.length, "window")} ticked`;
    note.textContent = apps.size === 1 ? `In ${chosen[0].app}` : `In ${apps.size} apps`;
    minimize.disabled = busy || Boolean(blocked.minimize) || chosen.every((entry) => entry.minimized);
    minimize.title = blocked.minimize ?? "Put the ticked windows away without closing them";
    restore.disabled = busy || !chosen.some((entry) => entry.minimized);
    close.disabled = busy;
  }

  return { element, paint };
}
