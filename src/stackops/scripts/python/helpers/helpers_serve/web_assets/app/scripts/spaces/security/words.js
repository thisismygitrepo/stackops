import { formatDuration } from "/assets/scripts/dom.js";
import { plural, relativeTime } from "../../words.js";

export const SCANS_HASH = "#/security/scans";
export const SCAN_COMMAND = ["devops", "security", "scan"];
export const STATUS_QUERY = ["devops", "security", "status", "--json"];
export const VIRUSTOTAL_FILE_ADDRESS = "https://www.virustotal.com/gui/file/";

// What each verdict of the scanner is called on the page, and its colour.
export const VERDICTS = {
  flagged: ["Flagged", "bad"], review: ["Worth a look", "warn"], no_verdict: ["No verdict", "warn"], failed: ["Check failed", "bad"], pending: ["Waiting", ""],
  not_scanned: ["Not reached", ""], unchecked: ["Never checked", ""], clean: ["Clean", "good"],
};

// The order a list settles into: what needs attention first.
export const GROUPS = [
  ["flagged", "Flagged"], ["review", "Worth a look"], ["changed", "Changed since their check"], ["unknown", "Could not be checked"], ["waiting", "Still waiting"],
  ["skipped", "Not reached before the scan ended"], ["unchecked", "Never checked"], ["clean", "Clean"],
];
const GROUP_OF = { failed: "unknown", no_verdict: "unknown", pending: "waiting", not_scanned: "skipped" };

// A flag outranks a changed file; a changed file outranks any other answer, because that answer is about an earlier file.
export const groupOf = (target) => (target.verdict === "flagged" || target.verdict === "review" ? target.verdict : target.changed_since ? "changed" : (GROUP_OF[target.verdict] ?? target.verdict));
export const needsScan = (target) => ["changed", "unknown", "unchecked"].includes(groupOf(target));

export const RUN_STATES = {
  completed: ["Completed", "good"], completed_with_errors: ["Completed with problems", "warn"], failed: ["Failed", "bad"], interrupted: ["Interrupted", "warn"],
  empty: ["Nothing matched", ""], running: ["Unfinished", "accent"],
};

export function scopeTitle(run) {
  if (run.scope === "all") return "Every installed app";
  if (run.scope === "path") return run.requested[0]?.split(/[\\/]/).at(-1) ?? "One file";
  return run.requested.length <= 3 ? run.requested.join(", ") : `${run.requested.slice(0, 3).join(", ")} and ${run.requested.length - 3} more`;
}

export function runTiming(run) {
  const took = run.finished_at && formatDuration((Date.parse(run.finished_at) - Date.parse(run.started_at)) / 1000);
  return [`Started ${relativeTime(run.started_at)}`, took && `took ${took}`].filter(Boolean).join(" · ");
}

export function countsLine(counts) {
  const flagged = (counts.flagged ?? 0) + (counts.review ?? 0);
  const unknown = (counts.failed ?? 0) + (counts.no_verdict ?? 0);
  const left = (counts.pending ?? 0) + (counts.not_scanned ?? 0);
  return [counts.clean && `${counts.clean} clean`, flagged && `${flagged} flagged`, unknown && `${unknown} not checked`, left && `${left} not reached`].filter(Boolean).join(" · ") || "nothing to check";
}

export const enginesLine = (target) =>
  target.verdict_engines > 0 ? `${target.flagged_engines} of ${plural(target.verdict_engines, "engine")}` : target.verdict === "no_verdict" ? "no engine gave a verdict" : "";
