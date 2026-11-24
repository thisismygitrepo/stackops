import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";

export const TOOL_PATH = "devops config terminal ghostty-theme";
export const TOOL_TOKENS = TOOL_PATH.split(" ");
export const TOOL_COMMAND = `stackops ${TOOL_PATH}`;
export const STATUS_ADDRESS = "/api/terminal/ghostty/status";
// Ghostty's name in the app catalog, and where to get it when the catalog has no installer for this system.
export const APP_NAME = "ghostty";
export const DOWNLOAD_ADDRESS = "https://ghostty.org/download";

// The keys Ghostty loads its settings again with, unless they were changed there, as key caps to put in a sentence.
export function reloadKeys() {
  const keys = state.boot.platform === "macOS" ? ["⌘", "⇧", ","] : ["Ctrl", "Shift", ","];
  return h("span", { class: "ghostty-theme-keys" }, keys.map((key) => h("kbd", { text: key })));
}

// A theme as the server reports it: the name for each appearance of the system. One name twice is a single theme, both empty is none.
export const isSingle = (theme) => theme.light === theme.dark && theme.light !== "";
export const isUnset = (theme) => theme.light === "" && theme.dark === "";
export const sameAs = (theme, name) => theme.light === name && theme.dark === name;

export function themeWords(theme) {
  if (isUnset(theme)) return "no theme";
  if (theme.light === theme.dark) return theme.light;
  return `${theme.light} in light mode and ${theme.dark} in dark mode`;
}
