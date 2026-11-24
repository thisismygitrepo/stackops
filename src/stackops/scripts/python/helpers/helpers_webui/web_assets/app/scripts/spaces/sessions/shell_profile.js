import { h, icon } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { staleKeeper } from "../../data.js";
import { replay, rise } from "../../motion.js";
import { button, callout, notice, sectionHead, skeleton } from "../../widgets.js";
import { createActions } from "./shell_profile/actions.js";
import { explainSection } from "./shell_profile/explain.js";
import { createGives } from "./shell_profile/gives.js";
import { blockedRow, shellCard } from "./shell_profile/shell_card.js";
import { PAGE_HASH, SHELLS, STATE_ADDRESS, TOOL_PATH } from "./shell_profile/words.js";

// Whoever opens the tool with Nushell picked lands on that shell's card.
export function open(_context, { preset }) {
  location.hash = ["nushell", "n"].includes(preset.which) ? `${PAGE_HASH}/nushell` : PAGE_HASH;
}

// Sessions › Shell profile, at #/sessions/shell-profile: every shell StackOps can set up, where this machine stands on each, what a setup run
// does, and what a terminal gains from it. The page reads the machine on every visit, because a profile is also edited outside this app.
export function createPart({ activity, tools }) {
  let shown = null;
  let ticket = 0;
  let latest = null;
  let spot = "";

  const bannerHolder = h("div");
  const body = h("div", { class: "shellprof-body" }, skeleton(1, "card"), skeleton(3, "row"));
  const actions = createActions({ activity, read: () => shown, reload: () => keeper.load(), onChange: () => shown && paint(shown) });
  const gives = createGives({ install: actions.install });

  function paint(next) {
    const entering = shown === null;
    shown = next;
    bannerHolder.replaceChildren(...[actions.banner()].filter(Boolean));
    const usable = next.shells.filter((shell) => !shell.blocker).sort((left, right) => Number(right.login) - Number(left.login));
    const blocked = next.shells.filter((shell) => shell.blocker);
    const login = usable.find((shell) => shell.login);
    const others = usable.filter((shell) => shell !== login);
    // The shell a setup run acts on: the login shell where the command reaches it, and Nushell otherwise.
    const target = usable.find((shell) => shell.login && shell.route !== "manual") ?? usable.find((shell) => shell.route !== "manual");
    const loginName = login ? SHELLS[login.id].name : next.login_shell;
    const cardOf = (shell) => shellCard(shell, { featured: shell === login, loginName, actions: { setUp: actions.setUp, copyFiles: actions.copyFiles, openFile: actions.openFile, busy: actions.busy() } });
    body.replaceChildren(
      ...[
        !login && next.login_shell && callout({ tone: "warn", title: `You sign in with ${next.login_shell}`, text: `StackOps has no setup for ${next.login_shell}, so nothing here changes the terminals that start in it. The shells below can still load StackOps' setup.` }),
        usable.length === 0 && notice({ glyph: "terminal", title: "No shell here can be set up", body: "StackOps sets up zsh and bash on macOS and Linux, PowerShell on Windows, and Nushell on all three. Once one of them is installed, it shows up here." }),
        login && cardOf(login),
        others.length + blocked.length > 0 && h("section", { class: "block" }, sectionHead(login ? "Other shells" : "Shells StackOps can set up"), h("div", { class: "shellprof-list" }, others.map(cardOf), blocked.map((shell) => blockedRow(shell, { install: actions.install })))),
        target && explainSection(target, next.folders),
        gives.element,
      ].filter(Boolean),
    );
    gives.paint(usable);
    if (entering) rise(body);
    const spotted = spot && body.querySelector(`[data-shell="${CSS.escape(spot)}"]`);
    spot = "";
    if (spotted) {
      spotted.scrollIntoView({ block: "center" });
      replay(spotted, "shellprof-spot");
    }
  }

  // Resolves to whether the page now shows what the machine holds. A read that a later one overtook waits for that one, so whoever asked
  // never carries on with an older answer.
  function load() {
    const mine = (ticket += 1);
    const pending = (async () => {
      let next;
      try {
        next = await request("GET", STATE_ADDRESS);
      } catch (error) {
        if (mine !== ticket) return latest;
        keeper.spoil();
        bannerHolder.replaceChildren();
        // A server started before this page existed has no answer for it. That clears up with a restart, so the notice says that and not "404".
        const reason = error.status === 404 ? "The StackOps server that is running is older than this page. Restart it, then open this page again." : error.message;
        body.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "This didn't load", body: reason, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: () => keeper.load() }) }));
        return false;
      }
      if (mine !== ticket) return latest;
      paint(next);
      return true;
    })();
    latest = pending;
    return pending;
  }

  const element = h(
    "div",
    { class: "shellprof", hidden: true },
    h(
      "header",
      { class: "view-head" },
      h("div", { class: "view-title" }, h("a", { class: "shellprof-back", href: "#/sessions" }, icon("back", 14), h("span", { text: "Sessions" })), h("h1", { text: "Shell profile" }), h("p", { text: "A shell reads its profile each time a terminal opens. One line in that file loads StackOps' short commands, prompt and history search." })),
      h(
        "div",
        { class: "view-actions" },
        button({ label: "All options", glyph: "sliders", title: "Open the form with every option this tool has", onclick: () => tools.open(TOOL_PATH, { plain: true }) }),
        button({ label: "Check again", glyph: "refresh", title: "Read the profiles on this machine again", onclick: () => keeper.load() }),
      ),
    ),
    bannerHolder,
    body,
  );
  const keeper = staleKeeper(element, load);
  return {
    element,
    show(rest) {
      spot = rest[0] ?? "";
      keeper.load();
    },
  };
}
