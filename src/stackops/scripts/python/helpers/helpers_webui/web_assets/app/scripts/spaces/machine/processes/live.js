import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { iconButton } from "../../../widgets.js";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

// The shared icons have no pause mark, so this one is drawn here, to the same measure as theirs.
function pauseIcon() {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  for (const [name, value] of [["viewBox", "0 0 24 24"], ["width", "16"], ["height", "16"], ["aria-hidden", "true"], ["class", "icon"]]) svg.setAttribute(name, value);
  svg.innerHTML = '<path d="M9 5v14M15 5v14"/>';
  return svg;
}

// Whether the list is following the machine, when it was last read, and the ways to hold it still or read it now.
export function createLive({ onToggle, onRefresh }) {
  const word = h("strong");
  const stamp = h("span");
  const status = h("span", { class: "procs-live" }, h("i"), word, stamp);
  const label = h("span");
  const toggle = h("button", { class: "btn", type: "button", onclick: onToggle }, pauseIcon(), label);
  const refresh = iconButton("refresh", "Read the list again now", onRefresh);
  refresh.classList.add("procs-refresh");
  let pausedShown = null;

  function paint({ paused, failing, ended, readAt, loading }) {
    const state = ended ? "ended" : failing ? "failing" : paused ? "paused" : "live";
    status.dataset.state = state;
    word.textContent = { ended: "Stopped", failing: "Not updating", paused: "Paused", live: "Live" }[state];
    stamp.textContent = readAt ? `${state === "live" ? "updated" : "as of"} ${formatClock(readAt)}` : "";
    if (pausedShown !== paused) toggle.firstChild.replaceWith(paused ? icon("play", 16) : pauseIcon());
    pausedShown = paused;
    label.textContent = paused ? "Resume" : "Pause";
    toggle.title = paused ? "Follow the machine again" : "Hold the list still, so nothing moves while you read it";
    toggle.disabled = refresh.disabled = ended;
    refresh.classList.toggle("busy", loading);
  }

  return { elements: [status, toggle, refresh], paint };
}
