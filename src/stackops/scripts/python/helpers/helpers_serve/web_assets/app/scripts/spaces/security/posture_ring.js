import { h, icon } from "/assets/scripts/dom.js";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const RADIUS = 46;
const LENGTH = 2 * Math.PI * RADIUS;
// The shortest arc drawn for a group that has anything in it, so that one flagged app among many is still seen.
const SHORTEST_ARC = 5;

function circle(className, attributes) {
  const node = document.createElementNS(SVG_NAMESPACE, "circle");
  node.setAttribute("class", className);
  for (const [name, value] of Object.entries({ cx: 60, cy: 60, r: RADIUS, ...attributes })) node.setAttribute(name, value);
  return node;
}

// The share of installed apps that are clean, worth a look, and flagged, drawn as arcs of one ring; what is left of the ring is still to scan.
// `settled` leaves out the arcs' drawing-in, for a ring that is refreshed in place.
export function postureRing({ clean, review, flagged, total, tone, settled }) {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  svg.setAttribute("viewBox", "0 0 120 120");
  svg.setAttribute("aria-hidden", "true");
  svg.append(circle("ring-track", {}));
  let start = 0;
  for (const [arcTone, count] of [["good", clean], ["warn", review], ["bad", flagged]]) {
    if (count === 0) continue;
    const length = Math.max((count / total) * LENGTH, SHORTEST_ARC);
    svg.append(circle(`ring-arc ${arcTone}`, { "stroke-dasharray": `${length} ${LENGTH - length}`, "stroke-dashoffset": -start }));
    start += length;
  }
  const answered = clean + review + flagged;
  return h(
    "div",
    { class: `posture-ring ${tone}${settled ? " settled" : ""}` },
    svg,
    h("div", { class: "posture-centre" }, answered > 0 ? [h("strong", { text: `${Math.round((clean / total) * 100)}%` }), h("span", { text: "clean" })] : icon("shield", 34)),
  );
}
