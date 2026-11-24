import { h } from "/assets/scripts/dom.js";
import { button, copyChip, glyphTile, notice, pill, skeleton } from "../../widgets.js";
import { formatBytes, plural } from "../../words.js";
import { readCloud, readCloudReach } from "./tools_api.js";
import { CLOUD_PROBLEMS, cloudKind } from "./tools_words.js";

// The way forward for a machine with no cloud to upload to: a tool to open, a page to go to, or a command to run in a terminal.
function problemNotice(cloud, { tools, sheet }) {
  const problem = CLOUD_PROBLEMS[cloud.problem];
  const action = problem.tool
    ? button({ label: problem.action, glyph: "sliders", tone: "primary", onclick: () => (sheet.close(), tools.open(problem.tool)) })
    : problem.hash
      ? h("a", { class: "btn primary", href: problem.hash }, h("span", { text: problem.action }))
      : problem.command && h("div", { class: "sec-cloud-command" }, h("span", { text: "Run this in a terminal" }), copyChip(problem.command));
  return notice({ glyph: "plug", title: problem.title, body: cloud.detail ? `${problem.body} ${cloud.detail}` : problem.body, action });
}

// The cloud an upload goes to, as a card: its name and the service behind it at once, then whether it answers and how full it is, which is
// asked over the network and filled in when it arrives. A machine with no cloud set up gets the reason and the way to set one up in its place.
// `onState` hears what this machine has, and null for a reading that failed.
export function createCloudCard({ tools, sheet, onState }) {
  const element = h("div", { class: "sec-cloud" }, skeleton(1, "row"));
  let shown = true;
  sheet.closed.then(() => (shown = false));

  async function reach(mark, space) {
    try {
      const found = await readCloudReach();
      if (!shown) return;
      mark.replaceChildren(found.reachable ? pill("Answering", "good") : pill("Not answering", "bad"));
      if (!found.reachable) return space.replaceChildren(h("span", { class: "sec-cloud-detail bad", text: found.detail || "It gave no reason." }));
      if (found.total === null || found.free === null) return space.replaceChildren(h("span", { class: "sec-cloud-detail", text: "This service does not say how full it is." }));
      const used = found.used ?? found.total - found.free;
      space.replaceChildren(
        h("span", { class: "sec-meter", title: `${formatBytes(used)} used` }, h("i", { class: used / found.total > 0.9 ? "full" : "go", style: `--share:${Math.min(used / found.total, 1)}` })),
        h("span", { class: "sec-cloud-detail", text: `${formatBytes(found.free)} free of ${formatBytes(found.total)}` }),
      );
    } catch (error) {
      if (!shown) return;
      mark.replaceChildren(pill("Not checked", "warn"));
      space.replaceChildren(h("span", { class: "sec-cloud-detail bad", text: error.message }));
    }
  }

  async function load() {
    element.replaceChildren(...skeleton(1, "row"));
    let cloud;
    try {
      cloud = await readCloud();
    } catch (error) {
      if (!shown) return;
      element.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The cloud settings didn't load", body: error.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: load }) }));
      return onState(null);
    }
    if (!shown) return;
    onState(cloud);
    if (cloud.problem) return element.replaceChildren(problemNotice(cloud, { tools, sheet }));
    const mark = h("span", { class: "sec-cloud-mark" }, pill("Checking", "accent"));
    const space = h("div", { class: "sec-cloud-space" });
    element.replaceChildren(
      h(
        "div",
        { class: "sec-cloud-card" },
        glyphTile("globe", 200, 40),
        h("div", { class: "sec-cloud-text" }, h("strong", { text: cloud.name }), h("span", { text: [cloudKind(cloud.kind), cloud.remotes > 1 && `the one chosen out of ${plural(cloud.remotes, "cloud account")}`].filter(Boolean).join(", ") }), space),
        mark,
      ),
    );
    reach(mark, space);
  }

  load();
  return { element };
}
