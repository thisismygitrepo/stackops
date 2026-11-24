import { h, icon } from "/assets/scripts/dom.js";
import { callout, pathChip } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { count } from "./words.js";

export const METHODS = [["copy", "Copy"], ["symlink", "Link"]];
export const METHOD_WORDS = {
  copy: "Two separate files. The one in your dotfiles folder changes only when you save from this machine. This is the default.",
  symlink: "One file under two names. The path here becomes a link to the copy in your dotfiles folder, so every edit lands there at once.",
};
// What to do when the file here and a kept copy both exist and differ, by the command's own words for it. The first is its default.
export const CONFLICTS = [
  { value: "throw-error", label: "Stop and change nothing", text: "" },
  { value: "overwrite-self-managed", label: "Keep the one here", text: "The one here replaces the kept copy." },
  { value: "backup-self-managed", label: "Keep the one here, set the kept copy aside", text: "The kept copy is renamed with .orig_ and a few letters at its end, then the one here takes its place." },
  { value: "overwrite-default-path", label: "Keep the kept copy", text: "The kept copy replaces the one here." },
  { value: "backup-default-path", label: "Keep the kept copy, set the one here aside", text: "The one here is renamed with .orig_ and a few letters at its end, then the kept copy takes its place." },
];
// What the command does, by where the two sides stand (`state` in the server's check) and by copy or link.
const HAPPENS = {
  collect: { copy: "It moves into your dotfiles folder, and a copy of it is put back where it was.", symlink: "It moves into your dotfiles folder, and a link to it takes its place." },
  collect_link: { copy: "This is a link. What it points to is copied into your dotfiles folder, and a copy of that replaces the link.", symlink: "This is a link. What it points to is copied into your dotfiles folder, and the link then points there." },
  restore: { copy: "Nothing is at this path, but a kept copy is in your dotfiles folder. It is copied to this path.", symlink: "Nothing is at this path, but a kept copy is in your dotfiles folder. A link to it is made at this path." },
  identical: { copy: "A kept copy with the same content is there already. Only the entry on your list is written.", symlink: "A kept copy with the same content is there already. The one here becomes a link to it." },
  relink: { copy: "This is a link to somewhere else, and a kept copy is there already. A copy of the kept one replaces the link.", symlink: "This is a link to somewhere else, and a kept copy is there already. The link then points to the kept one." },
  empty: { copy: "The link at this path points at nothing. It is removed, and an empty file is made here and in your dotfiles folder.", symlink: "The link at this path points at nothing. It is replaced by a link to a new, empty file in your dotfiles folder." },
};
// Where the command would stop, and why the button stays off.
export const STOPS = {
  missing: "Nothing is at this path, and no copy of it is kept either.",
  linked: "This already is a link to its kept copy, so there is nothing to move. The command stops on it.",
};

export function factsLine(facts, kept) {
  if (facts.kind === "missing") return { tone: kept.kind === "missing" ? "bad" : "", text: kept.kind === "missing" ? "Nothing is at this path." : "Nothing is at this path, but a kept copy of it is in your dotfiles folder." };
  if (facts.kind === "broken_link") return { tone: "warn", text: `A link that points at nothing (${facts.points_to}).` };
  const size = facts.kind === "folder" || (facts.kind === "link" && facts.files !== 1) ? `${facts.measured_whole ? count(facts.files, "file", "files") : `more than ${facts.files.toLocaleString()} files`}, ${formatBytes(facts.size_bytes)}${facts.measured_whole ? "" : " and more"}` : formatBytes(facts.size_bytes);
  const what = { file: "A file", folder: "A folder", link: `A link to ${facts.points_to}`, other: "Not a regular file" }[facts.kind];
  return { tone: "good", text: `${what} · ${size}` };
}

// Whether the file is looked after already, and anything else the person should know before adding it.
export function remarks(check) {
  return [
    check.list_problem && callout({ tone: "bad", title: "Your list of managed files cannot be read", text: check.list_problem }),
    ...check.listed.map((entry) =>
      callout({
        tone: entry.source === "user" ? "warn" : "", title: entry.source === "user" ? `Already on your list as ${entry.group} · ${entry.name}` : `StackOps looks after this one already, as ${entry.group} · ${entry.name}`,
        text: entry.source === "user" ? `It is ${entry.copy ? "copied" : "linked"}. Adding it again writes a second entry, or replaces that one when group and name are the same.` : "It comes with built-in settings. An entry of your own takes the place of the built-in one.",
      }),
    ),
    check.inside_store && callout({ tone: "warn", title: "This path is inside your dotfiles folder", text: "It is kept safe there already. Add the file where its program looks for it." }),
  ].filter(Boolean);
}

// What will happen, in a sentence, with where the file is and where it is kept, and the entry as the command will write it.
export function outcomeCard(check, { method, conflict }) {
  const chosen = CONFLICTS.find((option) => option.value === conflict);
  const sentence = STOPS[check.state] ?? (check.state === "conflict" ? chosen?.text || "What is here and the kept copy both exist and differ. Choose which one to keep." : HAPPENS[check.state][method]);
  const stops = Boolean(STOPS[check.state]) || (check.state === "conflict" && !chosen?.text);
  return h(
    "section",
    { class: `dotfiles-outcome${stops ? " stops" : ""}` },
    h("h3", { text: "What will happen" }),
    h("p", { text: sentence }),
    h("div", { class: "dotfiles-flow" }, pathChip(check.file.path), icon("arrow", 14), pathChip(check.kept.path)),
    !stops && h("div", { class: "dotfiles-entry" }, h("span", { class: "field-hint", text: check.replaces ? `Replaces the entry of that name, which is for ${check.replaces}. Written to` : "Added to your list at" }), pathChip(check.list_path), h("pre", { text: check.preview })),
  );
}
