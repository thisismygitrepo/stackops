import { h } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { query, staleKeeper } from "../../data.js";
import { button, copyChip, skeleton } from "../../widgets.js";
import { failNotice, mark, partHead } from "./kit.js";
import { createAddKey } from "./ssh/add_key.js";
import { checkTrack, openChecks, passedPills, serviceState, verdictOf } from "./ssh/checks.js";
import { createKeysCard } from "./ssh/keys.js";
import { createSetupCard } from "./ssh/setup.js";
import { API, HASHES, PATHS, go } from "./words.js";

let page = null;
// Which part of the page whoever opened it meant: the setup or the keys.
let wanted = "";

// SSH access is one page for two commands, `ssh install-server` and `ssh add-key`: both are about other machines signing in to this one,
// and what each does only makes sense beside what is already in place. It is a page and not a sheet because the setup runs as a task to
// watch and the page shows the result under it when the task ends.
export function open(_context, { preset }, section = "setup") {
  wanted = preset?.section ?? section;
  go(HASHES.ssh);
}

const PLACE = {
  title: "SSH access", commands: [PATHS.setup, PATHS.addKey, PATHS.debug],
  about: "Whether other machines can sign in to this one over SSH: the server, the checks it has to pass, and the public keys that are allowed in.",
  ideas: ["Why can't my other machine sign in here?"],
};

export function createPart(context) {
  page ??= createSshPage(context);
  return page;
}

function createSshPage({ activity, tools }) {
  let checks = null;
  let plan = null;
  let user = "";
  let ticket = 0;
  const hero = h("section", { class: "network-hero" }, skeleton(1, "card"));
  const problems = h("div", { class: "network-ssh-problems" });
  const failure = h("div");
  const keys = createKeysCard({ activity });
  const addKey = createAddKey({ onAdded: () => load() });
  const setup = createSetupCard({ activity });
  const grid = h("div", { class: "network-grid" }, keys.element, addKey.element);
  const again = button({ label: "Check again", glyph: "refresh", title: "Reads this machine once more", onclick: () => load(true) });

  function paintHero(result, address) {
    const verdict = verdictOf(result);
    hero.replaceChildren(
      h(
        "div",
        { class: `network-hero-top ${verdict.tone}` },
        mark(verdict.tone, verdict.glyph),
        h(
          "div",
          { class: "network-hero-text" },
          h("h2", { text: verdict.title }),
          h("p", { text: verdict.body }),
          !result.summary.has_errors && user && address && h("p", { class: "network-hero-hint" }, "From another machine on this network: ", copyChip(`ssh ${user}@${address}`)),
        ),
        serviceState(result.checks) !== "on" && !plan?.blocker && button({ label: "See how to switch it on", glyph: "power", tone: serviceState(result.checks) === "off" ? "primary" : "plain", onclick: () => setup.element.scrollIntoView({ block: "start", behavior: "smooth" }) }),
      ),
      checkTrack(result.checks),
    );
    const open = openChecks(result.checks);
    const passed = passedPills(result.checks);
    problems.replaceChildren(...[open, passed.length > 0 && open && h("div", { class: "project-facts" }, passed)].filter(Boolean));
  }

  // In steps: the keys and the plan are quick file reads; the checks run a command and arrive when they are done.
  async function load(fresh = false) {
    const mine = (ticket += 1);
    element.classList.add("loading");
    failure.replaceChildren();
    const overview = request("GET", `${API}/ssh/keys`).then((answer) => {
      if (mine !== ticket) return;
      user = answer.user;
      keys.paint(answer);
      addKey.paint(answer);
    });
    const planned = request("GET", `${API}/ssh/setup`).then((answer) => {
      if (mine !== ticket) return;
      plan = answer;
      setup.paint({ plan, checks });
    });
    const checked = Promise.all([query([...PATHS.debug.split(" "), "--json"], fresh), overview, query([...PATHS.address.split(" "), "--json"]).catch(() => null)]).then(([result, , address]) => {
      if (mine !== ticket) return;
      checks = result.json.checks;
      paintHero(result.json, address?.json?.lan?.ipv4_address);
      if (plan) setup.paint({ plan, checks });
    });
    try {
      await Promise.all([overview, planned, checked]);
    } catch (error) {
      if (mine !== ticket) return;
      keeper.spoil();
      failure.replaceChildren(failNotice(error, () => load(true)));
    }
    if (mine === ticket) element.classList.remove("loading");
  }

  const element = h(
    "div",
    { class: "network-part network-ssh", hidden: true },
    partHead({
      title: "SSH access", lede: "Whether other machines can sign in to this one over SSH, whose keys are allowed, and how to switch it on.",
      actions: [agentButton(activity, PLACE), again, button({ label: "All options", glyph: "sliders", title: "The add-a-key command's own form, which can also put a key on another machine", onclick: () => tools.open(PATHS.addKey, { plain: true }) })],
    }),
    failure,
    hero,
    problems,
    grid,
    setup.element,
  );
  const keeper = staleKeeper(element, () => load());
  return {
    element,
    show(rest) {
      const section = rest[0] ?? wanted;
      wanted = "";
      keeper.ensure();
      if (section === "keys") requestAnimationFrame(() => addKey.focus());
      if (section === "setup") requestAnimationFrame(() => setup.element.scrollIntoView({ block: "nearest", behavior: "smooth" }));
    },
  };
}
