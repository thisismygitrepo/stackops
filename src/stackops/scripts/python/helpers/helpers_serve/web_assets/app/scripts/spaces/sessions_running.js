import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { markStale, query } from "../data.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { avatar, button, copyChip, iconButton, notice, pill, skeleton } from "../widgets.js";
import { plural, relativeTime } from "../words.js";

const EXPORTABLE = new Set(["tmux", "herdr", "tuios", "zellij"]);
const PANE_MOODS = { "idle-shell": ["Idle", ""], running: ["Busy", "good"], exited: ["Exited", "warn"] };

const panesOf = (record) =>
  record.panes.map((pane) => ({ name: `${pane.window_name} · pane ${pane.pane_index}`, folder: pane.cwd, runs: pane.process_name, mood: PANE_MOODS[pane.category], flag: "--pane-id", id: pane.pane_target }));

// What one session holds, from the record the CLI sends when asked about it: TUIOS lists windows, tmux and Zellij list panes.
// A design choice: Herdr and AoE rows do not open. Herdr passes its own records through as they are and AoE has nothing below a session.
const INSIDE = {
  tuios: {
    unit: "window",
    read: (record) =>
      record.windows.map((window) => ({
        name: window.display_name || `Window ${window.index}`, folder: window.cwd, runs: window.running_command || window.foreground_command,
        // Not strictly the CLI's idle test, which also inspects the window's processes: this is the part of it the record carries.
        mood: window.agent_state !== "none" ? [`Agent ${window.agent_state}`, "accent"] : window.running_command || window.at_prompt === false ? ["Busy", "good"] : window.at_prompt ? ["Idle", ""] : undefined,
        flag: "--window-id", id: window.window_id,
      })),
  },
  tmux: { unit: "pane", read: panesOf },
  zellij: { unit: "pane", read: panesOf },
};

export function createRunningPanel({ activity }) {
  // The detail element of each session left open, by session name. It outlives a reload of the panel, so an open session keeps showing what it
  // held until the new answer lands, instead of blanking to a skeleton each time.
  const opened = new Map();
  let busy = false;
  let asks = 0;
  let risen = false;

  // Runs out of sight and only opens the activity panel if it goes wrong. Quiet runs do not refresh the pages on their own, so this does.
  // One at a time: the panel shows as loading while one is going and a second press is ignored, so the same pane is not closed twice.
  // `ask` is the question to put first, where there is one.
  async function quietly({ ask, title, emoji, arguments: runArguments, done }) {
    if (busy || (ask && !(await confirmAction(ask)))) return;
    busy = true;
    panel.element.classList.add("loading");
    let run, outcome;
    try {
      run = await activity.start({ title, emoji, arguments: runArguments, interactive: false, reveal: false });
      outcome = await run.done;
    } finally {
      busy = false;
      panel.element.classList.remove("loading");
    }
    if (outcome.exit_code !== 0) return activity.reveal(run.id);
    activity.remove(run.id);
    toast(done, "info");
    markStale();
  }

  async function end(session, backend) {
    const sure = await confirmAction({ title: `End “${session.name}”?`, body: "Everything running inside this session stops. This cannot be undone.", confirm: "End session", tone: "danger" });
    if (sure) await activity.start({ title: `End ${session.name}`, emoji: "💀", arguments: ["terminal", "kill", session.name, "--backend", backend], interactive: true, reveal: true });
  }

  // Whether a layout gets replaced is asked of the CLI at the moment of saving, not read off the Saved layouts panel: that panel may be showing
  // another source, or be out of date. Not strictly complete: the list command fails while there is no layouts file yet, and any failure of it
  // is read as nothing to replace.
  async function save(session, backend) {
    if (busy) return;
    const [path, replaces] = await Promise.all([
      query(["terminal", "path"]),
      query(["terminal", "list", "--json", "--source", "user"], true).then(({ json }) => json.layouts.some((layout) => layout.name === session.name), () => false),
    ]);
    await quietly({
      ask: replaces && { title: `Replace the layout “${session.name}”?`, body: "One of your saved layouts already has this name. Saving again replaces it with what the session holds now.", confirm: "Replace" },
      title: `Save ${session.name} as a layout`, emoji: "💾", arguments: ["terminal", "export", "--sessions", session.name, "--output", path.json.user.path, "--merge", "--backend", backend], done: `Saved “${session.name}” to your layouts.`,
    });
  }

  // Fills `holder` with what the session holds. The holder may already show an earlier answer, which stays until this one lands; an answer that a
  // newer request for the same holder has overtaken is dropped.
  function inside(session, backend, holder) {
    const { unit, read } = INSIDE[backend];
    const mine = (holder.dataset.ask = String((asks += 1)));
    const scope = ["terminal", "kill", session.name, "--backend", backend];
    const closeIdle = () =>
      quietly({
        ask: { title: `Close what is idle in “${session.name}”?`, body: `Every ${unit} sitting at an empty prompt is closed. If all of them are idle, the session ends.`, confirm: "Close idle ones", tone: "danger" },
        title: `Tidy ${session.name}`, emoji: "🧹", arguments: [...scope, "--idle"], done: `Closed what was idle in “${session.name}”.`,
      });
    const close = (item) =>
      quietly({
        ask: { title: `Close “${item.name}”?`, body: `Whatever is running in this ${unit} stops. This cannot be undone.`, confirm: `Close ${unit}`, tone: "danger" },
        title: `Close ${item.name}`, emoji: "✖️", arguments: [...scope, item.flag, item.id], done: `Closed “${item.name}”.`,
      });
    query(["terminal", "summary", "--json", "--session", session.name, "--backend", backend], true).then(
      ({ json }) => {
        if (holder.dataset.ask !== mine) return;
        const items = read(json.sessions[0]);
        holder.replaceChildren(
          h("div", { class: "session-inside-head" }, h("span", { class: "dim", text: plural(items.length, unit) }), button({ label: "Close idle ones", small: true, tone: "ghost", onclick: closeIdle })),
          h(
            "ul",
            {},
            items.map((item) =>
              h(
                "li",
                {},
                h("strong", { text: item.name }),
                h("code", { text: item.runs }),
                item.mood && pill(...item.mood),
                item.folder && copyChip(item.folder, tildify(item.folder, state.boot.home)),
                h("button", { class: "icon-btn danger", type: "button", title: `Close this ${unit}`, "aria-label": `Close ${item.name}`, onclick: () => close(item) }, icon("close", 14)),
              ),
            ),
          ),
        );
      },
      (error) => holder.dataset.ask === mine && holder.replaceChildren(h("p", { class: "dim", text: error.message })),
    );
  }

  // Each backend reports different facts about a session, so a row shows what its record carries instead of expecting one shape.
  function row(session, backend) {
    const measured = typeof session.running === "number" && typeof session.idle === "number";
    const total = Math.max(session.running + session.idle + (session.unknown ?? 0) + (session.exited ?? 0), 1);
    const inUse = session.attached ?? session.focused;
    const facts = [
      typeof session.window_count === "number" && plural(session.window_count, "window"),
      typeof session.tab_count === "number" && plural(session.tab_count, "tab"),
      typeof session.pane_count === "number" && plural(session.pane_count, "pane"),
      session.agent_count > 0 && plural(session.agent_count, "agent"),
      session.last_active && `active ${relativeTime(session.last_active)}`,
      session.agent,
      session.group,
    ];
    const line = h(
      "div",
      { class: "session-row" },
      avatar(session.name, 40),
      h("div", { class: "session-text" }, h("strong", { text: session.name }), h("span", { class: "dim", text: facts.filter(Boolean).join(" · ") })),
      measured && h("div", { class: "meter", title: `${session.running} busy, ${session.idle} idle` }, h("i", { class: "busy", style: `--share:${session.running / total}` }), h("i", { class: "idle", style: `--share:${session.idle / total}` })),
      measured && h("span", { class: "session-counts dim" }, `${session.running} busy · ${session.idle} idle`),
      typeof inUse === "boolean" ? pill(inUse ? "In use" : "In background", inUse ? "good" : "") : session.status && pill(session.status),
      iconButton("terminal", "Open this session here", () => activity.start({ title: `Session ${session.name}`, emoji: "📎", arguments: ["terminal", "attach", session.name, "--backend", backend], interactive: true, reveal: true, wide: true })),
      EXPORTABLE.has(backend) && iconButton("layers", "Save as a layout", () => save(session, backend)),
      h("button", { class: "icon-btn danger", type: "button", title: "End this session", "aria-label": `End ${session.name}`, onclick: () => end(session, backend) }, icon("stop", 15)),
    );
    const item = h("li", {}, line);
    if (!INSIDE[backend]) return item;
    const open = (holder) => {
      opened.set(session.name, holder);
      inside(session, backend, holder);
      item.append(holder);
      line.setAttribute("aria-expanded", "true");
    };
    const toggle = () => {
      const holder = opened.get(session.name);
      if (!holder) return open(h("div", { class: "session-inside" }, skeleton(2, "row")));
      holder.remove();
      opened.delete(session.name);
      line.setAttribute("aria-expanded", "false");
    };
    line.classList.add("opens");
    line.tabIndex = 0;
    line.title = "See what is inside";
    line.setAttribute("aria-expanded", "false");
    line.addEventListener("click", (event) => !event.target.closest("button") && toggle());
    // A design choice: the row takes Enter and Space like a button but is not given that role, because it holds real buttons of its own and a
    // screen reader hides what is inside a button.
    line.addEventListener("keydown", (event) => {
      if (event.target !== line || (event.key !== "Enter" && event.key !== " ")) return;
      event.preventDefault();
      toggle();
    });
    const kept = opened.get(session.name);
    if (kept) {
      // Its fade-in is for a session being opened, not for one that stayed open across a reload.
      kept.style.animation = "none";
      open(kept);
    }
    return item;
  }

  const panel = createLivePanel({
    title: "Running now", path: "terminal summary", extra: ["--json"], locked: ["session", "choose_session", "show_tabs"],
    render: (data, { setCount }) => {
      const sessions = data?.sessions ?? [];
      setCount(sessions.length ? `${plural(sessions.length, "session")} · ${data.backend}` : "");
      if (sessions.length === 0) return notice({ glyph: "layers", title: "Nothing is running", body: "Launch a layout above to start a session." });
      const list = h("ul", { class: "session-list" }, sessions.map((session) => row(session, data.backend)));
      // A design choice: the rows rise once, on arrival. This panel reloads after every pane it closes, and rising each time made the list blink.
      if (!risen) rise(list);
      risen = true;
      return list;
    },
  });
  return panel;
}
