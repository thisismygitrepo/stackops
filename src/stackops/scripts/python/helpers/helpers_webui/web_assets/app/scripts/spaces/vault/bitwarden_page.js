import { h, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { PLACES } from "../../agent_places.js";
import { markStale, staleKeeper } from "../../data.js";
import { confirmAction } from "../../overlays.js";
import { button, skeleton } from "../../widgets.js";
import { formatBytes, plural } from "../../words.js";
import { readPlace, readState, runCommand } from "./bitwarden_api.js";
import { createFinder } from "./bitwarden_find.js";
import { createStatus } from "./bitwarden_status.js";
import { APPS_ADDRESS, BITWARDEN_HASH, BITWARDEN_PATHS, KEY_NAMES, UNLOCK_PATH, failureOf } from "./bitwarden_words.js";
import { addLogin } from "./login_editor.js";
import { loadProblem, optionsButton, partHead, showInList } from "./tools_kit.js";

let page = null;
// What whoever opened the page meant: the part it is about, and a search word or account handed over with it.
let arrival = { focus: "", term: "", account: "" };

// The four Bitwarden commands share this page, at #/vault/bitwarden: unlocking, syncing and clearing the cache all change one state, and
// finding a login depends on it, so they are shown together with that state first. It is a page because the list of logins is something to
// search and come back to. Unlock, Sync and Clear run the commands themselves; the page only reads state and labels, and a value on request.
export function open(_context, { preset = {}, focus = "" }) {
  arrival = { focus, term: typeof preset.name === "string" ? preset.name : "", account: typeof preset.account_name === "string" ? preset.account_name : "" };
  if (location.hash === BITWARDEN_HASH) page?.arrive();
  else location.hash = BITWARDEN_HASH;
}

export function createPart(context) {
  page ??= createBitwardenPage(context);
  return page;
}

function createBitwardenPage({ activity, tools }) {
  let place = null;
  let state = null;
  let busy = "";
  let failure = null;
  let ticket = 0;

  const actions = {
    repaint: () => paint(),
    dismiss() {
      failure = null;
      paint();
    },
    install: () => (location.hash = APPS_ADDRESS),
    showKey: () => showInList({ term: state.login_name }),
    addKey: () =>
      addLogin({
        title: "Add your Bitwarden API key", place: "user",
        preset: { name: state.login_name, description: "API key the Bitwarden command-line program signs in with.", secrets: [{ name: "api-login", tags: [], scopes: [], values: KEY_NAMES.map((key) => ({ key, json: false })) }] },
      }).catch((error) => toast(error.message)),
    unlock: (account) => act("unlock", ["login-and-unlock", ...(account ? ["--account-name", account] : [])], "Bitwarden is unlocked.", "Unlock did not work"),
    sync: () => act("sync", ["sync"], "Bitwarden is in step with its server.", "The sync did not work"),
    async clear() {
      const searches = state?.cache_opened ? ` and what ${plural(state.saved_searches, "search")} found` : "";
      const sure = await confirmAction({
        title: "Clear what Bitwarden saved here?", confirm: "Clear the cache", tone: "danger",
        body: `This deletes the ${formatBytes(place.cache_bytes)} file that holds the saved session${searches}. Bitwarden stays signed in, but StackOps has to unlock it again before the next search or sync. Nothing in your Bitwarden vault changes.`,
      });
      if (sure) act("clear", ["clean-cache"], "The cache is cleared.", "The cache could not be cleared");
    },
  };
  const status = createStatus({ actions });
  const finder = createFinder({ actions: { install: actions.install, unlock: () => status.element.scrollIntoView({ behavior: "smooth", block: "start" }) } });
  const failureHolder = h("div");
  const waiting = h("div", { class: "vault-bw-waiting" }, skeleton(1, "card"));
  const again = button({
    label: "Check again", glyph: "refresh", title: "Asks Bitwarden how it stands once more",
    onclick: () => {
      failure = null;
      load();
    },
  });
  const element = h(
    "div",
    { class: "vault-bw", hidden: true },
    partHead({ title: "Bitwarden", lede: "Open your Bitwarden vault, keep this machine's copy of it in step, and look a login up. All of it goes through Bitwarden's command-line program.", actions: [agentButton(activity, { ...PLACES.vault, title: "Bitwarden", commands: ["devops vault bitwarden"], about: "StackOps' bridge to a Bitwarden vault through Bitwarden's command-line program: unlocking it, syncing this machine's copy, and looking a login up.", ideas: ["Why can't I unlock Bitwarden here?"] }), again, optionsButton(tools, BITWARDEN_PATHS)] }),
    failureHolder,
    waiting,
    status.element,
    finder.element,
  );

  function paint() {
    waiting.hidden = place !== null;
    status.element.hidden = place === null;
    finder.element.hidden = place === null;
    if (place) status.paint({ place, state, busy, failure });
  }

  // One of the three commands, run to its end with the button showing it is at work. Afterwards everything is read again, here and wherever
  // else the app shows it.
  async function act(name, commandArguments, done, failed) {
    if (busy) return;
    busy = name;
    failure = null;
    paint();
    try {
      const result = await runCommand(commandArguments);
      if (result.ok) toast(done, "info");
      else failure = { title: failed, text: failureOf(result.said) };
    } catch (error) {
      failure = { title: failed, text: error.message };
    }
    busy = "";
    markStale();
  }

  // In steps: what can be told at once, then what `bw` says, then the list. One after the other on purpose, since each of the last two opens
  // the cache with the GPG key, and a key that asks for its passphrase should ask once.
  async function load() {
    const mine = (ticket += 1);
    again.disabled = true;
    try {
      const found = await readPlace();
      if (mine !== ticket) return;
      place = found;
      failureHolder.replaceChildren();
      paint();
      finder.wait();
      const answer = found.installed ? await readState() : null;
      if (mine !== ticket) return;
      state = answer;
      paint();
      arrive();
      const listed = await finder.load(false);
      // A list read from Bitwarden just now was also written to the cache, which the cache's own numbers on this page do not show yet.
      if (mine === ticket && listed && !listed.saved) {
        place = await readPlace();
        if (mine !== ticket) return;
        if (state) state = { ...state, saved_searches: listed.searches };
        paint();
      }
    } catch (error) {
      if (mine !== ticket) return;
      keeper.spoil();
      place = null;
      state = null;
      paint();
      waiting.hidden = true;
      failureHolder.replaceChildren(loadProblem(error, { retry: load, tools, path: UNLOCK_PATH }));
    } finally {
      if (mine === ticket) again.disabled = false;
    }
  }

  // Brings the part that was asked for into view, once the page knows how Bitwarden stands.
  function arrive() {
    if (!place) return;
    const { focus, term, account } = arrival;
    arrival = { focus: "", term: "", account: "" };
    if (account) {
      status.choose(account);
      paint();
    }
    if (focus === "find") finder.arrive(term);
    else if (focus === "cache") status.element.querySelector(".vault-bw-cache").scrollIntoView({ behavior: "smooth", block: "center" });
  }

  const keeper = staleKeeper(element, load);
  return {
    element, arrive,
    // Every visit asks again: Bitwarden locks and syncs outside this app. Values that were on show are covered first.
    show() {
      finder.cover();
      keeper.load();
    },
  };
}
