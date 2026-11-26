import { h, icon } from "/assets/scripts/dom.js";
import { query } from "../../data.js";
import { createPanel } from "../../live_panel.js";
import { toolButton } from "../../space_kit.js";
import { avatar, button, notice } from "../../widgets.js";
import { plural } from "../../words.js";
import { actionBlock, areaHead, barList, stateCard, statRow, tally } from "./workbench_kit.js";

const DAY = 86400000;
const WEEK = 7 * DAY;
const WEEKS = 12;
const FEED_LENGTH = 6;
const WRITER_LIMIT = 6;
const ACTIONS = [
  { path: "agents ask", title: "Ask your Second Brain", blurb: "Get an answer drawn from everything your agents have written down.", preset: { second_brain: "on" } },
  { path: "agents second-brain init", blurb: "Install the guide that tells agents how to keep the notebook. Yours is kept unless you choose to replace it." },
  { path: "agents second-brain prune", title: "Clean up unreadable entries", blurb: "See which entries can't be read, then choose whether to remove them.", caution: "Can delete entries" },
];

const dayOf = (text) => Date.parse(`${text}T00:00:00Z`);
const notebookOf = (path) => path.split("/").at(-2) ?? "";
// Agents sign their notes in many ways ("Codex/root", "codex:/root"); the first word is the agent.
const writerOf = (record) => record.followup_agent ?? record.agent.toLowerCase().match(/[a-z][a-z0-9-]*/)?.[0] ?? "unknown";

function whenText(day, today) {
  const age = Math.round((today - day) / DAY);
  if (age <= 0) return "today";
  if (age === 1) return "yesterday";
  if (age < 30) return `${age} days ago`;
  return new Date(day).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

function weekChart(notes, monday) {
  const counts = Array.from({ length: WEEKS }, () => 0);
  for (const note of notes) {
    const index = WEEKS - 1 - Math.max(Math.ceil((monday - note.day) / WEEK), 0);
    if (index >= 0) counts[index] += 1;
  }
  const top = Math.max(...counts, 1);
  const label = (index) => new Date(monday - (WEEKS - 1 - index) * WEEK).toLocaleDateString(undefined, { day: "numeric", month: "short", timeZone: "UTC" });
  return h(
    "figure",
    { class: "wb-weeks" },
    h("figcaption", { class: "stat-label", text: `Notes added each week, last ${WEEKS} weeks` }),
    h("div", { class: "wb-columns" }, counts.map((count, index) => h("span", { title: `Week of ${label(index)}: ${plural(count, "note")}` }, h("i", { style: `--share:${count / top};--i:${index}` })))),
    h("div", { class: "wb-axis dim" }, h("span", { text: label(0) }), h("span", { text: "this week" })),
  );
}

export function createBrainArea({ tools }, { setStatus, failStatus, ask: askAgent }) {
  let fromBrain = true;
  const question = h("input", { class: "wb-ask-input", type: "text", placeholder: "Ask a quick question…", "aria-label": "Your question", autocomplete: "off" });
  const toggle = h("button", { class: "mini-toggle", type: "button", role: "switch", "aria-checked": "true" }, h("i", { class: "switch" }), h("span", { text: "Answer from my Second Brain" }));
  const ask = () => tools.open("agents ask", { preset: { ...(question.value.trim() ? { prompt: question.value.trim() } : {}), ...(fromBrain ? { second_brain: "on" } : {}) } });
  // The sessions to pick from are the ones the notebook records; the command shows its own list of them once it starts.
  const resume = toolButton(tools, "agents run-interactive", { label: "Continue a session", glyph: "clock", preset: { followup: "on" } });
  function useBrain(wanted, available) {
    fromBrain = wanted && available;
    toggle.hidden = !available;
    if (resume) resume.hidden = !available;
    toggle.setAttribute("aria-checked", String(fromBrain));
  }
  toggle.addEventListener("click", () => useBrain(!fromBrain, true));
  question.addEventListener("keydown", (event) => event.key === "Enter" && ask());

  const panel = createPanel({
    title: "What's in the notebook", skeletonShape: "card", onFail: failStatus,
    load: async (fresh) => (await query(["agents", "second-brain", "status", "--json"], fresh)).json,
    explain: (error, { reload }) => {
      // Setting it up only makes the folder, and the status command also reads the folder's git history. Until it has one, this is the answer.
      const unversioned = /not a git repository/i.test(error.message);
      if (!unversioned && !/not available|agents\/second-brain\/?$/i.test(error.message)) return null;
      setStatus("Not set up", "");
      useBrain(false, false);
      if (unversioned) {
        return notice({
          glyph: "book", title: "The notebook has no history yet",
          body: "Its folder is there, but it is not a git repository yet, and the notebook keeps its history in one. Run “git init” in ~/code/agents/second-brain, then check again.",
          action: button({ label: "Check again", glyph: "refresh", small: true, onclick: reload }),
        });
      }
      return notice({
        glyph: "book", title: "Second Brain isn't set up yet",
        body: "It is a folder your agents share. Set it up once and they start writing down what they worked on, so the next one can pick up where the last stopped.",
        action: toolButton(tools, "agents second-brain init", { label: "Set up Second Brain", glyph: "plus", tone: "primary" }),
      });
    },
    render: (data, { setCount }) => {
      const files = data?.update_files ?? [];
      const today = dayOf(data.today);
      const monday = today - ((new Date(today).getUTCDay() + 6) % 7) * DAY;
      const notes = files.flatMap((file) => file.records.map((record) => ({ ...record, day: dayOf(record.updated_on), notebook: notebookOf(file.path), writer: writerOf(record) })));
      notes.sort((first, second) => second.day - first.day);
      const writers = tally(notes, (note) => note.writer);
      const unreadable = files.reduce((total, file) => total + file.invalid_rows.length, 0);
      const broken = files.filter((file) => file.error).length;
      const tree = data.git_activity.working_tree;
      const unsaved = tree.new_files + tree.changed_files + tree.deleted_files;
      const week = data.git_activity.this_week;
      setCount(`${plural(notes.length, "note")} · ${plural(files.length, "notebook")}`);
      setStatus(plural(notes.length, "note"), "good");
      if (toggle.hidden) useBrain(true, true);
      return h(
        "div",
        { class: "stack" },
        statRow([
          { glyph: "book", hue: 330, label: "Notes kept", value: notes.length, note: `across ${plural(files.length, "notebook")}` },
          { glyph: "clock", hue: 200, label: "Added this week", value: notes.filter((note) => note.day >= monday).length, note: `${notes.filter((note) => note.day >= today).length} of them today` },
          { glyph: "bot", hue: 262, label: "Agents writing", value: writers.length, note: writers.length ? `mostly ${writers[0].label}` : "none yet" },
          { glyph: "sync", hue: 32, label: "Waiting to be saved", value: unsaved, note: unsaved ? `${tree.new_files} new · ${tree.changed_files} changed · ${tree.deleted_files} removed` : "everything is in its history" },
        ]),
        (unreadable > 0 || broken > 0) &&
          stateCard({
            tone: "warn", glyph: "alert", title: broken ? `${plural(broken, "notebook")} can't be read at all` : `${unreadable} ${unreadable === 1 ? "entry is" : "entries are"} unreadable`,
            body: broken ? "Their layout is damaged and needs fixing by hand before anything can be cleaned up." : "They are missing details or have a date that makes no sense. Review them, then remove them if you agree.",
            actions: [toolButton(tools, "agents second-brain prune", { label: "Review cleanup", glyph: "search" })],
          }),
        h(
          "div",
          { class: "wb-split" },
          h(
            "div",
            { class: "wb-feed" },
            h("span", { class: "stat-label", text: "Latest notes" }),
            notes.length === 0 && h("p", { class: "wb-note", text: "Nothing has been written down yet." }),
            h("ul", {}, notes.slice(0, FEED_LENGTH).map((note) => h("li", { title: note.topic }, avatar(note.writer, 30), h("div", {}, h("strong", { text: note.topic }), h("span", { class: "dim", text: `${note.agent} · ${note.notebook}` })), h("span", { class: "dim", text: whenText(note.day, today) })))),
          ),
          h(
            "div",
            { class: "stack" },
            weekChart(notes, monday),
            writers.length > 0 && h("div", {}, h("span", { class: "stat-label", text: "Notes by agent" }), barList(writers.slice(0, WRITER_LIMIT))),
            h("p", { class: "wb-note", text: `Saved to its history ${week.commits === 1 ? "once" : `${week.commits} times`} this week, touching ${plural(week.files_changed, "file")}.` }),
          ),
        ),
      );
    },
  });

  const element = h(
    "div",
    { class: "wb-area" },
    areaHead({ ask: askAgent, title: "Second Brain", lede: "A shared notebook your agents keep: what they worked on and what they learned, ready for the next one — or for you to ask.", actions: [resume] }),
    h("div", { class: "wb-ask" }, icon("chat", 20), question, toggle, button({ label: "Ask", glyph: "sparkle", tone: "primary", onclick: ask })),
    panel.element,
    actionBlock(tools, "Look after it", ACTIONS),
  );
  return { element, show: () => panel.ensure() };
}
