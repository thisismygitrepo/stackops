import { tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";

export const PAGE_HASH = "#/sessions/shell-profile";
export const TOOL_PATH = "devops config terminal config-shell";
export const STATE_ADDRESS = "/api/terminal/shell-profile/state";

// Each shell's name, the sign its prompt ends in, a colour, and the catalog app that installs it where there is one.
export const SHELLS = {
  zsh: { name: "zsh", sign: "%", hue: 252 },
  bash: { name: "bash", sign: "$", hue: 150 },
  nushell: { name: "Nushell", sign: ">", hue: 172, app: "nu" },
  pwsh: { name: "PowerShell", sign: "PS", hue: 210 },
};

export const shortPath = (path) => tildify(path, state.boot.home);
export const fileName = (path) => path.split(/[\\/]/).at(-1);
const onWindows = () => state.boot.platform === "Windows";
// Windows has no login shell; there the command's default choice is PowerShell.
export const loginLabel = () => (onWindows() ? "Default shell" : "Login shell");

// Where a shell stands, from what the server read. A shell with two profile files (Nushell) is set up when both have their line.
export function standingOf(shell) {
  if (shell.blocker) return shell.blocker;
  if (shell.files.some((file) => file.problem)) return "unreadable";
  const lines = shell.files.filter((file) => file.line_present).length;
  if (lines === shell.files.length) return !shell.setup_in_place ? "broken" : shell.setup_current ? "ready" : "behind";
  if (lines > 0) return "partial";
  if (shell.files.some((file) => file.old_line_present)) return "old";
  return shell.files.some((file) => file.exists) ? "absent" : "unstarted";
}

// The label and colour of each standing, and whether a setup run is what moves it on.
export const STANDINGS = {
  ready: { label: "Set up", tone: "good", due: false },
  behind: { label: "Setup file differs", tone: "warn", due: true },
  broken: { label: "Broken", tone: "bad", due: true },
  partial: { label: "Half set up", tone: "warn", due: true },
  old: { label: "Old line", tone: "warn", due: true },
  absent: { label: "Not set up", tone: "", due: true },
  unstarted: { label: "Not set up", tone: "", due: true },
  unreadable: { label: "Can't be read", tone: "bad", due: false },
  not_installed: { label: "Not installed", tone: "", due: false },
  other_system: { label: "Not on this system", tone: "", due: false },
};

// A shell's profile files as a sentence names them: the path of a single file, and the bare names of two that share a folder.
export const profileNames = (shell) => shell.files.map((file) => (shell.files.length > 1 ? fileName(file.path) : shortPath(file.path)));

export function standingText(shell, standing) {
  const { name } = SHELLS[shell.id];
  const names = profileNames(shell);
  const many = names.length > 1;
  const profile = names.join(" and ");
  // A shell the command does not act on is not told what setting it up would do; the note under its name says what to do instead.
  const sentences = {
    ready: `Every new ${name} terminal loads StackOps' setup.`,
    behind: `It works, but ${many ? "the setup files in place are not the ones" : "the setup file in place is not the one"} this version of StackOps ships. A setup run replaces ${many ? "them" : "it"}.`,
    broken: many
      ? `${profile} have their lines, but the files they load are missing, so every new ${name} terminal prints an error. A setup run puts them back.`
      : `${profile} has the line, but the file it loads is missing, so every new ${name} terminal prints an error. A setup run puts the file back.`,
    partial: "One of its two files has the line and the other does not. Setting up adds the missing one.",
    old: `${profile} still loads the setup file of an older StackOps, which is gone. A setup run swaps that line for the current one.`,
    absent: `${profile} ${many ? "have" : "has"} no StackOps line, so ${name} terminals open without what StackOps adds.`,
    unstarted: many
      ? `Neither ${names.join(" nor ")} exists yet. Setting up creates them.`
      : shell.route === "manual"
        ? `There is no ${profile} yet, so ${name} terminals open without what StackOps adds.`
        : `There is no ${profile} yet. Setting up creates it.`,
    unreadable: shell.files.filter((file) => file.problem).map((file) => `${shortPath(file.path)} could not be read. ${file.problem}`).join(" "),
    not_installed: `${name} is not installed on this computer.`,
    other_system: shell.id === "pwsh" ? "StackOps sets up PowerShell on Windows only." : "StackOps sets up zsh and bash on macOS and Linux only.",
  };
  return sentences[standing];
}

// Why a shell that is not the login shell has no Set up button, and what to do instead.
export function manualText(shell, login) {
  const file = shortPath(shell.files[0].path);
  const where = login ? `Set up acts on the shell you sign in with, which is ${SHELLS[login.id].name}.` : "Set up acts on the shell you sign in with.";
  const how = shell.files[0].line_present ? `The line in ${file} was put there by hand.` : `To use it in ${SHELLS[shell.id].name} as well, paste the line into ${file} yourself.`;
  const files = shell.setup_in_place ? "" : login ? ` The file it loads arrives once ${SHELLS[login.id].name} is set up.` : " The file it loads is not on this computer yet.";
  return `${where} ${how}${files}`;
}

// What each part of the setup does, by the key the server gives it. A part the page has no words for is left out.
export const EXTRAS = {
  prompt: { glyph: "sparkle", hue: 252, title: "A prompt that says more", text: "Starship draws the line you type on. It shows the folder you are in and, inside a project, its git branch." },
  jump: { glyph: "arrow", hue: 200, title: "Jump to a folder", text: "Type z and part of a folder's name to go to a folder you have been in before." },
  history: { glyph: "clock", hue: 30, title: "Search what you typed before", text: "Ctrl+R opens a search through your command history." },
  browse: { glyph: "folder", hue: 165, title: "Browse folders", text: "Type y to walk through your folders in yazi. When you leave it, the terminal is in the folder you ended on." },
  listing: { glyph: "menu", hue: 290, title: "A fuller file list", text: "Type l to list a folder with sizes, dates and hidden files." },
  path: { glyph: "terminal", hue: 330, title: "StackOps' programs by name", text: "The apps StackOps installs and its own scripts run from any folder, without typing where they are." },
};

export const listOf = (names) => (names.length < 3 ? names.join(" or ") : `${names.slice(0, -1).join(", ")} or ${names.at(-1)}`);
