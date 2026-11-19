import { h } from "/assets/scripts/dom.js";
import { notice } from "../../widgets.js";

export function createWorkbenchSection() {
  const element = h("div", { class: "agents-section" }, notice({ glyph: "cube", title: "Workbench", body: "This section is being built." }));
  return { element, show() {} };
}
