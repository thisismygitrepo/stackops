import { h, shellQuote } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";

export const EVERYWHERE = "all";
// The scripts kept in the StackOps repository, under the name the CLI gives their place.
export const ONLINE = "dynamic";
// The places a script can be in, as the server names them: the project's, one per member of a workspace (`workspace:<name>`), the user's, and the ones StackOps comes with.
const PLACES = { workspace: "This project", user: "Yours", library: "Built in", dynamic: "Online" };
export const PLACE_BLURBS = { workspace: "Kept with this project, for everyone who works in it.", user: "Your own, on hand in every project." };
// A file with no ending is run by the shell, as a `.sh` one is.
const KINDS = { ".py": ["Python", "PY", 215], ".sh": ["Shell", "SH", 150], "": ["Shell", "SH", 150], ".ps1": ["PowerShell", "PS", 262], ".bat": ["Batch file", "BAT", 32], ".cmd": ["Batch file", "CMD", 32] };
// The endings the CLI tries when a script is asked for by name alone, which is what it takes to be made for the system it runs on.
const WINDOWS_SUFFIXES = [".py", ".ps1", ".bat", ".cmd"];
const POSIX_SUFFIXES = [".py", ".sh", ""];

const onWindows = () => state.boot.platform === "Windows";
export const kindOf = (source) => source.split(":")[0];
export function placeLabel(source) {
  const [kind, member] = source.split(":");
  return member ? `${PLACES[kind]} · ${member}` : PLACES[kind];
}

export const keyOf = (script) => `${script.source}\n${script.name}`;
export const fileOf = (script) => script.name.split("/").at(-1);
export const folderOf = (script) => script.name.split("/").slice(0, -1).join("/");
export const kindLabel = (script) => KINDS[script.suffix][0];
export const runsHere = (script) => (onWindows() ? WINDOWS_SUFFIXES : POSIX_SUFFIXES).includes(script.suffix);
// Only the user's own scripts and a project's are edited or added to from here: the built-in ones belong to the installed StackOps.
export const canChange = (source) => ["workspace", "user"].includes(kindOf(source));
// The kinds a new script can be: the ones this system runs.
export const newKinds = () => (onWindows() ? [".py", ".ps1", ".bat"] : [".py", ".sh"]).map((suffix) => [suffix, KINDS[suffix][0]]);
export const haystackOf = (script) => `${script.name} ${script.summary} ${placeLabel(script.source)} ${kindLabel(script)}`.toLowerCase();

// The kind of script at a glance, in the kind's own colour.
export function scriptFace(script, size) {
  const [, letters, hue] = KINDS[script.suffix];
  return h("span", { class: "avatar script-face", style: `--hue:${hue};--size:${size}px`, text: letters });
}

// What the CLI is given to run exactly this script, with `extra` passed on to it. One on this machine is named by its file, so a script of the
// same name in another place is never run in its stead; one kept online is named by its place, which has the CLI fetch it first.
export const runArguments = (script, extra) => ["devops", "scripts", "run", ...(script.source === ONLINE ? ["--source", ONLINE, script.name] : [script.path]), ...extra];
// The same run as it is typed in a terminal.
export const commandLine = (script) => ["devops", "scripts", "run", "--source", kindOf(script.source), script.name].map(shellQuote).join(" ");
