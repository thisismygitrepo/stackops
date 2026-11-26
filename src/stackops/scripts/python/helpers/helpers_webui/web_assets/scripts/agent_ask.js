import { briefingFor, describePlace } from "/assets/app/scripts/agent_brief.js";
import { h, icon, toast } from "./dom.js";
import { api, parseRoute, state } from "./state.js";

const CHAT = ["agents", "run-prompt", "--interactive"];
const PAGE = "Developer view";
const VIEWS = {
  home: ["Home", "The developer view's start: dashboards, quick actions and recent runs."],
  dashboards: ["Dashboards", "Reports that commands draw as pages, kept side by side."],
  map: ["Command map", "Every StackOps command drawn as a sunburst, a treemap or an icicle."],
  browse: ["All commands", "Every StackOps command, as a tree to browse."],
};

// Where the developer view is: the command or group in the address, or the view itself with every entry point behind it.
function placeNow() {
  const route = parseRoute();
  const node = route.view === "browse" ? state.nodes.get(route.path) : null;
  if (node && node.kind !== "root") return { page: PAGE, title: `stackops ${node.path}`, commands: [node.path] };
  const [title, about] = VIEWS[route.view];
  return { page: PAGE, title, about, commands: state.boot.tree.children.map((child) => child.path) };
}

// "Ask an agent" for the developer view, in its top bar: what the app view's button does (app/scripts/agent_ask.js), with this view's own
// controls. The agent is told which command or view is on show, and the chat opens in the terminal dock.
export function createAgentAsk({ dock }) {
  const box = h("textarea", { class: "input ask-box", rows: "3", placeholder: "What should it do, or explain?", "aria-label": "Your request", spellcheck: "true" });
  const agents = h("select", { class: "select", "aria-label": "Agent" }, h("option", { value: "", text: "your default agent" }));
  const send = h("button", { class: "button primary", type: "button", title: "Enter starts it too. Shift and Enter make a new line." }, icon("chat", 14), "Start chat");
  const about = h("span");
  const panel = h("div", { class: "ask-panel", role: "dialog", "aria-label": "Ask an agent", hidden: true }, h("p", { class: "ask-about" }, icon("sparkle", 14), about), box, h("div", { class: "ask-foot" }, agents, send));
  const button = h(
    "button",
    { class: "ask-button", type: "button", title: "Have a coding agent explain this, or make the change for you. It is told which command you are on." },
    icon("sparkle", 14),
    h("span", { text: "Ask an agent" }),
  );
  const element = h("div", { class: "ask" }, button, panel);
  let place = null;
  let launching = false;

  const sync = () => (send.disabled = box.value.trim() === "");
  const close = () => (panel.hidden = true);

  async function open() {
    place = placeNow();
    about.textContent = `About ${describePlace(place).where}`;
    panel.hidden = false;
    box.focus();
    sync();
    // The agents are the ones the command takes, read on the first opening. None picked leaves the choice to the command.
    if (agents.options.length > 1) return;
    const { parameters } = await api.command(CHAT.slice(0, 2).join(" "));
    const names = (parameters ?? []).find((spec) => spec.name === "agent")?.choices ?? [];
    if (agents.options.length === 1) agents.append(...names.map((name) => h("option", { value: name, text: name })));
  }

  async function start() {
    const request = box.value.trim();
    if (!request || launching) return;
    launching = true;
    try {
      await dock.start({ arguments: [...CHAT, ...(agents.value ? ["--agent", agents.value] : []), "--context", briefingFor(place), "--", request], interactive: true, reveal: true });
      box.value = "";
      close();
    } catch (error) {
      toast(error.message);
    }
    launching = false;
    sync();
  }

  button.addEventListener("click", () => (panel.hidden ? open() : close()));
  send.addEventListener("click", start);
  box.addEventListener("input", sync);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      close();
      button.focus();
    } else if (event.key === "Enter" && event.target === box && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      start();
    }
  });
  document.addEventListener("pointerdown", (event) => !panel.hidden && !element.contains(event.target) && close());
  // The box speaks of the place it was opened on, so it does not stay up over another one.
  window.addEventListener("hashchange", close);
  return { element };
}
