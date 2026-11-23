import { h } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { createPanel } from "../../live_panel.js";
import { rise } from "../../motion.js";
import { editButton, toolButton } from "../../space_kit.js";
import { button } from "../../widgets.js";
import { actionBlock, areaHead, pathText, statusPill } from "./workbench_kit.js";
import { createResetPanel } from "./workbench_reset.js";

const KINDS = [
  { id: "prompts", title: "Saved prompts", body: "Instructions you reuse, ready to hand to any agent." },
  { id: "mcp", title: "Tool servers", body: "Extra tools an agent can be connected to." },
];
const PLACES = [
  { id: "workspace", title: "This project" },
  { id: "user", title: "Yours, everywhere" },
  { id: "library", title: "Built in" },
];
const VERDICTS = { ready: ["Ready", "good", "check"], missing: ["Not created", "", null], absent: ["No project here", "", null], broken: ["Needs fixing", "bad", "alert"] };
const ACTIONS = [
  { path: "agents init", blurb: "Add the instructions and settings your agents look for to a project folder." },
  { path: "agents config init", blurb: "Start a list of saved prompts or tool servers." },
  { path: "agents config validate", blurb: "Make sure a list is written correctly before an agent relies on it." },
  { path: "agents reset", blurb: "Remove what has been added to your agents. It only shows the plan, and removes nothing until you switch Apply on.", caution: "Permanent, no backup" },
];

async function inspect(kind, place, fresh) {
  const about = ["agents", "config"];
  try {
    const { text } = await query([...about, "validate", kind, "--source", place], fresh);
    return { kind, place, verdict: "ready", path: text.slice(text.indexOf(": ") + 2).trim() };
  } catch (error) {
    const located = await query([...about, "path", kind, "--source", place], fresh).then(({ json }) => json?.path ?? "", () => "");
    // The path lookup only works out where a list lives, so it fails only when that place is not there: "This project" outside of a project.
    return { kind, place, verdict: !located ? "absent" : /no such file/i.test(error.message) ? "missing" : "broken", path: located };
  }
}

export function createSetupArea({ activity, tools, openReport }, { setStatus, failStatus }) {
  function cell(check, kind, place) {
    const preset = { kind: check.kind, source: check.place };
    const broken = check.verdict === "broken";
    // Built-in lists stay read-only: a change made there is lost with the next update.
    const editable = check.verdict !== "missing" && check.place !== "library" && check.path;
    return h(
      "div",
      { class: `wb-list-cell ${check.verdict}` },
      h("div", { class: "wb-line" }, h("span", { class: "stat-label", text: place.title }), statusPill(...VERDICTS[check.verdict])),
      check.path && pathText(check.path),
      check.verdict === "missing" && check.place !== "library" && button({ label: "Create it", glyph: "plus", small: true, onclick: () => tools.open("agents config init", { preset }) }),
      (broken || editable) &&
        h(
          "span",
          { class: "wb-line-actions" },
          broken && button({ label: "See what's wrong", glyph: "search", small: true, onclick: () => tools.open("agents config validate", { preset }) }),
          editable && editButton(activity, { title: `${kind.title.toLowerCase()} (${place.title.toLowerCase()})`, kind: check.kind, path: check.path }, { label: broken ? "Fix it" : "Edit", small: true }),
        ),
    );
  }

  // The reset preview is asked for before the lists, here and on every refresh signal (panels answer that in the order they were made). The lists
  // start nine commands at once and a browser sends six requests at a time, so the one preview would otherwise wait behind them.
  const reset = createResetPanel({ tools, openReport });
  const lists = createPanel({
    title: "Lists your agents draw from", onFail: failStatus,
    load: (fresh) => Promise.all(KINDS.flatMap((kind) => PLACES.map((place) => inspect(kind.id, place.id, fresh)))),
    render: (checks, { setCount }) => {
      const ready = checks.filter((check) => check.verdict === "ready").length;
      const broken = checks.filter((check) => check.verdict === "broken").length;
      setCount(`${ready} of ${checks.length} ready`);
      setStatus(broken ? `${broken} ${broken === 1 ? "needs" : "need"} fixing` : `${ready} lists ready`, broken ? "bad" : "good");
      return rise(
        h(
          "div",
          { class: "wb-lists" },
          KINDS.map((kind) =>
            h(
              "div",
              { class: "wb-list-row" },
              h("div", { class: "wb-list-name" }, h("strong", { text: kind.title }), h("span", { class: "dim", text: kind.body })),
              PLACES.map((place) => cell(checks.find((check) => check.kind === kind.id && check.place === place.id), kind, place)),
            ),
          ),
        ),
      );
    },
  });

  const element = h(
    "div",
    { class: "wb-area" },
    areaHead({
      title: "Setup and cleanup", lede: "Get a project ready for agents, keep the lists they draw from in order, and see what a clean slate would remove.",
      actions: [toolButton(tools, "agents init", { label: "Set up a project", glyph: "plus", tone: "primary" })],
    }),
    lists.element,
    reset.element,
    actionBlock(tools, "Prepare and clean", ACTIONS),
  );
  return {
    element,
    show() {
      reset.ensure();
      lists.ensure();
    },
  };
}
