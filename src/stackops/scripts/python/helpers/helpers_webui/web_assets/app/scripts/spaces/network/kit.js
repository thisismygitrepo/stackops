import { h, icon } from "/assets/scripts/dom.js";
import { backLink } from "../../space_kit.js";
import { button, notice } from "../../widgets.js";

// The parts every view of the Network page is built from. Their rules are in network.css under the same names.
export function partHead({ title, lede, actions }) {
  return h(
    "header",
    { class: "view-head" },
    h("div", { class: "view-title" }, backLink("#/network", "Network"), h("h1", { text: title }), h("p", { text: lede })),
    h("div", { class: "view-actions" }, actions),
  );
}

// Puts new content into a node, leaving out what is nothing, so a part can be written as `condition && node` as inside `h`.
export const fill = (node, ...children) => node.replaceChildren(...children.flat().filter((child) => child !== null && child !== undefined && child !== false && child !== ""));

export const card = (properties, ...content) => h("section", { ...properties, class: `network-card ${properties.class ?? ""}` }, ...content);
export const cardHead = (title, ...tail) => h("header", { class: "network-card-head" }, h("h2", { text: title }), ...tail);
export const mark = (tone, glyph, size = 26) => h("span", { class: `network-mark ${tone}` }, icon(glyph, size));
export const reason = (text) => h("p", { class: "network-reason" }, icon("info", 14), h("span", { text }));

// A problem that takes the place of a view's content. Most often a server started before these routes existed, which only a restart brings in.
export function failNotice(error, retry) {
  return notice({
    glyph: "alert", tone: "bad", title: "This didn't load",
    body: `${error.message.replace(/[.\s]*$/, "")}. If StackOps was just updated, restart the web UI and open this page again.`,
    action: button({ label: "Try again", glyph: "refresh", small: true, onclick: retry }),
  });
}

// Signal strength as four bars, lit from the left. `percent` of null draws them all unlit.
export function signalBars(percent, size = "") {
  const lit = percent === null ? 0 : Math.max(1, Math.ceil(percent / 25));
  const tone = percent === null ? "" : percent >= 50 ? "good" : percent >= 25 ? "warn" : "bad";
  return h("span", { class: `network-bars ${size} ${tone}`, role: "img", "aria-label": percent === null ? "Signal unknown" : `Signal ${percent} percent` }, [1, 2, 3, 4].map((step) => h("i", { class: step <= lit ? "lit" : "", style: `--step:${step}` })));
}

// A numbered list of what something will do, in order.
export function stepList(steps) {
  return h("ol", { class: "network-steps" }, steps.map((step, index) => h("li", {}, h("b", { text: String(index + 1) }), h("div", {}, h("strong", { text: step.title }), h("span", { text: step.detail })))));
}

// One choice between a few, each with a sentence that says what it means. `blocked` maps a choice to why it cannot be picked here.
export function choiceCards(options, { value, blocked = {}, onPick }) {
  const cards = options.map(([id, title, text]) => {
    const why = blocked[id];
    return h(
      "button",
      { class: "network-choice", type: "button", disabled: Boolean(why), "aria-pressed": String(id === value), "data-id": id, onclick: () => set(id) },
      h("i", { class: "network-radio" }),
      h("span", {}, h("strong", { text: title }), h("span", { text: text }), why && h("em", { text: why })),
    );
  });
  const element = h("div", { class: "network-choices", role: "group" }, cards);
  function set(id) {
    for (const item of cards) item.setAttribute("aria-pressed", String(item.dataset.id === id));
    onPick(id);
  }
  return { element };
}
