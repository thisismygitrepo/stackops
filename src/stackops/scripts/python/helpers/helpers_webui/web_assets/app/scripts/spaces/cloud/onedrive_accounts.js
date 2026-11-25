import { h, icon, toast } from "/assets/scripts/dom.js";
import { openDialog } from "../../overlays.js";
import { avatar, button, copyText, field, notice, pathChip, pill, textBox } from "../../widgets.js";
import { failureIn } from "../security/tools_kit.js";
import { startWatched } from "../security/tools_run.js";
import { addAccount, signInArguments, startInTurn } from "./onedrive_api.js";
import { safeLink } from "./onedrive_words.js";

const APP_REGISTRATIONS = "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade";
const CODE_POLL_MILLISECONDS = 400;

// The accounts as tabs, each with whether it is signed in, then the way to add one and where they are kept.
export function createAccountsBar({ onPick, onAdd }) {
  const tabs = h("div", { class: "od-accounts", role: "tablist", "aria-label": "OneDrive accounts" });
  const kept = h("span", { class: "od-kept" });
  const adder = button({ label: "Add account", glyph: "plus", small: true, onclick: onAdd });
  const element = h("div", { class: "od-accounts-bar" }, tabs, adder, h("span", { class: "spacer" }), kept);
  return {
    element,
    paint(accounts, selected) {
      tabs.replaceChildren(
        ...accounts.map((account) =>
          h(
            "button",
            { class: "od-account", type: "button", role: "tab", "aria-selected": String(account.name === selected), title: account.signedIn ? `Show ${account.name}'s files` : `${account.name} has to sign in first`, onclick: () => onPick(account.name) },
            avatar(account.name, 28),
            h("span", { class: "od-account-name", text: account.name }),
            pill(account.signedIn ? "Signed in" : "Sign-in needed", account.signedIn ? "good" : "warn"),
          ),
        ),
      );
      tabs.hidden = accounts.length === 0;
    },
    showKept: (path) => kept.replaceChildren(h("span", { class: "dim", text: "Accounts are kept in" }), pathChip(path)),
  };
}

// A new account is a name of your choosing and the ID of an app registered with Microsoft. `taken` holds the names in use.
export function openAddAccount({ taken, onAdded }) {
  const dialog = openDialog({ label: "Add a OneDrive account", size: "small" });
  const name = textBox("", { placeholder: "personal", "aria-label": "Account name" });
  const clientId = textBox("", { placeholder: "00000000-0000-0000-0000-000000000000", "aria-label": "Application (client) ID" });
  const problem = h("p", { class: "od-problem", hidden: true });
  const say = (text) => {
    problem.textContent = text;
    problem.hidden = text === "";
  };
  const add = button({ label: "Add account", tone: "primary", onclick: () => submit() });

  function reasonAgainst(chosen, id) {
    if (chosen === "") return "Give the account a name.";
    if (chosen.startsWith("-")) return "A name cannot start with a dash.";
    if (taken.includes(chosen)) return `There is already an account called ${chosen}.`;
    if (id === "") return "Paste the application's ID.";
    if (id.startsWith("-")) return "An application ID does not start with a dash.";
    return "";
  }

  async function submit() {
    const chosen = name.value.trim();
    const id = clientId.value.trim();
    const reason = reasonAgainst(chosen, id);
    say(reason);
    if (reason) return;
    add.disabled = true;
    try {
      await addAccount(chosen, id);
    } catch (error) {
      say(error.message);
      add.disabled = false;
      return;
    }
    dialog.close();
    onAdded(chosen);
  }

  for (const box of [name, clientId]) box.addEventListener("keydown", (event) => event.key === "Enter" && submit());
  dialog.body.append(
    h("h2", { text: "Add a OneDrive account" }),
    h("p", { text: "After this you sign in once on Microsoft's site. The sign-in is then kept with the account, so it is not asked for again." }),
    field("Name", name, "Yours to choose. It tells your accounts apart here."),
    field(
      "Application (client) ID",
      clientId,
      "From an app you register in the Azure portal. It has to allow personal Microsoft accounts and public client flows, because you sign in with a code on Microsoft's site.",
    ),
    h("a", { class: "link od-out", href: APP_REGISTRATIONS, target: "_blank", rel: "noopener" }, "Open app registrations in the Azure portal", icon("external", 13)),
    problem,
    h("div", { class: "dialog-actions" }, button({ label: "Cancel", onclick: () => dialog.close() }), add),
  );
  name.focus();
}

// The code the sign-in command prints first, as one line of JSON, before it waits for the sign-in to finish on Microsoft's side.
function challengeIn(text) {
  const line = /\{[^{}]*"status":\s*"authorization_required"[^{}]*\}/.exec(text);
  if (!line) return null;
  try {
    return JSON.parse(line[0]);
  } catch {
    return null;
  }
}

// Signing an account in, shown in place of its files: an offer, then Microsoft's code and the page to enter it on, then the wait. The command
// runs as a task kept out of the Activity panel; "Show the console" brings it there. One sign-in runs at a time. `onDone(account)` is called
// when a sign-in is saved.
export function createSignIn({ activity, onDone }) {
  const element = h("section", { class: "od-signin", hidden: true });
  // The account whose sign-in the page shows, the sign-in on its way, and how the last one ended when it did not work.
  let viewed = null;
  let current = null;
  let last = null;

  const offer = (account, words) =>
    notice({
      glyph: "key", title: `Sign in to use ${account}`,
      body: words || "Microsoft shows you a short code and a page to enter it on. Your password is typed there, never here.",
      action: button({ label: "Sign in with Microsoft", glyph: "key", tone: "primary", onclick: () => start(account) }),
    });

  const failed = ({ account, reason, run }) =>
    notice({
      glyph: "alert", tone: "bad", title: "The sign-in did not go through", body: reason || "The command stopped without saying why.",
      action: h("div", { class: "dialog-actions" }, run && button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", onclick: run.show }), button({ label: "Try again", glyph: "refresh", small: true, onclick: () => start(account) })),
    });

  function waiting({ account, run, challenge }) {
    const page = challenge && safeLink(challenge.verification_uri);
    const minutes = challenge && Number.isFinite(challenge.expires_in) ? Math.max(1, Math.round(challenge.expires_in / 60)) : null;
    return h(
      "div",
      { class: "od-signin-card", role: "status" },
      h("h2", { text: `Signing in ${account}` }),
      challenge
        ? h(
            "ol",
            { class: "od-steps" },
            h("li", {}, h("span", { text: "Open Microsoft's sign-in page" }), page ? h("a", { class: "btn primary small", href: page, target: "_blank", rel: "noopener" }, h("span", { text: "Open the page" }), icon("external", 14)) : h("code", { text: String(challenge.verification_uri) })),
            h("li", {}, h("span", { text: "Enter this code there" }), h("strong", { class: "od-code", text: challenge.user_code }), button({ label: "Copy", glyph: "copy", small: true, onclick: async () => (await copyText(challenge.user_code, "Type the code by hand.")) && toast("Code copied.", "info") })),
            h("li", {}, h("span", { text: "Sign in and allow access. This page moves on by itself." })),
          )
        : h("p", { class: "dim", text: "Asking Microsoft for a code…" }),
      h(
        "div",
        { class: "od-signin-foot" },
        h("i", { class: "ring" }),
        h("span", { text: challenge ? `Waiting for you to finish there${minutes ? `. The code works for about ${minutes} minutes.` : "."}` : "One moment." }),
        h("span", { class: "spacer" }),
        run && button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", onclick: run.show }),
        run && button({ label: "Cancel", glyph: "stop", small: true, onclick: run.stop }),
      ),
    );
  }

  function paint() {
    if (viewed === null) return;
    if (current && current.account === viewed) return element.replaceChildren(waiting(current));
    if (current) {
      return element.replaceChildren(
        notice({ glyph: "clock", title: `${current.account} is signing in`, body: "One sign-in runs at a time. Finish that one on Microsoft's site, or cancel it.", action: current.run && button({ label: "Cancel that sign-in", glyph: "stop", small: true, onclick: current.run.stop }) }),
      );
    }
    const ended = last && last.account === viewed ? last : null;
    element.replaceChildren(ended && !ended.cancelled ? failed(ended) : offer(viewed, ended ? "The sign-in was cancelled. Nothing was changed." : ""));
  }

  async function start(account) {
    if (current) return;
    const mine = (current = { account, run: null, challenge: null });
    last = null;
    paint();
    try {
      mine.run = await startInTurn(() => startWatched(activity, { title: `Sign in to OneDrive · ${account}`, emoji: "🔑", arguments: signInArguments(account) }));
    } catch (error) {
      current = null;
      last = { account, reason: error.message, run: null, cancelled: false };
      return paint();
    }
    paint();
    const watch = setInterval(() => {
      mine.challenge = challengeIn(mine.run.text());
      if (!mine.challenge) return;
      clearInterval(watch);
      paint();
    }, CODE_POLL_MILLISECONDS);
    const end = await mine.run.ended;
    clearInterval(watch);
    current = null;
    if (end.ok) return onDone(account);
    last = { account, reason: failureIn(end.text), run: mine.run, cancelled: end.stopped };
    paint();
  }

  return {
    element,
    show(account) {
      viewed = account;
      element.hidden = false;
      paint();
    },
    hide: () => (element.hidden = true),
    start,
  };
}
