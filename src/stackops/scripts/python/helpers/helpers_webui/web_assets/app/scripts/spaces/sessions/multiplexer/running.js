import { h, icon } from "/assets/scripts/dom.js";
import { avatar } from "../../../widgets.js";
import { plural } from "../../../words.js";

const FACES = 4;

// What is running in one multiplexer, as one line: a face for each of the first few sessions, the count, and their names.
// `info` is the server's answer, and nothing while that is still on its way.
export function runningLine(info) {
  if (!info) return h("div", { class: "mux-running waiting" }, h("i", { class: "ring" }), h("span", { text: "Looking for sessions" }));
  if (info.count === null) return h("div", { class: "mux-running unread", title: info.problem }, icon("alert", 15), h("span", { text: "Its sessions could not be read" }), h("small", { text: info.problem }));
  if (info.count === 0) return h("div", { class: "mux-running idle" }, h("i", { class: "mux-dot" }), h("span", { text: "Nothing running" }));
  const hidden = info.count - Math.min(info.names.length, FACES);
  return h(
    "div",
    { class: "mux-running live", title: info.names.join(", ") },
    h("span", { class: "mux-faces" }, info.names.slice(0, FACES).map((name) => avatar(name, 24)), hidden > 0 && h("b", { text: `+${hidden}` })),
    h("strong", { text: `${plural(info.count, "session")} running` }),
    h("span", { class: "mux-names", text: info.names.join(", ") }),
  );
}
