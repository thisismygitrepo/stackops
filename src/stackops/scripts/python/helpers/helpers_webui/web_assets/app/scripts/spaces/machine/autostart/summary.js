import { h, icon } from "/assets/scripts/dom.js";
import { countUp } from "../../../motion.js";
import { FACETS, inUniverse, tally } from "./model.js";
import { KINDS, MANNERS, SCOPES, STATES, systemName, whoseWords } from "./words.js";

const card = (title, ...content) => h("section", { class: "autostart-card" }, h("span", { class: "overline", text: title }), ...content);
const amount = (count) => count.toLocaleString();

// A name, a count and a bar measured against the largest count beside it. A click narrows the list to it.
function meterRow({ label, hint, lead, onclick }) {
  const count = h("b", { class: "num" });
  const fill = h("i");
  const note = h("em");
  const element = h("button", { class: "autostart-meter", type: "button", title: hint, "aria-pressed": "false", onclick }, lead, h("span", { class: "autostart-meter-name" }, label, note), count, h("span", { class: "autostart-track" }, fill));
  return {
    element,
    set({ total, largest, pressed, aside = "" }) {
      element.hidden = total === 0;
      count.textContent = amount(total);
      note.textContent = aside;
      fill.style.setProperty("--share", String(Math.min(1, total / Math.max(largest, 1))));
      element.setAttribute("aria-pressed", String(pressed));
      element.classList.toggle("aside", aside !== "");
    },
  };
}

// One moment, and what starts then as one bar split by how it starts. The two bars share a scale, so their lengths compare.
function lane(scope, { toggle, pickCell }) {
  const total = h("b", { class: "num" });
  const head = h("button", { class: "autostart-lane-head", type: "button", "aria-pressed": "false", title: `Show only what is started ${SCOPES[scope].moment}`, onclick: () => toggle("scopes", scope) }, icon(SCOPES[scope].glyph, 15), h("span", { text: SCOPES[scope].label }), total);
  const segments = Object.keys(MANNERS).map((manner) => {
    const figure = h("span", { class: "num" });
    const element = h("button", { class: "autostart-segment", type: "button", "data-slot": String(MANNERS[manner].slot), "aria-pressed": "false", onclick: () => pickCell(scope, manner) }, h("i"), figure);
    return { manner, element, figure };
  });
  const bar = h("div", { class: "autostart-lane-bar" }, segments.map((segment) => segment.element));
  const none = h("p", { class: "autostart-lane-none dim", text: "Nothing" });
  return {
    element: h("div", { class: "autostart-lane" }, head, bar, none),
    paint(entries, largest, picks) {
      const mine = entries.filter((entry) => entry.scope === scope);
      const counts = tally(mine, FACETS.manners);
      const narrowed = picks.scopes.size > 0 || picks.manners.size > 0;
      total.textContent = amount(mine.length);
      head.setAttribute("aria-pressed", String(picks.scopes.has(scope)));
      bar.hidden = mine.length === 0;
      none.hidden = mine.length > 0;
      bar.style.setProperty("--share", String(mine.length / Math.max(largest, 1)));
      for (const { manner, element, figure } of segments) {
        const count = counts.get(manner) ?? 0;
        const included = (picks.scopes.size === 0 || picks.scopes.has(scope)) && (picks.manners.size === 0 || picks.manners.has(manner));
        element.hidden = count === 0;
        element.style.setProperty("--part", String(count));
        element.title = `${MANNERS[manner].label}: ${amount(count)}. ${MANNERS[manner].hint}`;
        element.setAttribute("aria-label", `${SCOPES[scope].label}, ${MANNERS[manner].lower}: ${amount(count)}`);
        element.setAttribute("aria-pressed", String(narrowed && included));
        element.classList.toggle("dimmed", narrowed && !included);
        figure.textContent = amount(count);
      }
    },
  };
}

// The top of the page: how much starts on its own and what it is doing now, when it starts, whose it is and what kind of thing it is.
// Every count is a way to narrow the list. The counts are of the whole list, with or without the standard parts of the system, and do
// not move when the list is narrowed. Everything is made once and filled in again, so what is clicked is never swapped for a copy.
export function createSummary({ view, toggle, pickCell, setSystem }) {
  const figure = h("strong", { class: "autostart-figure", text: "—" });
  const systemLink = h("button", { class: "link autostart-system-link", type: "button", onclick: () => setSystem(!view.system) });
  const facts = Object.keys(STATES).map((id) => {
    const text = h("span");
    const element = h("button", { class: "autostart-fact", type: "button", "data-tone": STATES[id].tone, "aria-pressed": "false", onclick: () => toggle("states", id) }, icon(STATES[id].glyph, 14), text, icon("arrow", 13));
    return { id, element, text };
  });
  const lanes = Object.keys(SCOPES).map((scope) => ({ scope, ...lane(scope, { toggle, pickCell }) }));
  const legend = Object.keys(MANNERS).map((manner) => {
    const count = h("b", { class: "num" });
    const element = h("button", { class: "autostart-key", type: "button", "data-slot": String(MANNERS[manner].slot), title: MANNERS[manner].hint, "aria-pressed": "false", onclick: () => toggle("manners", manner) }, h("i"), h("span", { text: MANNERS[manner].label }), count);
    return { manner, element, count };
  });
  const whoseRows = new Map();
  const whoseList = h("div", { class: "autostart-meters" });
  const kindRows = Object.keys(KINDS).map((id) => ({
    id,
    ...meterRow({ label: KINDS[id].label, hint: KINDS[id].long, lead: h("span", { class: "autostart-kind-mark", style: `--hue:${KINDS[id].hue}` }, icon(KINDS[id].glyph, 13)), onclick: () => toggle("kinds", id) }),
  }));
  const element = h(
    "div",
    { class: "autostart-cards" },
    card("In all", h("div", { class: "autostart-headline" }, figure, h("span", { text: "start on their own" })), h("div", { class: "autostart-facts" }, facts.map((fact) => fact.element)), systemLink),
    card("When they start", lanes.map((item) => item.element), h("div", { class: "autostart-legend" }, legend.map((item) => item.element))),
    card("Whose they are", whoseList),
    card("What kind", h("div", { class: "autostart-meters" }, kindRows.map((row) => row.element))),
  );

  function paint(model) {
    const entries = inUniverse(model, view);
    const { picks } = view;
    const standard = model.entries.filter((entry) => entry.stock).length;
    countUp(figure, entries.filter((entry) => entry.enabled).length);
    systemLink.hidden = standard === 0;
    systemLink.textContent = `${view.system ? "Hide" : "Show"} the ${amount(standard)} standard parts of ${systemName(model.platform)}`;
    const states = tally(entries, FACETS.states);
    for (const fact of facts) {
      const count = states.get(fact.id) ?? 0;
      fact.element.hidden = count === 0 && !picks.states.has(fact.id);
      fact.text.textContent = `${amount(count)} ${STATES[fact.id].label.toLowerCase()}`;
      fact.element.setAttribute("aria-pressed", String(picks.states.has(fact.id)));
    }
    const largestLane = Math.max(...lanes.map(({ scope }) => entries.filter((entry) => entry.scope === scope).length));
    for (const item of lanes) item.paint(entries, largestLane, picks);
    const manners = tally(entries, FACETS.manners);
    for (const item of legend) {
      item.count.textContent = amount(manners.get(item.manner) ?? 0);
      item.element.hidden = !manners.has(item.manner) && !picks.manners.has(item.manner);
      item.element.setAttribute("aria-pressed", String(picks.manners.has(item.manner)));
    }
    // The system's own row stays in view while they are left out of the list: it says how many there are, and a click brings them in.
    const words = whoseWords(model.platform);
    const whose = tally(view.system ? entries : model.entries, FACETS.whose);
    for (const id of Object.keys(words)) {
      if (!whoseRows.has(id)) {
        const row = meterRow({ label: words[id].label, hint: words[id].hint, lead: null, onclick: () => (id === "system" && !view.system ? setSystem(true, "system") : toggle("whose", id)) });
        whoseRows.set(id, row);
        whoseList.append(row.element);
      }
      const leftOut = id === "system" && !view.system;
      whoseRows.get(id).set({ total: whose.get(id) ?? 0, largest: Math.max(...Object.keys(words).filter((other) => view.system || other !== "system").map((other) => whose.get(other) ?? 0)), pressed: picks.whose.has(id), aside: leftOut ? "not shown" : "" });
    }
    const kinds = tally(entries, FACETS.kinds);
    for (const row of kindRows) row.set({ total: kinds.get(row.id) ?? 0, largest: Math.max(...kinds.values(), 1), pressed: picks.kinds.has(row.id) });
  }

  return { element, paint };
}
