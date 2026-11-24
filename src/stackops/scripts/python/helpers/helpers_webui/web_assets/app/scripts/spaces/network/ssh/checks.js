import { h, icon } from "/assets/scripts/dom.js";
import { rise } from "../../../motion.js";
import { copyChip, pill } from "../../../widgets.js";
import { plural } from "../../../words.js";

// What `devops network ssh debug --json` found, drawn for the Network overview's panel and for the SSH page alike. Its suggestions, some of
// them `sudo` commands, are offered to copy and never run from here.
const CHECK_PILLS = { error: ["Problem", "bad"], unknown: ["Not confirmed", "warn"] };
const GROUPS = [["installation", "Installed"], ["service", "Switched on"], ["configuration", "Settings"], ["permissions", "Sign-in rights"], ["network", "Listening"], ["firewall", "Firewall"]];
const GROUP_MARKS = { ok: ["good", "check"], error: ["bad", "alert"], unknown: ["warn", "info"], none: ["", "info"] };

export const summaryText = (summary) =>
  summary.ready ? "ready for SSH connections" : [summary.error_count > 0 && plural(summary.error_count, "problem"), summary.unknown_count > 0 && `${summary.unknown_count} not confirmed`].filter(Boolean).join(" · ");

export const passedPills = (checks) => checks.filter((check) => check.status === "ok").map((check) => pill(check.label, "good"));

// The checks that did not pass, problems first, each with what the command advises.
export function openChecks(checks) {
  const open = checks.filter((check) => check.status !== "ok").sort((left, right) => (right.status === "error") - (left.status === "error"));
  if (open.length === 0) return null;
  return rise(
    h(
      "ul",
      { class: "session-list" },
      open.map((check) =>
        h(
          "li",
          { class: "session-row check-row" },
          h("div", { class: "session-text" }, h("strong", { text: check.label }), h("span", { text: check.message }), check.manual_advice.map((advice) => h("span", { class: "dim", text: advice })), check.command_suggestions.map((command) => copyChip(command))),
          pill(...CHECK_PILLS[check.status]),
        ),
      ),
    ),
  );
}

// The six things that have to hold for a connection to get in, in the order a connection meets them. A step is as bad as its worst check.
export function checkTrack(checks) {
  return h(
    "ol",
    { class: "network-ssh-track" },
    GROUPS.map(([group, label]) => {
      const mine = checks.filter((check) => check.group === group);
      const state = mine.some((check) => check.status === "error") ? "error" : mine.some((check) => check.status === "unknown") ? "unknown" : mine.length > 0 ? "ok" : "none";
      const [tone, glyph] = GROUP_MARKS[state];
      const passed = mine.filter((check) => check.status === "ok").length;
      return h("li", { class: tone, title: mine.map((check) => `${check.label}: ${check.message}`).join("\n") }, h("i", {}, icon(glyph, 15)), h("strong", { text: label }), h("span", { text: mine.length === 0 ? "Not checked here" : `${passed} of ${mine.length} confirmed` }));
    }),
  );
}

export function verdictOf({ summary, checks }) {
  if (summary.ready) return { tone: "good", glyph: "check", title: "This machine accepts SSH connections", body: `All ${plural(summary.total_checks, "check")} passed.` };
  if (summary.has_errors) return { tone: "bad", glyph: "alert", title: `${plural(summary.error_count, "problem")} in the way of SSH connections`, body: "What is wrong is listed below, with what to do about each." };
  const confirmed = checks.filter((check) => check.status === "ok").length;
  return {
    tone: "warn", glyph: "info", title: "SSH could not be confirmed",
    body: `${confirmed} of ${plural(summary.total_checks, "check")} passed. The rest could not be read without administrator rights, so this machine may or may not accept connections.`,
  };
}

// Whether SSH is switched on, as far as the checks can tell: "on", "off", or "unknown" when the one that says so could not be read.
export function serviceState(checks) {
  const service = checks.filter((check) => check.group === "service");
  if (service.some((check) => check.status === "error")) return "off";
  return service.length > 0 && service.every((check) => check.status === "ok") ? "on" : "unknown";
}
