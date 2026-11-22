import { h, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { query } from "../../data.js";
import { confirmAction, openDialog } from "../../overlays.js";
import { button } from "../../widgets.js";
import { plural } from "../../words.js";
import { SCAN_COMMAND, STATUS_QUERY } from "./words.js";

const WHAT_HAPPENS = "Each file's fingerprint is looked up on VirusTotal. A file it has never seen is uploaded there for analysis, and VirusTotal shares uploaded files with its security partners.";
const PACE = " Lookups are spaced out to stay within the account limits, so this takes a while.";
const KEY_ENTRY = "A scan needs a login named virusTotal in your secrets, with an account name and one secret holding API_KEY.";

// Every scan from this page starts behind a yes: it sends file fingerprints, and sometimes the files themselves, to VirusTotal.
// Not strictly complete: the scanner splits app names on commas, so an app with a comma in its name cannot be picked out here.
export function createScanStarter({ activity, tools }) {
  async function start(title, body, scanArguments) {
    const { accounts } = (await query(STATUS_QUERY)).json;
    if (accounts.problem) {
      const add = await confirmAction({ title: "Scans cannot run yet", body: `${accounts.problem} ${KEY_ENTRY}`, confirm: "Add a VirusTotal key" });
      if (add) addKey();
      return;
    }
    if (!(await confirmAction({ title: `${title}?`, body, confirm: "Start the scan" }))) return;
    await activity.start({ title, emoji: "🦠", arguments: [...SCAN_COMMAND, ...scanArguments], interactive: true, reveal: true });
  }
  const guarded = (...parameters) => start(...parameters).catch((error) => toast(error.message));

  const addKey = () => tools.open("devops vault add", { preset: { secrets_source: "user" }, title: "Add a VirusTotal key" });
  const apps = (names) => guarded(names.length === 1 ? `Scan ${names[0]}` : `Scan ${plural(names.length, "app")}`, `${WHAT_HAPPENS}${names.length > 4 ? PACE : ""}`, [names.join(",")]);
  const everything = () => guarded("Scan every installed app", `${WHAT_HAPPENS}${PACE}`, ["--all"]);
  const path = (file) => guarded(`Scan ${file.split(/[\\/]/).at(-1)}`, WHAT_HAPPENS, ["--path", file]);

  function file() {
    let chosen = "";
    const dialog = openDialog({ label: "Scan a file", size: "small" });
    const go = () => {
      const typed = chosen.trim().replace(/^~(?=\/|$)/, state.boot.home);
      if (!typed) return;
      dialog.close();
      path(typed);
    };
    const combo = createCombo({
      label: "File to scan", glyph: "folder", placeholder: "Type a file's path", emptyText: "No such file",
      suggest: async (text) => (await api.paths(text, state.settings.workingDirectory)).entries.map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
      onInput: (text) => (chosen = text),
      // Picking a folder keeps the list open on what is inside it; picking a file is the choice made.
      onPick: (option) => {
        chosen = option.value;
        if (!option.keepOpen) go();
      },
    });
    combo.input.addEventListener("keydown", (event) => event.key === "Enter" && !event.defaultPrevented && go());
    dialog.body.append(
      h("h2", { text: "Scan a file" }),
      h("p", { text: "Check any file on this machine, such as a download you are not sure about." }),
      combo.element,
      h("div", { class: "dialog-actions" }, button({ label: "Cancel", onclick: () => dialog.close() }), button({ label: "Scan this file", glyph: "shield", tone: "primary", onclick: go })),
    );
    combo.input.focus();
  }

  return { apps, everything, path, file, addKey, keyEntry: KEY_ENTRY };
}
