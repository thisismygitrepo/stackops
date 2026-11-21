import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { rise } from "../../motion.js";
import { avatar, button, copyChip, pill } from "../../widgets.js";
import { relativeTime } from "../../words.js";
import { enginesLine, GROUPS, groupOf, VERDICTS } from "./words.js";

// The groups that are folded to their first few rows until asked for: the ones nobody has to act on.
const FOLDED = { clean: 6 };

// How the engines answered, as one bar: flags first, then the ones that found nothing, then the ones that gave no answer.
export function engineMeter(target) {
  if (target.total_engines === 0) return null;
  const quiet = target.harmless_engines + target.undetected_engines;
  const silent = target.total_engines - target.verdict_engines;
  const parts = [["m-bad", target.malicious_engines], ["m-warn", target.suspicious_engines], ["m-good", quiet], ["m-none", silent]];
  return h(
    "span",
    { class: "meter engine-meter", title: `${target.malicious_engines} malicious · ${target.suspicious_engines} suspicious · ${quiet} found nothing · ${silent} gave no answer` },
    parts.filter(([, count]) => count > 0).map(([tone, count]) => h("i", { class: tone, style: `--share:${count / target.total_engines}` })),
  );
}

export function verdictPills(target) {
  const [label, tone] = VERDICTS[target.verdict];
  return [pill(label, tone), target.changed_since && h("span", { class: "pill warn", title: "The file was written after this check, so the result is about an earlier version.", text: "Changed since" })];
}

function targetRow(target, { onOpen, onScan }) {
  const detail = target.verdict === "failed" ? target.notes : enginesLine(target);
  const row = h(
    "li",
    { class: "session-row scan-row opens", tabindex: "0", title: "See what each engine said" },
    avatar(target.name, 40),
    h("div", { class: "session-text" }, h("strong", {}, target.name, target.version && h("span", { class: "version", text: target.version })), copyChip(target.path, tildify(target.path, state.boot.home))),
    h("div", { class: "scan-verdict" }, verdictPills(target), engineMeter(target), detail && h("span", { class: "dim scan-detail", title: detail, text: detail })),
    h("span", { class: "dim scan-when", title: target.checked_at && new Date(target.checked_at).toLocaleString(), text: target.checked_at ? `Checked ${relativeTime(target.checked_at)}` : "" }),
    h("div", { class: "scan-actions" }, onScan && button({ label: target.checked_at ? "Scan again" : "Scan", glyph: "shield", small: true, onclick: () => onScan(target) }), h("span", { class: "scan-go" }, icon("chevron", 14))),
  );
  row.addEventListener("click", (event) => !event.target.closest("button") && onOpen(target));
  row.addEventListener("keydown", (event) => event.key === "Enter" && event.target === row && onOpen(target));
  return row;
}

// Targets under the group each belongs to, worst first. `groupAction(id, members)` may return a button for the group's heading;
// `settled` skips the entrance animation, for a list that is refreshed in place.
export function targetGroups(targets, { onOpen, onScan, groupAction, settled = false, unfolded = false }) {
  return GROUPS.map(([id, title]) => [id, title, targets.filter((target) => groupOf(target) === id)])
    .filter(([, , members]) => members.length > 0)
    .map(([id, title, members]) => {
      const cap = unfolded ? members.length : (FOLDED[id] ?? members.length);
      const list = h("ul", { class: "session-list" }, members.slice(0, cap).map((target) => targetRow(target, { onOpen, onScan })));
      const more =
        members.length > cap &&
        button({
          label: `Show the other ${members.length - cap}`, glyph: "down", small: true, tone: "ghost",
          onclick: () => {
            list.append(...members.slice(cap).map((target) => targetRow(target, { onOpen, onScan })));
            more.remove();
          },
        });
      return h("section", { class: "scan-group" }, h("h3", {}, title, h("b", { text: String(members.length) }), h("span", { class: "spacer" }), groupAction?.(id, members)), settled ? list : rise(list), more);
    });
}
