import { h } from "/assets/scripts/dom.js";
import { button, callout, pathChip, segmented } from "../../widgets.js";
import { formatBytes, plural, relativeTime } from "../../words.js";
import { APPS_ADDRESS, KEY_NAMES, headlineOf, stepsOf } from "./bitwarden_words.js";
import { mark } from "./tools_kit.js";

// How Bitwarden stands on this machine, and the three things to do about it. Each button is live only when its command can work, and says
// why when it cannot. `actions` are the page's: unlock(account), sync(), clear(), addKey(), showKey(), install().
export function createStatus({ actions }) {
  const headline = h("div", { class: "vault-bw-headline" });
  const steps = h("ol", { class: "vault-bw-steps" });
  const notes = h("div", { class: "vault-bw-notes" });
  const cache = h("section", { class: "vault-bw-cache" });
  const element = h("div", { class: "vault-bw-status" }, h("section", { class: "vault-bw-hero" }, headline, steps, notes), cache);
  // The account whose API key Unlock uses, when the vault holds more than one.
  let account = null;

  function actionButton({ label, glyph, tone, busy, working, blocked, onclick }) {
    const control = button({ label: working ? `${label}…` : label, glyph, tone, title: blocked || "", onclick });
    control.disabled = Boolean(blocked) || busy !== "";
    control.classList.toggle("vault-tools-busy", working);
    return control;
  }

  // Which of the vault's API keys Unlock would use, and what stands in its way. A vault with several needs one named, as the command does.
  function keyOf(state) {
    const sets = state.key_sets;
    if (state.key_problem) return { blocked: state.key_problem, note: callout({ tone: "warn", title: "The API key cannot be read", text: state.key_problem, extra: h("a", { class: "btn small", href: "#/vault/file" }, h("span", { text: "See what is wrong with the vault file" })) }) };
    if (sets.length === 0) {
      return {
        blocked: "Add your Bitwarden API key to the vault first.",
        note: callout({
          tone: "", title: "Unlock needs your Bitwarden API key in the vault",
          text: `It reads a login called ${state.login_name} with three values: ${KEY_NAMES.join(", ")}, the last being your master password. Bitwarden's web vault shows the key under Settings, Security, Keys.`,
          extra: button({ label: "Add the API key", glyph: "plus", small: true, onclick: actions.addKey }),
        }),
      };
    }
    const named = sets.filter((set) => set.account);
    if (sets.length > 1 && !named.some((set) => set.account === account)) account = named.find((set) => set.current)?.account ?? null;
    const chosen = sets.length === 1 ? sets[0] : (named.find((set) => set.account === account) ?? null);
    const picker = segmented(named.map((set) => [set.account, set.current ? `${set.account} · signed in` : set.account]), (value) => {
      account = value;
      actions.repaint();
    });
    picker.set(account);
    const chooser = sets.length > 1 && h(
      "div",
      { class: "vault-bw-accounts" },
      h("span", { class: "dim", text: "Unlock with the key of" }),
      picker.element,
      named.length < sets.length && h("span", { class: "dim", text: `${plural(sets.length - named.length, "key")} without an account name cannot be chosen here.` }),
    );
    if (chosen?.gap) return { blocked: chosen.gap, chosen, note: h("div", {}, chooser, callout({ tone: "warn", title: "This API key cannot be used", text: chosen.gap, extra: button({ label: "Show the login", small: true, onclick: actions.showKey }) })) };
    return { blocked: chosen ? "" : "Choose which account's key to unlock with.", chosen, note: chooser || null };
  }

  function paintCache(place, state, busy) {
    const holds = !place.cache_exists
      ? "Nothing is saved yet. Unlocking saves the session here, and a search saves what it found."
      : !state
        ? "It holds the session that keeps Bitwarden unlocked for StackOps, and what earlier searches found."
        : !state.cache_opened
          ? "This machine's GPG key could not open it, so the session in it cannot be used. Clearing it and unlocking again starts afresh."
          : `It holds ${state.session_saved ? "the session that keeps Bitwarden unlocked for StackOps" : "no session"} and ${state.saved_searches === 0 ? "no saved searches" : `what ${plural(state.saved_searches, "search")} found, the list below among them`}. It is encrypted with this machine's GPG key.`;
    cache.replaceChildren(
      h("div", { class: "vault-bw-cache-text" }, h("h3", { text: "Saved on this machine" }), h("p", { text: holds }), place.cache_exists && h("div", { class: "vault-bw-cache-facts" }, h("strong", { text: formatBytes(place.cache_bytes) }), h("span", { class: "dim", text: `changed ${relativeTime(place.cache_modified)}` }), pathChip(place.cache_path))),
      actionButton({ label: place.cache_exists ? `Clear the cache · ${formatBytes(place.cache_bytes)}` : "Clear the cache", glyph: "trash", busy, working: busy === "clear", blocked: place.cache_exists ? "" : "There is nothing saved to clear.", onclick: actions.clear }),
    );
  }

  return {
    element,
    // The account handed over by whoever opened the page, for a vault that holds several keys.
    choose: (given) => (account = given),
    paint({ place, state, busy, failure }) {
      const { tone, title, body } = headlineOf(place, state);
      const key = state && place.installed ? keyOf(state) : { blocked: "", note: null, chosen: null };
      const unlocked = state?.status === "unlocked";
      const switching = unlocked && key.chosen && !key.chosen.current && state.key_sets.length > 1;
      const controls = !place.installed
        ? [button({ label: "Install it from Apps", glyph: "download", tone: "primary", title: "Opens Bitwarden's command-line program in Apps, where one click installs it", onclick: actions.install })]
        : [
            actionButton({
              label: switching ? "Switch account" : "Unlock", glyph: "key", tone: unlocked && !switching ? "plain" : "primary", busy, working: busy === "unlock",
              blocked: !state ? "Still asking Bitwarden how it stands." : unlocked && !switching ? "Bitwarden is already unlocked." : key.blocked,
              onclick: () => actions.unlock(state.key_sets.length > 1 ? account : null),
            }),
            actionButton({
              label: "Sync", glyph: "sync", tone: unlocked && !switching ? "primary" : "plain", busy, working: busy === "sync",
              blocked: !state ? "Still asking Bitwarden how it stands." : unlocked ? "" : "Unlock Bitwarden first. A sync needs the vault open.",
              onclick: actions.sync,
            }),
          ];
      headline.replaceChildren(mark(tone, 24), h("div", { class: "vault-bw-headline-text" }, h("h2", { text: title }), h("p", { text: body })), h("div", { class: "vault-bw-actions" }, controls));
      headline.dataset.tone = tone;
      steps.replaceChildren(...stepsOf(place, state).map((step, index) => h("li", { class: step.tone }, mark(step.tone === "idle" ? "idle" : step.tone, 13), h("div", {}, h("span", { class: "overline", text: `Step ${index + 1}` }), h("strong", { text: step.title }), step.detail && h("span", { class: "dim", text: step.detail })))));
      notes.replaceChildren(
        ...[
          failure && callout({ tone: "bad", title: failure.title, text: failure.text, extra: button({ label: "Dismiss", small: true, tone: "ghost", onclick: actions.dismiss }) }),
          // The way to the key matters until Bitwarden is open. With several keys the choice stays on show, since it is also how to switch account.
          !unlocked || key.chosen?.gap || state.key_sets.length > 1 ? key.note : null,
        ].filter(Boolean),
      );
      paintCache(place, state, busy);
    },
  };
}
