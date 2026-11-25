import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { backLink } from "../../../space_kit.js";
import { button, iconButton } from "../../../widgets.js";
import { TOOL_PATH } from "./words.js";

const SVG_NAMESPACE = "http://www.w3.org/2000/svg";

// The shared icons have no pause mark, so this one is drawn here, to the same measure as theirs.
function pauseIcon() {
  const svg = document.createElementNS(SVG_NAMESPACE, "svg");
  for (const [name, value] of [["viewBox", "0 0 24 24"], ["width", "16"], ["height", "16"], ["aria-hidden", "true"], ["class", "icon"]]) svg.setAttribute(name, value);
  svg.innerHTML = '<path d="M9 5v14M15 5v14"/>';
  return svg;
}

// The top of the page: the way back, what the page is, and beside it whether the list is following the machine, when it was last read,
// the ways to hold it still or read it now, and the command's own form for every option the page does not offer.
export function createHead({ tools, onToggle, onRefresh }) {
  const word = h("strong");
  const stamp = h("span");
  const status = h("span", { class: "procs-live" }, h("i"), word, stamp);
  const label = h("span");
  const toggle = h("button", { class: "btn", type: "button", onclick: onToggle }, pauseIcon(), label);
  const refresh = iconButton("refresh", "Read the list again now", onRefresh);
  refresh.classList.add("procs-refresh");
  const element = h(
    "header",
    { class: "view-head" },
    h("div", { class: "view-title" }, backLink("#/machine", "Machine"), h("h1", { text: "Processes" }), h("p", { text: "Everything running on this machine, read again every few seconds. Find what is slowing it down and stop it." })),
    h("div", { class: "view-actions" }, status, toggle, refresh, button({ label: "All options", glyph: "sliders", title: "The plain form, with every option of the command behind this page", onclick: () => tools.open(TOOL_PATH, { plain: true }) })),
  );
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

  return { element, paint };
}
