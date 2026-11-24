import { formatClock, h, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { staleKeeper } from "../../data.js";
import { confirmAction } from "../../overlays.js";
import { button, notice } from "../../widgets.js";
import { lookInside, readImportState } from "./api.js";
import { idleCard, listingCard } from "./import_listing.js";
import { importBanner, runImport } from "./import_run.js";
import { createSourceCard } from "./import_source.js";
import { everyOption, partHead } from "./kit.js";
import { IMPORT_HASH, IMPORT_PATH, count, lossOf } from "./words.js";

let asked = null;
let arrive = () => {};

export function open(_context, { preset }) {
  asked = preset;
  if (location.hash === IMPORT_HASH) return arrive();
  location.hash = IMPORT_HASH;
}

// Bring settings from another machine, at #/dotfiles/import. On arrival it says what this machine's dotfiles folder holds and lists the
// archives in the home folder. An archive is looked into before anything changes: what is new, what differs, what is only here and would
// go. Bringing it in runs the import command as a task, and the page then offers to put the files in place.
export function createPart({ activity, tools }) {
  const choice = { from: "file", source: "", address: "", remote: "", password: "", busy: false };
  const view = { fate: "", term: "", order: "fate", limit: 150 };
  let machine = null;
  let problem = null;
  // What the last look inside found, and for which archive: a change of the source drops it.
  let listing = null;
  let lookedAt = "";
  let lookProblem = "";
  let looking = false;
  let run = null;
  let ticket = 0;
  let lookTicket = 0;
  let readAt = 0;

  const reload = () => keeper.load();
  const card = createSourceCard({ choice, tools, onChange: sourceChanged, onLook: look, onCopy: copyOver, onReceived: () => read() });
  const stamp = h("span", { class: "dotfiles-stamp" });
  const refresh = button({ label: "Refresh", glyph: "refresh", onclick: reload });
  const bannerHolder = h("div");
  const problemHolder = h("div");
  const mainHolder = h("div", { class: "dotfiles-main" });
  const columns = h("div", { class: "dotfiles-columns", hidden: true }, mainHolder, card.element);
  const preset = () => (choice.from === "ssh" ? { ssh: "on", remote: choice.remote.trim() } : card.sourceOf() ? { url: card.sourceOf() } : {});
  const element = h(
    "div",
    { class: "dotfiles-part", hidden: true },
    partHead({ title: "Bring settings from another machine", lede: "Open an archive made on the other machine, see what it would change here, then put it in place.", actions: [stamp, everyOption(tools, IMPORT_PATH, preset), refresh] }),
    bannerHolder,
    problemHolder,
    columns,
  );

  function sourceChanged() {
    if (listing && card.sourceOf() === lookedAt) return;
    lookTicket += 1;
    listing = null;
    lookProblem = "";
    looking = false;
    paintMain();
  }

  function paintMain() {
    if (!machine) return;
    mainHolder.replaceChildren(listing ? listingCard({ listing, source: tildify(lookedAt, state.boot.home), view, busy: choice.busy, onApply: apply }) : idleCard({ machine, looking, problem: lookProblem }));
  }

  function paint() {
    stamp.textContent = machine && readAt ? `Read at ${formatClock(readAt)}` : "";
    bannerHolder.replaceChildren(
      ...(run
        ? [
            importBanner({
              run, tools,
              onReveal: () => activity.reveal(run.id),
              onDismiss() {
                run = null;
                paint();
              },
            }),
          ]
        : []),
    );
    problemHolder.replaceChildren(...(problem ? [notice({ glyph: "alert", tone: "bad", title: "This machine could not be read", body: problem.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: reload }) })] : []));
    columns.hidden = !machine || problem !== null;
    if (!machine || problem) return;
    card.show(machine);
    if (asked) card.fill(asked);
    asked = null;
    paintMain();
  }

  async function read() {
    const mine = (ticket += 1);
    refresh.disabled = true;
    let found = null;
    let failure = null;
    try {
      found = await readImportState();
    } catch (error) {
      failure = error;
    }
    if (mine !== ticket) return found;
    refresh.disabled = false;
    machine = found ?? machine;
    problem = failure;
    readAt = Date.now() / 1000;
    if (failure) keeper.spoil();
    paint();
    return found;
  }

  async function look() {
    if (choice.busy || card.problems().length > 0) return;
    const mine = (lookTicket += 1);
    const source = card.sourceOf();
    listing = null;
    lookProblem = "";
    looking = true;
    paintMain();
    let found = null;
    try {
      found = await lookInside(source, choice.password);
    } catch (error) {
      lookProblem = error.message;
    }
    if (mine !== lookTicket) return;
    looking = false;
    listing = found;
    lookedAt = source;
    Object.assign(view, { fate: "", term: "", limit: 150 });
    paintMain();
  }

  async function bring({ source, password, remote }) {
    choice.busy = true;
    card.paint();
    paintMain();
    await runImport({
      activity, source, password, remote, read,
      onPhase(next) {
        if (run !== next) card.forget();
        run = next;
        // What was looked into no longer says what would change: the folder is another one now.
        if (next.phase === "done") listing = null;
        paint();
        if (!element.closest("[hidden]")) element.closest(".stage")?.scrollTo({ top: 0, behavior: "smooth" });
      },
    });
    choice.busy = false;
    card.paint();
    paintMain();
  }

  async function apply() {
    if (choice.busy || !listing) return;
    const lost = listing.counts.removed + listing.counts.replaced;
    const sure =
      !listing.folder_exists ||
      (await confirmAction({
        title: "Replace your dotfiles folder?", confirm: "Replace the folder", tone: lost > 0 ? "danger" : "primary",
        body: `Everything in ${tildify(machine.folder, state.boot.home)} is removed and the archive's files take its place. ${lost > 0 ? `${lossOf(listing.counts)}. ` : "Every file here is in the archive unchanged. "}This cannot be undone from here.`,
      }));
    if (sure) bring({ source: lookedAt, password: choice.password, remote: "" });
  }

  async function copyOver() {
    if (choice.busy || card.problems().length > 0) return;
    const remote = choice.remote.trim();
    const here = machine.exists && machine.files > 0;
    const sure = await confirmAction({
      title: `Copy the dotfiles folder from ${remote}?`, confirm: "Copy it over", tone: here ? "danger" : "primary",
      body: here ? `This machine's dotfiles folder holds ${count(machine.files, "file", "files")}. The other machine's folder is copied over it, and the page cannot show first what that changes.` : "This machine has no dotfiles yet. The other machine's folder becomes this one's.",
    });
    if (sure) bring({ source: "", password: null, remote });
  }

  const keeper = staleKeeper(element, () => (choice.busy ? machine : read()));
  // Archives arrive outside this page, so every visit reads the home folder again. What was chosen and looked into stays.
  arrive = () => keeper.load();
  return { element, show: () => arrive() };
}
