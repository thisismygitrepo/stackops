import { lineage } from "/assets/scripts/state.js";
import { TOOL_TITLES, WORDS } from "./catalog.js";

export function humanize(name) {
  const words = name.replace(/^-+/, "").split(/[-_\s]+/).filter(Boolean).map((word) => WORDS[word.toLowerCase()] ?? word.toLowerCase());
  const text = words.join(" ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function plainText(text) {
  return text.replace(/^[^\p{L}\p{N}"'(]+/u, "").trim();
}

export function friendlyText(text) {
  const clauses = plainText(text).split(/(?<=;)\s+|(?<=\.)\s+(?=[A-Z(])/);
  const kept = clauses.filter((clause) => !/(^|[\s(`'"])--?([a-zA-Z]|\s)/.test(clause) && !/usage:/i.test(clause));
  const stripped = clauses[0].replace(/\s+(?:(?:for|with|via|using|use|pass|requires?|see)\s+)?[`'"]?--?[a-zA-Z][\w-]*[`'"]?/g, "").replace(/\s{2,}/g, " ");
  const chosen = kept.length ? kept.join(" ") : stripped;
  const cleaned = chosen.replace(/[;,]\s*$/, "").trim();
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export const titleOf = (node) => TOOL_TITLES[node.path] ?? humanize(node.name);
export function fullTitleOf(node) {
  const parent = lineage(node).at(-2);
  return TOOL_TITLES[node.path] || !parent ? titleOf(node) : `${titleOf(node)} · ${titleOf(parent)}`;
}
export const trailOf = (node) => lineage(node).slice(0, -1).map(titleOf).join(" › ");
export const plural = (count, word) => `${count.toLocaleString()} ${word}${count === 1 ? "" : "s"}`;

export function hueOf(name) {
  let hash = 0;
  for (const character of name) hash = (hash * 31 + character.codePointAt(0)) % 360;
  return hash;
}

export function initialsOf(name) {
  const parts = name.split(/[-_.\s]+/).filter(Boolean);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}

export function relativeTime(value) {
  const then = typeof value === "number" ? value * 1000 : Date.parse(value);
  if (Number.isNaN(then)) return "";
  const seconds = Math.round((Date.now() - then) / 1000);
  const steps = [[60, "second"], [60, "minute"], [24, "hour"], [30, "day"], [12, "month"], [Infinity, "year"]];
  let amount = Math.abs(seconds);
  for (const [size, unit] of steps) {
    if (amount < size) return amount < 5 && unit === "second" ? "just now" : `${plural(Math.floor(amount), unit)} ${seconds >= 0 ? "ago" : "from now"}`;
    amount /= size;
  }
  return "";
}

export function formatBytes(bytes) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let amount = bytes;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return `${amount >= 10 || unit === 0 ? Math.round(amount) : amount.toFixed(1)} ${units[unit]}`;
}

export function greeting() {
  const hour = new Date().getHours();
  return hour < 5 ? "Still up" : hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";
}
