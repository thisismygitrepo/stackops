import { h } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { plural } from "./words.js";

export const CLEANUP_HASH = "#/machine/cleanup";
export const CLEANUP_TOOL = ["utils", "machine", "clean-drive"];

export const CATEGORIES = {
  dev: { title: "Developer caches", blurb: "Downloads that package managers and build tools keep to work faster.", glyph: "code", hue: 252 },
  projects: { title: "Project folders", blurb: "Dependencies, environments and build output found inside your projects.", glyph: "folder", hue: 200 },
  stackops: { title: "StackOps leftovers", blurb: "Scratch files, logs, staging copies and search indexes StackOps left behind.", glyph: "layers", hue: 290 },
  containers: { title: "Docker", blurb: "Containers, images, volumes and build layers that nothing is using.", glyph: "cube", hue: 165 },
  system: { title: "System", blurb: "Temporary files, logs and downloads the system keeps around.", glyph: "cpu", hue: 30 },
  trash: { title: "Trash", blurb: "Files you already threw away.", glyph: "trash", hue: 340 },
};
export const CATEGORY_ORDER = Object.keys(CATEGORIES);
export const categoryOf = (id) => CATEGORIES[id] ?? { title: id.charAt(0).toUpperCase() + id.slice(1), blurb: "", glyph: "cube", hue: 220 };

export const RISKS = {
  safe: { label: "Safe", tone: "good", rank: 0, hint: "Comes back by itself the next time it is needed." },
  caution: { label: "Check first", tone: "warn", rank: 1, hint: "You may have to reinstall or rebuild something, or it is gone for good. Read what you lose first." },
  danger: { label: "Risky", tone: "bad", rank: 2, hint: "Can destroy data you still need. It cannot be recovered." },
};
export const RISK_ORDER = Object.keys(RISKS);

const UNITS = ["bytes", "kB", "MB", "GB", "TB"];
const QUALIFIERS = { exact: "", at_least: "at least", at_most: "up to", approximate: "about" };
const QUALIFIER_NOTES = {
  at_least: "Some folders could not be read, so it is probably more.",
  at_most: "This is the size of the whole store; only the unused part is removed.",
  approximate: "Reported by the tool itself, so treat it as a rough figure.",
};
// Notes name the command a target is cleaned with ("Runs `uv cache clean`."); that belongs in the details, not in the sentence people read.
const CLEANER_LEAD = /^(?:Runs?|BleachBit) `[^`]*`[\s,;:.]*/;
// Some notes describe each system in turn ("On macOS, …"); only the sentence about this machine's system is shown.
const SYSTEM_LEAD = /^on ((?:Linux|Windows|macOS)(?:(?:,| and| or) (?:Linux|Windows|macOS))*)[:,]\s*/i;

// Decimal units, like the cleanup's own console output and the file manager. `like` fixes the unit, so a number counting up does not hop between units.
export function sizeText(bytes, like = bytes) {
  let scale = 1;
  let unit = 0;
  while (like / scale >= 1000 && unit < UNITS.length - 1) {
    scale *= 1000;
    unit += 1;
  }
  const amount = bytes / scale;
  return unit === 0 ? `${Math.round(amount)} bytes` : `${amount >= 100 ? Math.round(amount) : amount.toFixed(1)} ${UNITS[unit]}`;
}

export const qualifierOf = (target) => QUALIFIERS[target.estimateKind] ?? "";
export const qualifierNoteOf = (target) => QUALIFIER_NOTES[target.estimateKind] ?? "";
export const estimateText = (target) => [qualifierOf(target), sizeText(target.bytes)].filter(Boolean).join(" ");

export function plainNote(note) {
  const kept = [];
  let dropped = false;
  for (const part of note.split(/(?<=[.;])\s+/)) {
    const cleaned = part.replace(CLEANER_LEAD, "");
    const system = cleaned.match(SYSTEM_LEAD);
    const rest = system ? (system[1].includes(state.boot.platform) ? cleaned.slice(system[0].length) : "") : cleaned;
    if (rest === "") {
      dropped = true;
      continue;
    }
    kept.push(dropped || rest !== part ? rest.charAt(0).toUpperCase() + rest.slice(1) : rest);
    dropped = false;
  }
  return kept.join(" ");
}

export const firstSentence = (note) => plainNote(note).split(/(?<=\.)\s+(?=[A-Z~$_.])/)[0];
export const codeNodes = (text) => text.split("`").map((piece, index) => (index % 2 ? h("code", { text: piece }) : piece));

export function actionText(target) {
  if (target.commands.length) return ["Uses the tool's own cleanup: ", ...target.commands.flatMap((command, index) => [index > 0 && ", then ", h("code", { text: command.join(" ") })])];
  const count = target.paths.length;
  if (target.action_kind === "projects") return [`Deletes ${plural(count, "folder")} found in your projects.`];
  return [`Deletes ${plural(count, "item")} from this machine.`];
}

export const adminHow = (platform) => (platform === "Windows" ? "That only works when StackOps was started from an administrator window; otherwise that part is skipped." : "The console asks for your password when it gets there.");
export const adminText = (platform) => `Needs administrator rights. ${adminHow(platform)}`;

export function quietReason(target) {
  if (target.phase === "error") return { label: "Could not be measured", detail: target.problem };
  if (target.status === "missing_tool") return { label: `${target.message.split(" not found")[0]} is not installed`, detail: "" };
  if (target.status === "failed") return { label: "Could not be measured", detail: target.message.split(" failed: ").at(-1) };
  return { label: "Already clean", detail: "" };
}

export const clockText = (seconds) => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
