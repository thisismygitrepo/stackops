import { formatClock, h } from "/assets/scripts/dom.js";
import { agentButton } from "../../agent_ask.js";
import { query, staleKeeper } from "../../data.js";
import { button, notice } from "../../widgets.js";
import { readExportPlan } from "./api.js";
import { contentsCard } from "./export_contents.js";
import { createPlanCard } from "./export_plan.js";
import { runExport } from "./export_run.js";
import { exportBanner, stepsCard } from "./export_steps.js";
import { everyOption, partHead } from "./kit.js";
import { EXPORT_HASH, EXPORT_PATH } from "./words.js";

const STATUS_ARGUMENTS = ["devops", "config", "dotfiles", "status", "--json"];

// What the view was opened with, kept until the page takes it: `open` can run before the page is made.
let asked = null;
let arrive = () => {};

export function open(_context, { preset }) {
  asked = preset;
  if (location.hash === EXPORT_HASH) return arrive();
  location.hash = EXPORT_HASH;
}

// Move to a new machine, at #/dotfiles/export. On arrival it shows what an archive made now would hold and what stays behind. The card beside
// that takes how the archive gets to the other machine, its password and where it is saved, and under the contents stand the steps for the
// other machine. The export runs as a task; the page says when the archive is ready, on offer, or sent.
export function createPart({ activity, tools }) {
  const choice = { way: "file", remote: "", password: "", again: "", elsewhere: false, output: "", place: null, busy: false };
  let plan = null;
  let problem = null;
  // The status command's answer, which the Dotfiles page has usually fetched already. It adds two remarks and is not waited for.
  let status = null;
  let run = null;
  let ticket = 0;
  let readAt = 0;

  const reload = () => keeper.load();
  const card = createPlanCard({ choice, tools, onChange: () => paintSteps(), onGo: make });
  const stamp = h("span", { class: "dotfiles-stamp" });
  const refresh = button({ label: "Refresh", glyph: "refresh", onclick: reload });
  const bannerHolder = h("div");
  const problemHolder = h("div");
  const contentsHolder = h("div");
  const stepsHolder = h("div");
  const columns = h("div", { class: "dotfiles-columns", hidden: true }, h("div", { class: "dotfiles-main" }, contentsHolder, stepsHolder), card.element);
  const preset = () => ({ ...(choice.way === "share" && { serve: "on" }), ...(choice.way === "ssh" && { ssh: "on", remote: choice.remote.trim() }), ...(choice.elsewhere && choice.output.trim() && { output: choice.output.trim() }) });
  const element = h(
    "div",
    { class: "dotfiles-part", hidden: true },
    partHead({ title: "Move to a new machine", lede: "Pack your dotfiles folder into one protected archive and get it to the other machine.", actions: [stamp, agentButton(activity, { commands: [EXPORT_PATH] }), everyOption(tools, EXPORT_PATH, preset), refresh] }),
    bannerHolder,
    problemHolder,
    columns,
  );

  function paintSteps() {
    const nothing = !plan || !plan.exists || plan.files === 0;
    stepsHolder.replaceChildren(...(nothing ? [] : [stepsCard({ plan, choice })]));
  }

  function paint() {
    stamp.textContent = plan && readAt ? `Read at ${formatClock(readAt)}` : "";
    bannerHolder.replaceChildren(
      ...(run && plan
        ? [
            exportBanner({
              run, plan,
              onReveal: () => activity.reveal(run.id),
              onStop: () => run.stop(),
              onDismiss() {
                run = null;
                paint();
              },
            }),
          ]
        : []),
    );
    problemHolder.replaceChildren(...(problem ? [notice({ glyph: "alert", tone: "bad", title: "This machine's dotfiles could not be read", body: problem.message, action: button({ label: "Try again", glyph: "refresh", small: true, onclick: reload }) })] : []));
    columns.hidden = !plan || problem !== null;
    if (!plan || problem) return;
    const nothing = !plan.exists || plan.files === 0;
    columns.classList.toggle("solo", nothing);
    card.element.hidden = nothing;
    contentsHolder.replaceChildren(contentsCard({ plan, status, tools }));
    card.show(plan);
    if (asked) card.fill(asked);
    asked = null;
    paintSteps();
  }

  // Only the latest reading is shown. The answer is handed back either way, to the run that asked for it.
  async function read() {
    const mine = (ticket += 1);
    refresh.disabled = true;
    let found = null;
    let failure = null;
    try {
      found = await readExportPlan();
    } catch (error) {
      failure = error;
    }
    if (mine !== ticket) return found;
    refresh.disabled = false;
    plan = found ?? plan;
    problem = failure;
    readAt = Date.now() / 1000;
    if (failure) keeper.spoil();
    paint();
    query(STATUS_ARGUMENTS).then((answer) => {
      if (mine !== ticket || !answer.json) return;
      status = answer.json;
      if (plan && !problem) contentsHolder.replaceChildren(contentsCard({ plan, status, tools }));
    }, () => {});
    return found;
  }

  async function make() {
    if (choice.busy || card.problems().length > 0) return;
    choice.busy = true;
    card.paint();
    await runExport({
      activity, plan, choice, read,
      onPhase(next) {
        // The task has the password by now, so the boxes let go of it.
        if (run !== next) card.forget();
        run = next;
        paint();
        if (!element.closest("[hidden]")) element.closest(".stage")?.scrollTo({ top: 0, behavior: "smooth" });
      },
    });
    choice.busy = false;
    card.paint();
  }

  // A finished task asks every page to read again. A run of this page's own reads the plan itself, so that signal is let pass meanwhile.
  const keeper = staleKeeper(element, () => (choice.busy ? plan : read()));
  // The folder changes outside this page, so every visit reads it again. What was chosen and typed stays.
  arrive = () => keeper.load();
  return { element, show: () => arrive() };
}
