import { h } from "/assets/scripts/dom.js";

// Text that is plain but usually loosely structured: a saved prompt, a file an agent reads, what an agent was told and what it answered.
// The `prompt-` class names are from its first use, on the Prompts tab; their rules are in agents_prompts.css.
const WORDS_PER_MINUTE = 220;
const SNIPPET_RADIUS = 46;
const FENCE = /^\s*(```|~~~)/;
const RULE = /^\s*([-=*_])\1{2,}\s*$/;
const HEADING = /^\s*(#{1,6})\s+(.+?)\s*#*\s*$/;
const ITEM = /^(\s*)([-*•+]|\d{1,3}[.)])\s+(.*)$/;
const LABEL = /^[^\n]{1,64}:$/;
const INLINE = /(`[^`\n]+`|\*\*[^*\n]+\*\*)/;

// The two ways such a text is shown, as the choices of a `segmented` picker.
export const TEXT_VIEWS = [["formatted", "Easy to read"], ["plain", "As written"]];

export function readingStats(text) {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return { words, minutes: Math.max(1, Math.round(words / WORDS_PER_MINUTE)) };
}

export function markAll(text, term) {
  if (!term) return [text];
  const lower = text.toLowerCase();
  const needle = term.toLowerCase();
  const parts = [];
  let from = 0;
  for (let at = lower.indexOf(needle); at >= 0; at = lower.indexOf(needle, from)) {
    if (at > from) parts.push(text.slice(from, at));
    parts.push(h("mark", { text: text.slice(at, at + needle.length) }));
    from = at + needle.length;
  }
  if (from < text.length) parts.push(text.slice(from));
  return parts;
}

export function snippetAround(text, term) {
  const at = text.toLowerCase().indexOf(term.toLowerCase());
  if (at < 0) return null;
  const start = Math.max(0, at - SNIPPET_RADIUS);
  const end = Math.min(text.length, at + term.length + SNIPPET_RADIUS);
  return `${start > 0 ? "…" : ""}${text.slice(start, end).replace(/\s+/g, " ").trim()}${end < text.length ? "…" : ""}`;
}

// The structure looked for: underlined or #-marked headings, bullets, and fenced examples.
function parseLooseText(text) {
  const lines = text.replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  const flush = () => {
    if (paragraph.length) blocks.push({ kind: "text", text: paragraph.join("\n") });
    paragraph = [];
  };
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const heading = line.match(HEADING);
    const item = line.match(ITEM);
    if (FENCE.test(line)) {
      flush();
      const body = [];
      for (index += 1; index < lines.length && !FENCE.test(lines[index]); index += 1) body.push(lines[index]);
      blocks.push({ kind: "code", text: body.join("\n") });
    } else if (line.trim() === "") {
      flush();
    } else if (heading) {
      flush();
      blocks.push({ kind: "heading", level: heading[1].length, text: heading[2] });
    } else if (RULE.test(line)) {
      if (paragraph.length === 1 && /^[-=]/.test(line.trim())) {
        blocks.push({ kind: "heading", level: line.trim()[0] === "=" ? 1 : 2, text: paragraph[0].trim().replace(/:$/, "") });
        paragraph = [];
      } else {
        flush();
        blocks.push({ kind: "rule" });
      }
    } else if (item) {
      flush();
      blocks.push({ kind: "item", depth: Math.floor(item[1].replace(/\t/g, "  ").length / 2), marker: /\d/.test(item[2]) ? item[2] : "", text: item[3] });
    } else if (paragraph.length === 0 && blocks.at(-1)?.kind === "item" && /^\s+\S/.test(line)) {
      blocks.at(-1).text += `\n${line.trim()}`;
    } else {
      paragraph.push(line);
    }
  }
  flush();
  return blocks;
}

function inline(text, term) {
  return text.split(INLINE).filter(Boolean).flatMap((piece) => {
    if (piece.length > 2 && piece.startsWith("`") && piece.endsWith("`")) return [h("code", {}, markAll(piece.slice(1, -1), term))];
    if (piece.length > 4 && piece.startsWith("**") && piece.endsWith("**")) return [h("strong", {}, markAll(piece.slice(2, -2), term))];
    return markAll(piece, term);
  });
}

export function renderLooseText(text, term) {
  return h(
    "div",
    { class: "prompt-prose" },
    parseLooseText(text).map((block) => {
      if (block.kind === "code") return h("pre", { class: "prompt-code" }, markAll(block.text, term));
      if (block.kind === "rule") return h("hr");
      if (block.kind === "heading") return h(block.level <= 2 ? "h3" : "h4", {}, inline(block.text, term));
      if (block.kind === "item") return h("div", { class: `prompt-item${block.marker ? " numbered" : ""}`, style: `--depth:${Math.min(block.depth, 4)}` }, h("span", { class: "prompt-marker", text: block.marker }), h("p", {}, inline(block.text, term)));
      return h("p", { class: LABEL.test(block.text.trim()) ? "prompt-label" : "" }, inline(block.text, term));
    }),
  );
}
