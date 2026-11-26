import { h } from "/assets/scripts/dom.js";
import { openDialog } from "../../../overlays.js";
import { avatar, button, glyphTile } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { titleOf } from "./words.js";

// The last stop before a window is closed: each one by name, and what closing means. Resolves to true only on an explicit yes.
export function confirmClose(entries, ask) {
  const one = entries.length === 1;
  const dialog = openDialog({ label: "Close windows", size: "windows-confirm" });
  const body = one
    ? `It closes as if you pressed its own close button. ${entries[0].app} may first ask about unsaved changes. Anything it does not ask about is lost.`
    : "Each one closes as if you pressed its own close button. An app may first ask about unsaved changes. Anything it does not ask about is lost.";
  dialog.body.append(
    h("header", { class: "windows-confirm-head" }, glyphTile("close", 350, 46), h("div", {}, h("h2", { text: one ? "Close this window?" : `Close ${plural(entries.length, "window")}?` }), h("p", { text: body }))),
    h("ul", { class: "windows-confirm-list" }, entries.map((entry) => h("li", {}, avatar(entry.app, 28), h("strong", { text: titleOf(entry) }), h("span", { text: entry.app })))),
    h("div", { class: "dialog-actions" }, ask, button({ label: one ? "Keep it open" : "Keep them open", onclick: () => dialog.close(false) }), button({ label: one ? "Close window" : `Close ${plural(entries.length, "window")}`, glyph: "close", tone: "danger", onclick: () => dialog.close(true) })),
  );
  return dialog.closed.then((answer) => answer === true);
}
