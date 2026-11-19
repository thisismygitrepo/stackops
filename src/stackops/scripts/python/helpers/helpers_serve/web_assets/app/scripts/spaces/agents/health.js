import { h } from "/assets/scripts/dom.js";
import { notice } from "../../widgets.js";

export function createHealthSection() {
  const element = h("div", { class: "agents-section" }, notice({ glyph: "bot", title: "Health", body: "This section is being built." }));
  return { element, show() {} };
}
