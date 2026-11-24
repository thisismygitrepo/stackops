import { h } from "/assets/scripts/dom.js";
import { countUp } from "../../../motion.js";
import { plural } from "../../../words.js";

// The top of the page: how many windows are open and in what state, beside the map of the screens. On a machine that does not say where its
// windows are there is no map, and the counts stand alone.
export function createWindowsHero(map) {
  const figure = h("strong", { class: "windows-figure num", text: "—" });
  const line = h("p");
  const facts = h("div", { class: "windows-facts" });
  const element = h("section", { class: "windows-hero" }, h("div", { class: "windows-total" }, h("span", { class: "overline", text: "Open right now" }), figure, line, facts), map.element);

  function paint(model) {
    const { windows } = model;
    const count = (test) => windows.filter(test).length;
    countUp(figure, windows.length);
    line.textContent = windows.length === 0 ? "No windows are open." : `${windows.length === 1 ? "window" : "windows"} in ${plural(new Set(windows.map((entry) => entry.app)).size, "app")}`;
    const states = [
      [count((entry) => entry.showing), "on screen"],
      [count((entry) => entry.minimized), "minimized"],
      [count((entry) => entry.hidden && !entry.minimized), "hidden"],
      [count((entry) => entry.full_screen), "full screen"],
      [count((entry) => entry.stray), "off screen"],
    ];
    facts.replaceChildren(...states.filter(([amount]) => amount > 0).map(([amount, word]) => h("span", { class: "windows-fact" }, h("b", { text: String(amount) }), word)));
    map.element.hidden = !model.located;
    element.classList.toggle("plain", !model.located);
  }

  return { element, paint };
}
