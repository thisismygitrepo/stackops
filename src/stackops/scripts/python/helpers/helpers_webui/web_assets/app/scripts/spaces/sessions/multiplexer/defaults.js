import { h, icon } from "/assets/scripts/dom.js";
import { avatar, button, pill } from "../../../widgets.js";
import { runningLine } from "./running.js";
import { ROLES, standingOf, wordsOf } from "./words.js";

// One of the two defaults as it stands: which multiplexer, whether the person chose it or StackOps fell back on it, what follows it, and what
// is in its way when it cannot be used. `item` is that multiplexer as the server describes it. `onKeep(role, name, control)` writes a
// built-in default down as the person's own choice. Returns the tile and `setRunning`, which the sessions default shows.
export function defaultTile({ role, chosen, item, platform, onKeep }) {
  const { title } = wordsOf(chosen.name);
  const words = ROLES[role];
  const standing = standingOf(item, platform);
  const issue = {
    unsupported: `${title} does not run on ${platform}, so ${words.stalled}. Pick another below.`,
    missing: `${title} is not installed, so ${words.stalled}. Install it or pick another below.`,
    problem: `${title} cannot be used as it is, so ${words.stalled}. Update it or pick another below.`,
  }[standing.id];
  const running = h("div", { class: "mux-state" }, runningLine());
  const keep = button({ label: "Keep it as my choice", small: true, tone: "ghost", title: "Saves it, so it stays the default even if the built-in one changes", onclick: () => onKeep(role, chosen.name, keep) });
  keep.classList.add("mux-pick");
  const element = h(
    "article",
    { class: `mux-default${issue ? " warn" : ""}` },
    h("span", { class: "overline", text: words.label }),
    h("div", { class: "mux-default-name" }, avatar(chosen.name, 46), h("strong", { text: title }), pill(chosen.chosen ? "Your choice" : "Built-in default", chosen.chosen ? "accent" : "")),
    h("p", { text: words.uses }),
    !chosen.chosen && h("p", { class: "mux-unpicked" }, h("span", { text: `You have not picked one, so StackOps uses ${title}.` }), !issue && keep),
    issue ? h("p", { class: "mux-issue" }, icon("alert", 15), h("span", { text: issue })) : role === "session" && running,
  );
  return { element, setRunning: (info) => running.replaceChildren(runningLine(info)) };
}
