import { h } from "/assets/scripts/dom.js";
import { notice } from "../../widgets.js";

export function createPromptsSection() {
  const element = h("div", { class: "agents-section" }, notice({ glyph: "sparkle", title: "Prompts", body: "This section is being built." }));
  return { element, show() {} };
}
