import { h, icon, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { openSheet } from "../../overlays.js";
import { avatar, button, copyChip, keyValue, notice, pill, skeleton } from "../../widgets.js";
import { plural, relativeTime } from "../../words.js";
import { engineMeter, verdictPills } from "./app_rows.js";
import { SCANS_HASH, VIRUSTOTAL_FILE_ADDRESS } from "./words.js";

const SOURCES = { existing_report: "VirusTotal already knew this file", submitted_file: "Uploaded for analysis" };
const FLAG_TONES = { malicious: "bad", suspicious: "warn" };
const QUIET = ["harmless", "undetected"];
const EXPLAIN = {
  flagged: (target) => `${plural(target.flagged_engines, "engine")} of the ${target.verdict_engines} that gave a verdict flagged this file. That many is rarely a false alarm.`,
  review: (target) => `${plural(target.flagged_engines, "engine")} of the ${target.verdict_engines} that gave a verdict flagged this file. A lone flag is often a false alarm; what each one found is listed below.`,
  clean: (target) => `None of the ${plural(target.verdict_engines, "antivirus engine")} that gave a verdict flagged this file.`,
  no_verdict: () => "VirusTotal answered, but no engine gave a verdict on this file.",
  failed: (target) => target.notes || "The check did not finish.",
  pending: () => "The scan has not reached this file yet.",
  not_scanned: () => "The scan ended before it reached this file.",
  unchecked: () => "This app has not been checked yet.",
};

const when = (value) => value && h("span", { title: new Date(value).toLocaleString(), text: relativeTime(value) });

function engineBlocks(engines) {
  const flags = engines.filter((engine) => FLAG_TONES[engine.engine_category]);
  const quiet = engines.filter((engine) => QUIET.includes(engine.engine_category));
  const silent = engines.filter((engine) => !FLAG_TONES[engine.engine_category] && !QUIET.includes(engine.engine_category));
  const fold = (title, members, label) =>
    members.length > 0 && h("details", { class: "fold" }, h("summary", {}, icon("chevron", 13), h("span", { text: title }), h("b", { text: String(members.length) })), h("div", { class: "chip-row" }, members.map((engine) => pill(label(engine)))));
  return [
    flags.length > 0 &&
      h(
        "ul",
        { class: "engine-flags" },
        flags.map((engine) => h("li", {}, h("strong", { text: engine.engine_name }), h("code", { text: engine.engine_result ?? "no name given" }), pill(engine.engine_category, FLAG_TONES[engine.engine_category]))),
      ),
    fold("Found nothing", quiet, (engine) => engine.engine_name),
    fold("Gave no answer", silent, (engine) => `${engine.engine_name} · ${engine.engine_category}`),
  ];
}

// One checked file, opened over the list: the verdict in words, where the answer came from, and what every engine said.
// `loadEngines` is called only when there are engine results to show.
export function openTargetSheet({ target, loadEngines, onScan }) {
  const sheet = openSheet({ label: target.name });
  const engines = h("div", { class: "stack" });
  sheet.body.append(
    h("header", { class: "app-detail-head scan-sheet-head" }, avatar(target.name, 64), h("div", {}, h("h1", { text: target.name }), h("p", {}, copyChip(target.path, tildify(target.path, state.boot.home))))),
    h(
      "div",
      { class: "verdict-card" },
      h("div", { class: "project-facts" }, verdictPills(target), engineMeter(target)),
      h("p", { text: EXPLAIN[target.verdict](target) }),
      target.changed_since && h("p", { class: "verdict-caution", text: "The file was written after this check, so the answer is about an earlier version of it. Scan it again." }),
    ),
    keyValue([
      ["Version", target.version],
      ["Checked", when(target.checked_at)],
      ["Analysed by VirusTotal", when(target.analyzed_at)],
      ["Answer came from", SOURCES[target.source]],
      ["Fingerprint", target.sha256 && copyChip(target.sha256, `${target.sha256.slice(0, 16)}…`)],
      ["Scan", target.run_id && h("a", { class: "link", href: `${SCANS_HASH}/${target.run_id}`, text: "Open the scan it was part of" })],
      ["Notes", target.verdict !== "failed" && target.notes],
      ["Uploaded copy", target.app_url && h("a", { class: "link", href: target.app_url, target: "_blank", rel: "noopener noreferrer", text: "Open in cloud storage" })],
    ]),
    engines,
  );
  if (target.total_engines > 0) {
    engines.replaceChildren(...skeleton(3, "row"));
    loadEngines().then(
      (found) => sheet.body.isConnected && engines.replaceChildren(...engineBlocks(found).filter(Boolean)),
      (error) => engines.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The engine results didn't load", body: error.message })),
    );
  }
  sheet.foot.hidden = false;
  sheet.foot.append(
    ...[
      target.sha256 && h("a", { class: "btn plain", href: `${VIRUSTOTAL_FILE_ADDRESS}${target.sha256}`, target: "_blank", rel: "noopener noreferrer", title: "Opens this file's page on virustotal.com" }, icon("external", 16), h("span", { text: "Open on VirusTotal" })),
      h("span", { class: "spacer" }),
      onScan &&
        button({
          label: target.checked_at ? "Scan again" : "Scan now", glyph: "shield", tone: "primary",
          onclick: () => {
            sheet.close();
            onScan(target);
          },
        }),
    ].filter(Boolean),
  );
}
