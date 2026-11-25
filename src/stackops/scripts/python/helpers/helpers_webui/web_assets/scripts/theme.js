// Light or dark, for both views. The stylesheets say what dark looks like in plain `@media (prefers-color-scheme: dark)` blocks, which follow the system.
// A choice made with the button overrides the system by rewriting those conditions in place. No stylesheet has to know about the button, and one written
// later the usual way follows it too. This file imports nothing: both pages load it first, on its own, so the choice is in place before anything is drawn.
const THEME_KEY = "stackops-webui-theme";
const SCHEME_CONDITION = /\(\s*prefers-color-scheme\s*:\s*(light|dark)\s*\)/g;
// What a scheme condition is replaced with: one that always holds, or one that never does. The rest of a longer condition stays as it was written.
const ALWAYS = "(min-width: 0px)";
const NEVER = "(max-width: 0px)";

const systemDark = matchMedia("(prefers-color-scheme: dark)");
const systemTheme = () => (systemDark.matches ? "dark" : "light");
const writtenConditions = new WeakMap();
const listeners = new Set();

function chosenTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  return stored === "light" || stored === "dark" ? stored : null;
}

export const currentTheme = () => chosenTheme() ?? systemTheme();

function applyToRules(rules, chosen) {
  for (const rule of rules) {
    if (rule instanceof CSSMediaRule) {
      const written = writtenConditions.get(rule) ?? rule.media.mediaText;
      if (written.includes("prefers-color-scheme")) {
        writtenConditions.set(rule, written);
        const wanted = chosen ? written.replace(SCHEME_CONDITION, (_, scheme) => (scheme === chosen ? ALWAYS : NEVER)) : written;
        if (rule.media.mediaText !== wanted) rule.media.mediaText = wanted;
      }
    }
    if (rule.cssRules) applyToRules(rule.cssRules, chosen);
  }
}

function apply() {
  const chosen = chosenTheme();
  for (const sheet of document.styleSheets) {
    try {
      applyToRules(sheet.cssRules, chosen);
    } catch {
      // A stylesheet that is still loading has no rules to read yet. It is handled when it has loaded, by the listener below.
    }
  }
  // The browser's own parts (scrollbars, form controls) take their look from this property; left empty, the stylesheet's `light dark` follows the system.
  document.documentElement.style.colorScheme = chosen ?? "";
}

function refresh() {
  apply();
  for (const listener of listeners) listener(currentTheme());
}

// For what is drawn by a script and not by a stylesheet (a chart's colours, the button's own icon).
export function onThemeChange(listener) {
  listeners.add(listener);
}

export function toggleTheme() {
  const next = currentTheme() === "dark" ? "light" : "dark";
  // Choosing the look the system asks for anyway goes back to following the system, so one that changes with the time of day is followed again.
  if (next === systemTheme()) localStorage.removeItem(THEME_KEY);
  else localStorage.setItem(THEME_KEY, next);
  refresh();
}

systemDark.addEventListener("change", refresh);
// Another tab of this address changed the choice.
window.addEventListener("storage", (event) => event.key === THEME_KEY && refresh());
// A stylesheet fetched later (the terminal's, on first use). Load events do not bubble, so they are caught on the way down.
document.addEventListener("load", (event) => event.target instanceof HTMLLinkElement && apply(), true);
apply();
