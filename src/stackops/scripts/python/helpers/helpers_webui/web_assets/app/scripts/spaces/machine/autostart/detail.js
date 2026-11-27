import { h, icon, shellQuote } from "/assets/scripts/dom.js";
import { agentButton } from "../../../agent_ask.js";
import { openSheet } from "../../../overlays.js";
import { button, copyChip, glyphTile, keyValue, pathChip, pill } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { readDetail } from "./api.js";
import { COMMAND, KINDS, MANNERS, PROCESSES_COMMAND, SCOPES, lastEndText, lockText, stateWords, triggerLines, whenText, whoseWords } from "./words.js";

const chips = (paths) => h("div", { class: "autostart-chips" }, paths.map(pathChip));

// Everything about one entry, in a side sheet. What the list already knows shows at once; the rest of a launchd job (what it is given, where
// its output goes, how often it has run) is read when the sheet opens and filled in when it arrives.
export function openDetail({ activity, entry, platform, tools, handlers }) {
  const sheet = openSheet({ label: entry.title, wide: true });
  const kind = KINDS[entry.category];
  const status = stateWords(entry);
  const facts = h("div");
  const trouble = h("p", { class: "dim", hidden: true });
  const act = (run) => () => {
    sheet.close();
    run(entry);
  };

  const ask = agentButton(activity, {
    title: entry.title, commands: [COMMAND], about: "One of the things that start on their own on this computer, at start-up or at sign-in.",
    notes: [`The entry on screen is “${entry.title}”${entry.program ? `, which runs ${entry.program}` : ""}. It is ${entry.enabled ? "turned on" : "turned off"}.`],
    ideas: ["What is this, and is it safe to turn off?"],
  });

  function paintFacts(detail) {
    const since = entry.scope === "boot" ? "the computer started" : "you signed in";
    const processes = entry.pid && button({ label: "Show in Processes", glyph: "arrow", small: true, onclick: act(() => tools.open(PROCESSES_COMMAND, { preset: { pid: String(entry.pid) } })) });
    facts.replaceChildren(
      keyValue([
        [entry.kind === "login_item" || entry.kind === "sign_in" ? "Opens" : "Runs", entry.program && pathChip(entry.program)],
        ["Given", detail?.arguments.length > 0 && h("code", { class: "autostart-code", text: detail.arguments.map(shellQuote).join(" ") })],
        ["Belongs to", entry.owner],
        ["Starts", h("ul", { class: "autostart-starts" }, triggerLines(entry, detail ?? null).map((line) => h("li", { text: line })))],
        ["Right now", status && h("div", { class: "autostart-now" }, h("span", { text: status.text }), processes)],
        ["Last time", entry.live !== "running" && entry.state !== "trouble" && lastEndText(entry)],
        ["Started", detail?.runs > 0 && `${plural(detail.runs, "time")} since ${since}`],
        ["Defined in", entry.file ? pathChip(entry.file) : entry.kind === "login_item" && "The list of login items that macOS keeps. System Settings shows it under General, Login Items & Extensions."],
        ["Runs as", detail?.run_as],
        ["Starts in", detail?.working_directory && pathChip(detail.working_directory)],
        ["Writes to", detail?.output_files.length > 0 && chips(detail.output_files)],
        ["Watches", detail?.watched.length > 0 && chips(detail.watched)],
        ["Listed as", `${entry.source}, ${kind.long.toLowerCase()}`],
      ]),
    );
  }

  sheet.body.classList.add("autostart-sheet");
  sheet.body.append(
    h("header", { class: "autostart-sheet-head" }, glyphTile(kind.glyph, kind.hue, 52), h("div", {}, h("h2", { text: entry.title }), entry.name !== entry.title && copyChip(entry.name))),
    h(
      "div",
      { class: "autostart-sheet-pills" },
      status && pill(status.label, status.tone),
      pill(SCOPES[entry.scope].label),
      pill(MANNERS[entry.manner].label),
      pill(whoseWords(platform)[entry.whose].label, entry.whose === "yours" ? "accent" : ""),
    ),
    h("p", { class: "autostart-sheet-lede", text: (entry.kind === "listed" || entry.kind === "systemd") && entry.description ? entry.description : `${whenText(entry)}.` }),
    facts,
    trouble,
  );
  paintFacts(null);

  const changeable = entry.actions.includes("turn_off") || entry.actions.includes("turn_on");
  sheet.foot.hidden = false;
  if (changeable) {
    sheet.foot.append(
      ask,
      button({ label: entry.enabled ? "Turn off" : "Turn back on", glyph: "power", tone: entry.enabled ? "plain" : "primary", onclick: act((shown) => handlers.toggle(shown, platform)) }),
      h("span", { class: "spacer" }),
      ...(entry.actions.includes("remove") ? [button({ label: "Move to the Trash", glyph: "trash", tone: "ghost", title: "Stops it and puts its file in the Trash", onclick: act(handlers.remove) })] : []),
    );
  } else if (entry.actions.includes("remove")) {
    sheet.foot.append(ask, button({ label: "Stop opening it at sign-in", glyph: "close", onclick: act(handlers.remove) }));
  } else {
    sheet.foot.append(ask, h("p", { class: "autostart-locked" }, icon("lock", 15), h("span", { text: lockText(entry, platform) })));
  }

  if (entry.kind === "launchd") {
    readDetail(entry.id).then(paintFacts, (error) => {
      trouble.hidden = false;
      trouble.textContent = `The rest could not be read. ${error.message}`;
    });
  }
  return sheet;
}
