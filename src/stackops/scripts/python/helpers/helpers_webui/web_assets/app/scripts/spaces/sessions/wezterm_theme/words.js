import { tildify } from "/assets/scripts/dom.js";
import { state as app } from "/assets/scripts/state.js";
import { plural } from "../../../words.js";

export const TOOL_PATH = "devops config terminal wezterm-theme";
export const PICKER_COMMAND = `stackops ${TOOL_PATH}`;

export const fileName = (path) => path.split(/[\\/]/).at(-1);

// Why a theme cannot be saved on this machine, short enough for a button's hint. Empty when it can.
export function obstacle(now) {
  return {
    ready: "",
    missing: "WezTerm has no settings file to save a theme in.",
    unreadable: "The settings file could not be read.",
    no_line: "The settings file has no line that sets the colour scheme.",
    line_off: "The line that sets the colour scheme is switched off in the settings file.",
  }[now.file];
}

// What the settings file says about the theme in use: the answer, and a remark to go beside it.
export function inUse(now) {
  if (now.file === "unreadable") return { text: "Not known", note: "" };
  if (now.file !== "ready") return { text: "None set", note: "WezTerm uses its own colours." };
  if (now.current === null) return { text: `Chosen by code in ${fileName(now.path)}`, note: "" };
  return { text: now.current, note: now.names.includes(now.current) ? "" : "Not one of the themes listed here." };
}

// What a new theme writes over that this tool cannot bring back: lines that choose the scheme with code, or a name outside its list.
// Empty when the theme in use is one of the listed names, which one more click restores.
export function loss(now) {
  if (now.file !== "ready") return "";
  const file = fileName(now.path);
  if (now.current === null) {
    return `${file} sets the colour scheme with code of its own, in ${plural(now.places, "line")}. A theme from here is written over ${now.places === 1 ? "that line" : "each of those lines"} as one fixed name. To get the code back you would type it in again.`;
  }
  if (now.names.includes(now.current)) return "";
  return `WezTerm uses "${now.current}" now, and this tool cannot set that one. To go back to it you would type its name into ${file} yourself.`;
}

// What stands in the way, each with its way forward. `actions` holds what the buttons do: `install`, `setUp` and `edit(line)`.
export function remarks(now, actions) {
  const file = fileName(now.path);
  return [
    !now.installed && {
      tone: "warn", title: "WezTerm is not installed on this machine", text: "A theme picked by name is still saved, and shows once WezTerm is installed.",
      action: { label: "Install WezTerm", glyph: "download", onclick: actions.install },
    },
    now.file === "missing" && {
      tone: "warn", title: "WezTerm has no settings file yet",
      text: "Themes are kept in the settings file named above, and it does not exist yet. StackOps comes with WezTerm settings of its own, and applying them puts the file there.",
      action: { label: "Set up WezTerm's settings", glyph: "sliders", onclick: actions.setUp },
    },
    now.file === "no_line" && {
      tone: "warn", title: `${file} does not set a colour scheme`, snippet: "config.color_scheme = 'Pro'",
      text: "A theme is written into the line that begins with config.color_scheme, and this file has none, so no theme can be saved. Add the line below above the last line of the file, save it, and open this again.",
      action: { label: `Open ${file}`, glyph: "terminal", onclick: () => actions.edit(null) },
    },
    now.file === "line_off" && {
      tone: "warn", title: "The colour scheme line is switched off",
      text: `Line ${now.line} of ${file} sets the colour scheme, but it begins with two dashes, so WezTerm skips it and no theme can be saved. Remove the dashes, save the file, and open this again.`,
      action: { label: `Open ${file} at line ${now.line}`, glyph: "terminal", onclick: () => actions.edit(now.line) },
    },
    now.file === "unreadable" && { tone: "bad", title: `${file} could not be read`, text: now.detail },
    now.shadow !== "" && {
      tone: "warn", title: "WezTerm reads another settings file first",
      text: `${tildify(now.shadow, app.boot.home)} exists, and WezTerm reads it before the file a theme is saved in. A theme picked here shows only once that file is gone.`,
    },
  ].filter(Boolean);
}
