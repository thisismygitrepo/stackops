import { h, icon } from "/assets/scripts/dom.js";
import { avatar, button, pill } from "../../../widgets.js";
import { runningLine } from "./running.js";
import { CAPABILITIES, ROLES, standingOf, wordsOf } from "./words.js";

// One multiplexer as something to pick. `holds` lists the defaults it is right now, and `marked` the ones whoever opened the page proposed it for.
// `onPick(role, name, control)` is handed the button that asked. One that cannot work here is greyed out, with the reason and the way forward
// in place of its sessions. Returns the card and `setRunning`, which fills in what is running in it once that is known.
export function multiplexerCard({ item, capabilities, holds, marked, platform, onPick }) {
  const { title, about } = wordsOf(item.name);
  const standing = standingOf(item, platform);
  const ready = standing.id === "ready";
  const running = h("div", { class: "mux-state" }, runningLine());
  const way = h("div", { class: "mux-way" }, h("p", { text: standing.reason }), standing.href && h("a", { class: "btn small", href: standing.href }, icon("download", 14), h("span", { text: standing.action })));
  const controls = item.roles.map((role) => {
    if (holds.includes(role)) return h("span", { class: "mux-holds" }, icon("check", 14), h("span", { text: ROLES[role].holds }));
    const control = button({ label: ROLES[role].pick, small: true, onclick: () => onPick(role, item.name, control) });
    control.classList.add("mux-pick");
    control.classList.toggle("suggested", ready && marked[role] === item.name);
    control.disabled = !ready;
    return control;
  });
  const works = capabilities.map((id) => {
    const on = item.works_with.includes(id);
    const { label, what } = CAPABILITIES[id] ?? { label: id, what: "" };
    return h("li", { class: on ? "on" : "off", title: `${what} ${on ? "Works" : "Does not work"} with ${title}.`.trim() }, icon(on ? "check" : "close", 12), h("span", { text: label }), h("span", { class: "mux-unseen", text: on ? ", works" : ", does not work" }));
  });
  const element = h(
    "article",
    { class: `mux-card lit ${standing.id}${holds.length ? " current" : ""}`, tabindex: "-1" },
    h(
      "header",
      {},
      avatar(item.name, 44),
      h("div", { class: "mux-card-title" }, h("h3", { text: title }), h("span", { class: "dim", text: item.version ? `Version ${item.version}` : item.installed ? "Version unknown" : "" })),
      pill(...standing.pill),
    ),
    h("p", { class: "mux-about", text: about }),
    ready ? running : way,
    h("ul", { class: "mux-works", "aria-label": "What else works with it" }, works),
    h("footer", {}, controls),
  );
  return { element, setRunning: (info) => running.replaceChildren(runningLine(info)) };
}
