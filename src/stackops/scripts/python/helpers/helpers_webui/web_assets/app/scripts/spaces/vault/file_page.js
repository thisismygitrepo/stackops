import { h, toast } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { PLACES } from "../../agent_places.js";
import { markStale, staleKeeper } from "../../data.js";
import { button, sectionHead, skeleton } from "../../widgets.js";
import { createFile, protectFile, readHealth, refreshSchema, runCheck } from "./file_api.js";
import { fileCard } from "./file_card.js";
import { createHolds } from "./file_holds.js";
import { FILE_HASH, FILE_PATHS, ROTATE_PATH, VALIDATE_PATH, fileTitle, summaryOf } from "./file_words.js";
import { loadProblem, mark, optionsButton, partHead, showInList } from "./tools_kit.js";
import { kindOf } from "./words.js";

let page = null;
// Which part of the page whoever opened it meant: the check, what the vault holds, or creating a file.
let wanted = "";

// Three commands share this page, at #/vault/file: checking the vault file, counting what it holds, and creating a missing one are one job, the
// state of the file. It is a page and not a sheet because it is something to read, and its findings should still be there after a repair.
// Each command takes a file of the person's own choosing as well; one handed over that way goes to the command's own form.
export function open({ tools }, { preset = {}, focus = "", path = VALIDATE_PATH }) {
  if (preset.custom_path) return tools.open(path, { plain: true, preset });
  wanted = focus;
  if (location.hash === FILE_HASH) page?.arrive();
  else location.hash = FILE_HASH;
}

export function createPart(context) {
  page ??= createFilePage(context);
  return page;
}

function createFilePage({ activity, tools }) {
  // The full check's answers, by file and the version of it that was checked, so a file is only checked again once it has changed.
  const checks = new Map();
  let health = null;
  let ticket = 0;

  const summary = h("div", { class: "vault-file-summary", hidden: true });
  const cards = h("div", { class: "vault-file-cards" }, skeleton(2, "card"));
  const failure = h("div");
  const holds = createHolds({
    onLabel: (label) => showInList({ term: label }),
    onShow: (row) => showInList({ key: `${row.source}\n${row.index}` }),
    // The tool must find exactly one secret. Two logins can share a name, so the account goes along as a search word where it can be one.
    onReplace: (row) => tools.open(ROTATE_PATH, { preset: { login_name: row.login, secret_name: row.secret, secrets_source: kindOf(row.source), ...(row.account && !/\s/.test(row.account) && { terms: row.account }) } }),
  });
  const filesSection = h("section", { class: "block" }, sectionHead("The files"), cards);
  const again = button({ label: "Check again", glyph: "refresh", title: "Reads the files and runs the full check once more", onclick: () => load(true) });
  const element = h(
    "div",
    { class: "vault-file", hidden: true },
    partHead({ title: "Vault file", lede: "Whether each vault file can be used, what is wrong if not, and what it holds. Nothing here reads a value into the page.", actions: [agentButton(activity, { ...PLACES.vault, title: "Vault file", commands: FILE_PATHS, about: "Whether each vault file can be used, what is wrong with it if not, and how many logins and values it holds.", ideas: ["Why does my vault file not pass its check?"] }), again, optionsButton(tools, FILE_PATHS)] }),
    failure,
    summary,
    filesSection,
    holds.element,
  );

  const checkOf = (file) => checks.get(`${file.name}\n${file.version}`);
  const checksByName = () => new Map(health.files.map((file) => [file.name, checkOf(file)]));
  // One change to a file, then the page and everything else that shows the vault read it again.
  const change = (action, done) => async (file) => {
    try {
      await action(file.name);
      toast(done(file), "info");
    } catch (error) {
      toast(error.message);
    }
    markStale();
  };
  const actions = {
    create: change(createFile, (file) => `Created ${fileTitle(file.name).toLowerCase()}.`),
    schema: change(refreshSchema, () => "The schema file is in place."),
    protect: change(protectFile, () => "Only you can read the file now."),
    recheck: (file) => check(file, ticket),
    showDue: () => holds.dueSection.scrollIntoView({ behavior: "smooth", block: "start" }),
    showLogins: () => showInList({}),
  };

  function paint() {
    const { tone, title, body } = summaryOf(health.files, checksByName());
    summary.hidden = false;
    summary.dataset.tone = tone;
    summary.replaceChildren(mark(tone, 22), h("div", {}, h("h2", { text: title }), h("p", { text: body })));
    // The person's own file first: it is the one every project reads.
    const ordered = [...health.files].sort((left, right) => (kindOf(left.name) === "user" ? 0 : 1) - (kindOf(right.name) === "user" ? 0 : 1));
    cards.replaceChildren(...ordered.map((file) => fileCard({ file, check: checkOf(file), starter: health.starter_logins, activity, actions })));
    holds.paint(health.files);
  }

  async function check(file, mine) {
    const key = `${file.name}\n${file.version}`;
    checks.delete(key);
    if (mine === ticket) paint();
    const answer = await runCheck(file.name).catch((error) => ({ verdict: "unchecked", finding: null, trouble: error.message }));
    checks.set(key, answer);
    if (mine === ticket) paint();
  }

  // In steps: the files as they read, which is quick, and then the full check of each file that reads fine, shown as it comes in.
  async function load(fresh) {
    const mine = (ticket += 1);
    again.disabled = true;
    try {
      const answer = await readHealth();
      if (mine !== ticket) return;
      health = answer;
      failure.replaceChildren();
      filesSection.hidden = false;
    } catch (error) {
      if (mine !== ticket) return;
      health = null;
      keeper.spoil();
      summary.hidden = true;
      filesSection.hidden = true;
      holds.element.hidden = true;
      failure.replaceChildren(loadProblem(error, { retry: () => load(false), tools, path: VALIDATE_PATH }));
      return;
    } finally {
      if (mine === ticket) again.disabled = false;
    }
    if (fresh) checks.clear();
    paint();
    arrive();
    await Promise.all(health.files.filter((file) => file.holds && !checkOf(file)).map((file) => check(file, mine)));
  }

  // Brings what was asked for into view once there is something to show.
  function arrive() {
    if (!wanted || !health) return;
    const target = wanted === "holds" ? holds.element : wanted === "create" ? (cards.querySelector(".vault-file-card.missing") ?? filesSection) : null;
    wanted = "";
    if (target && !target.hidden) requestAnimationFrame(() => target.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  const keeper = staleKeeper(element, () => load(false));
  return {
    element, arrive,
    // Every visit reads the files again: they change outside this app, and the reading is quick.
    show: () => keeper.load(),
  };
}
