const SVG_NAMESPACE = "http://www.w3.org/2000/svg";
const WIDTH = 132;
const HEIGHT = 34;
const INSET = 4;

function shape(tag, className) {
  const node = document.createElementNS(SVG_NAMESPACE, tag);
  node.setAttribute("class", className);
  return node;
}

// A small line of the last readings of one share, 0 to 100, newest at the right edge. It is a picture of the figure beside it and carries
// no numbers of its own, so its description says what the line did in words.
export function createTrend({ label, limit }) {
  const svg = shape("svg", "procs-trend");
  svg.setAttribute("viewBox", `0 0 ${WIDTH} ${HEIGHT}`);
  svg.setAttribute("role", "img");
  const area = shape("path", "procs-trend-area");
  const line = shape("path", "procs-trend-line");
  const dot = shape("circle", "procs-trend-dot");
  dot.setAttribute("r", "3");
  svg.append(area, line, dot);

  function paint(values) {
    svg.style.visibility = values.length < 2 ? "hidden" : "visible";
    if (values.length < 2) return;
    const step = (WIDTH - INSET * 2) / (limit - 1);
    const points = values.map((value, index) => [WIDTH - INSET - (values.length - 1 - index) * step, HEIGHT - INSET - (Math.min(value, 100) / 100) * (HEIGHT - INSET * 2)]);
    const path = points.map(([x, y], index) => `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
    line.setAttribute("d", path);
    area.setAttribute("d", `${path} L${points.at(-1)[0].toFixed(1)} ${HEIGHT} L${points[0][0].toFixed(1)} ${HEIGHT} Z`);
    dot.setAttribute("cx", points.at(-1)[0].toFixed(1));
    dot.setAttribute("cy", points.at(-1)[1].toFixed(1));
    svg.setAttribute("aria-label", `${label}: between ${Math.round(Math.min(...values))}% and ${Math.round(Math.max(...values))}% over the last ${values.length} readings, now ${Math.round(values.at(-1))}%.`);
  }

  return { element: svg, paint };
}
