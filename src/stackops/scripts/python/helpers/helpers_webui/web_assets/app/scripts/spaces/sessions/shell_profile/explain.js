import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { copyChip, glyphTile, pathChip, sectionHead } from "../../../widgets.js";
import { SHELLS, shortPath } from "./words.js";

const item = (glyph, hue, title, text, ...chips) => h("li", { class: "shellprof-does" }, glyphTile(glyph, hue, 38), h("div", {}, h("strong", { text: title }), h("p", { text }), chips.flat().filter(Boolean)));

// What a setup run does to this machine, in the order the person cares about: the profile, the two folders, and the terminals that are open.
// It is written for the shell the run acts on, with that shell's own files and line, and says where something is already in place.
export function explainSection(shell, folders) {
  const { name } = SHELLS[shell.id];
  const [settings, scripts] = ["settings", "scripts"].map((folder) => folders.find((candidate) => candidate.name === folder));
  const missing = shell.files.filter((file) => !file.line_present);
  const profiles = shell.files.map((file) => shortPath(file.path)).join(" and ");
  const several = shell.files.length > 1;
  return h(
    "section",
    { class: "block" },
    sectionHead(`What setting up ${name} does`),
    h(
      "ul",
      { class: "shellprof-does-list" },
      missing.length === 0
        ? item("check", 150, `Leaves ${profiles} alone`, several ? "Both files already have their line, so neither is touched." : "The line is already in it, so the file is not touched.", shell.files.map((file) => copyChip(file.line)))
        : item(
            "pencil", 252, `Adds one line to ${missing.map((file) => shortPath(file.path)).join(" and ")}`,
            `The line goes at the end of the file${missing.some((file) => !file.exists) ? ", which is created first if it is not there" : ""}. Your own lines stay as they are.`,
            missing.map((file) => copyChip(file.line)),
          ),
      item(
        "sliders", 200, settings.exists ? "Replaces StackOps' settings folder" : "Puts StackOps' settings in place",
        settings.exists ? "A fresh copy of the settings StackOps ships takes the place of the whole folder. Anything you changed inside it is lost." : "The settings StackOps ships are copied here. The setup file the line loads is one of them.",
        pathChip(settings.path),
      ),
      item(
        "code", 165, scripts.exists ? "Copies StackOps' scripts afresh" : "Puts StackOps' scripts in place",
        `The scripts the setup file calls are copied here${state.boot.platform === "Windows" ? "" : " and made runnable"}. A script of the same name is overwritten, and the rest of the folder stays.`,
        pathChip(scripts.path),
      ),
      item(
        "refresh", 30, "Leaves open terminals as they are",
        `A terminal reads its profile when it starts, so one that is already open carries on as before. Open a new one${shell.reload_command ? ", or run this in the open one." : "."}`,
        shell.reload_command && copyChip(shell.reload_command),
      ),
    ),
  );
}
