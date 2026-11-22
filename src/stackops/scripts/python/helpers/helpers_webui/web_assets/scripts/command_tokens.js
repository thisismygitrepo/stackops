import { splitArguments } from "./dom.js";

// Text parameters that take prose. The whole text is passed as one value and never split at spaces or quotes, so an apostrophe stays an apostrophe.
// Design choice: they are known by name. The ones that take several values (PROMPT on three `agents` commands) are joined with spaces by the CLI, so one value reads the same there.
export const LONG_TEXT_NAMES = new Set(["prompt", "message", "command", "context", "note"]);

export const longOf = (flags) => flags.find((flag) => flag.startsWith("--")) ?? flags[0];

function tokensOf(spec, value) {
  if (!value) return [];
  if (spec.control === "switch") return [value === "off" ? longOf(spec.off_flags) : longOf(spec.flags)];
  const items = !spec.multiple || LONG_TEXT_NAMES.has(spec.name) ? [value] : spec.control === "choice" ? value.split("\n") : splitArguments(value);
  return spec.kind === "option" ? items.flatMap((item) => [longOf(spec.flags), item]) : items;
}

// The one place form values become CLI arguments, for the developer view's form and the app view's.
// `values` maps a parameter's name to what its field holds, and `extra` is tokens the caller adds as they were typed.
// A problem is `{ spec, gap }`: `gap` is null when `spec` is required and empty, or else the earlier argument to fill in before `spec`. Each form words them itself.
export function collectTokens(specs, values, extra) {
  const optionTokens = [];
  const argumentTokens = [];
  const problems = [];
  let gap = null;
  for (const spec of specs) {
    const tokens = tokensOf(spec, values.get(spec.name) ?? "");
    if (spec.required && tokens.length === 0) problems.push({ spec, gap: null });
    if (spec.kind === "option") optionTokens.push(...tokens);
    else if (tokens.length === 0) gap ??= spec;
    else if (gap) problems.push({ spec, gap });
    else argumentTokens.push(...tokens);
  }
  // An argument that starts with a dash needs `--` in front of it, and whatever follows `--` is read as an argument. So `extra` goes ahead of `--` then,
  // where an option typed there still counts as one. Without `--` it stays last, which is where a tool that passes arguments on looks for them.
  // Not strictly correct: with `--`, a plain value typed as extra lands ahead of the form's arguments. Options are what gets typed there far more often.
  const dashed = argumentTokens.some((token) => token.startsWith("-"));
  return { tokens: [...optionTokens, ...(dashed ? [...extra, "--"] : []), ...argumentTokens, ...(dashed ? [] : extra)], problems };
}
