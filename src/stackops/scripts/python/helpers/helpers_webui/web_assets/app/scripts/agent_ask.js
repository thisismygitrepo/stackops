import { h } from "/assets/scripts/dom.js";
import { briefingFor, describePlace } from "./agent_brief.js";
import { createCombo } from "./combo.js";
import { commandDetail } from "./data.js";
import { closeAll, openPopover } from "./overlays.js";
import { button, glyphTile } from "./widgets.js";

const AGENT_KEY = "stackops-webui-ask-agent";
const CHAT_PATH = "agents run-prompt";
const LABEL = "Ask an agent";
// What every place offers to start from, ahead of its own ideas.
const IDEAS = ["Explain what this is and how I use it", "What can I change here, and where is it kept?"];
// What was typed and not sent, by place: a click beside the box closes it, and the words are there again when it is opened.
const drafts = new Map();

// "Ask an agent": one button, the same wherever something can be set up, changed or explained. It opens a box for the request and starts a
// chat with a coding agent in the Activity panel, which is told where the button stands (agent_brief.js) before it reads the request.
// `place` says what the button stands beside, as an object or, where that changes (the tool on show, the script selected), as a function
// asked when the button is pressed.
// `small` is the button beside one thing on a page (a file's Edit, a row, a card): the same mark without the words, which the page's own
// button in its heading has already put a name to.
export function agentButton(activity, place, { small = false } = {}) {
  const control = button({
    label: small ? "" : LABEL, glyph: "sparkle", tone: "agent", small, title: `${LABEL}: it explains this, or makes the change for you. It is told where you are.`,
    onclick: () => openAsk(control, activity, typeof place === "function" ? place() : place),
  });
  control.setAttribute("aria-label", LABEL);
  return control;
}

function openAsk(anchor, activity, place) {
  const { title, where } = describePlace(place);
  let agent = localStorage.getItem(AGENT_KEY) ?? "";
  let launching = false;
  const box = h("textarea", { class: "text-input", rows: "3", placeholder: "What should it do, or explain?", "aria-label": "Your request", spellcheck: "true", value: drafts.get(where) ?? "" });
  const problem = h("span", { class: "tool-problem" });
  const send = button({ label: "Start chat", glyph: "chat", tone: "primary", small: true, title: "Enter starts it too. Shift and Enter make a new line.", onclick: start });
  // The agents are the ones the command takes. Nothing picked leaves the choice to the command, which uses the person's default agent.
  const picker = createCombo({
    label: "Agent", glyph: "bot", readOnly: true, placeholder: "Your default agent", emptyText: "The list of agents could not be read",
    suggest: async () => {
      const { parameters } = await commandDetail(CHAT_PATH);
      const names = (parameters ?? []).find((spec) => spec.name === "agent")?.choices ?? [];
      return names.length > 0 ? [{ value: "", label: "Your default agent" }, ...names.map((name) => ({ value: name, label: name }))] : [];
    },
    onPick(option) {
      agent = option.value;
      localStorage.setItem(AGENT_KEY, agent);
    },
  });
  picker.setValue(agent);
  const sync = () => {
    drafts.set(where, box.value);
    send.disabled = box.value.trim() === "";
  };

  async function start() {
    const request = box.value.trim();
    if (!request || launching) return;
    launching = true;
    try {
      await activity.start({
        title: `Ask an agent · ${title}`, emoji: "✨", interactive: true, reveal: true,
        arguments: [...CHAT_PATH.split(" "), "--interactive", ...(agent ? ["--agent", agent] : []), "--context", briefingFor(place), "--", request],
      });
      drafts.delete(where);
      // The chat is in the Activity panel, which a sheet or dialog would lie over: whatever the button stood in is put away with the box.
      closeAll();
    } catch (error) {
      launching = false;
      problem.textContent = error.message;
    }
  }

  // An idea that ends in "…" is the start of a sentence, so the cursor waits at its end; a whole one only needs Enter.
  const idea = (text) =>
    h("button", {
      class: "chip-button", type: "button", text,
      onclick: () => {
        box.value = text.replace(/…$/, "");
        box.focus();
        box.setSelectionRange(box.value.length, box.value.length);
        sync();
      },
    });
  box.addEventListener("input", sync);
  box.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
    event.preventDefault();
    start();
  });
  sync();
  openPopover(
    anchor,
    h(
      "div",
      { class: "agent-ask" },
      h("header", {}, glyphTile("sparkle", 252, 38), h("div", {}, h("h3", { text: LABEL }), h("p", { text: `About ${where}` }))),
      box,
      h("div", { class: "chip-row" }, [...(place.ideas ?? []), ...IDEAS].map(idea)),
      h("div", { class: "agent-ask-foot" }, picker.element, send),
      problem,
      h("p", { class: "agent-ask-note", text: "Opens a chat in the Activity panel, where you can go on talking. The agent is told where you are, and has StackOps' own guide to look the rest up in." }),
    ),
    // From the button's left edge, which keeps the box inside the sheet or dialog its button is in; near the window's edge it is moved in.
    { align: "start" },
  );
  box.focus();
}
