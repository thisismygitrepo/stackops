import { formatClock, h, icon } from "/assets/scripts/dom.js";
import { button, iconButton, pathChip } from "../../../widgets.js";

// What a mount is doing, and afterwards whether it worked and where the device is now.
export function mountBanner(run, { onReveal, onDismiss }) {
  if (run.phase !== "done") {
    return h(
      "section",
      { class: "mount-banner working" },
      h("span", { class: "task-mark" }, h("i", { class: "ring" })),
      h("div", { class: "mount-banner-text" }, h("h2", { text: `Mounting ${run.name}…` }), h("p", { text: run.asks ? "It runs in the Activity panel. If it asks for a password, type it there." : "It runs in the Activity panel and takes a moment." })),
      button({ label: "Show progress", glyph: "terminal", small: true, onclick: onReveal }),
      iconButton("close", "Stop waiting for it", onDismiss),
    );
  }
  const mounted = run.result === "mounted";
  const stopped = run.result === "stopped";
  const title = mounted ? `${run.name} is mounted` : stopped ? `Mounting ${run.name} was stopped` : `${run.name} was not mounted`;
  const lines = mounted
    ? [run.place ? h("p", { class: "mount-banner-place" }, "It is at ", pathChip(run.place)) : h("p", { text: "The system chose the place. If the list does not show it yet, press Refresh." })]
    : stopped
      ? [h("p", { text: "It was stopped before it finished." })]
      : [h("p", { text: run.reason || "The Activity panel shows what went wrong." }), h("p", { text: "The choices are still here. Change them and try again." })];
  return h(
    "section",
    { class: `mount-banner ${mounted ? "good" : stopped ? "" : "warn"}` },
    h("span", { class: `task-mark ${mounted ? "done" : stopped ? "stopped" : "failed"}` }, icon(mounted ? "check" : stopped ? "stop" : "alert", 22)),
    h("div", { class: "mount-banner-text" }, h("h2", { text: title }), lines, h("small", { class: "dim", text: `Finished at ${formatClock(run.finishedAt)}` })),
    button({ label: "Show what happened", glyph: "terminal", small: true, onclick: onReveal }),
    iconButton("close", "Dismiss", onDismiss),
  );
}
