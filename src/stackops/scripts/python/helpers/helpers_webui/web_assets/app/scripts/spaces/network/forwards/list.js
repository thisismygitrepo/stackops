import { h, icon, toast } from "/assets/scripts/dom.js";
import { request } from "/assets/scripts/state.js";
import { confirmAction } from "../../../overlays.js";
import { button, copyChip, notice, pill, searchInput } from "../../../widgets.js";
import { plural, relativeTime } from "../../../words.js";
import { card, cardHead } from "../kit.js";
import { API } from "../words.js";

const ORIGINS = {
  stackops: { label: "Started by StackOps", tone: "accent" },
  switcher: { label: "Shows another machine here", tone: "" },
  other: { label: "Started outside StackOps", tone: "" },
};
const FILTERS = [["all", "All", () => true], ["stackops", "Started by StackOps", (forward) => forward.origin === "stackops"], ["other", "Everything else", (forward) => forward.origin !== "stackops"]];
const FILTER_FROM = 5;
const LOOPBACK = ["127.0.0.1", "localhost", "::1"];
const LOCAL_BROWSER = ["127.0.0.1", "localhost", "[::1]"].includes(location.hostname);
const OUTCOMES = { stopped: "The forward was stopped.", already_gone: "That forward had already ended.", still_running: "The forward did not stop in time. Stop it from the Processes page.", not_allowed: "This forward belongs to another account, so StackOps may not stop it.", failed: "The forward could not be stopped." };

// What stopping takes away, said before it happens. A forward StackOps started is only a forward, so it stops at one click.
function stopQuestion(forward) {
  if (forward.origin === "stackops") return null;
  if (forward.origin === "switcher") return `This is the connection that shows ${forward.destination} inside this app. Stopping it closes that machine's page.`;
  return `This ends an SSH connection to ${forward.destination} that was started outside StackOps. If a terminal session runs over the same connection, it ends too.`;
}

// Every `ssh` on this machine that forwards a port, whoever started it, newest first, each with a way to stop it.
export function createForwardList({ onStopped }) {
  let forwards = [];
  let filter = "all";
  let term = "";
  const count = h("span", { class: "count" });
  const search = searchInput({
    placeholder: "Filter forwards",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paintRows();
    },
  });
  const chips = h("div", { class: "chip-row" });
  const tools = h("div", { class: "network-toolbar", hidden: true }, chips, h("span", { class: "spacer" }), search.element);
  const list = h("ul", { class: "network-fwd-list" });

  async function stop(forward, control) {
    const question = stopQuestion(forward);
    if (question && !(await confirmAction({ title: "Stop this forward?", body: question, confirm: "Stop it", tone: "danger" }))) return;
    control.disabled = true;
    try {
      const { outcome } = await request("POST", `${API}/forwards/stop`, { pid: forward.pid, started: forward.started });
      toast(OUTCOMES[outcome], ["stopped", "already_gone"].includes(outcome) ? "info" : "error");
    } catch (error) {
      toast(error.message);
    }
    onStopped();
  }

  const row = (forward) =>
    h(
      "li",
      { class: "network-fwd-row" },
      h(
        "div",
        { class: "network-fwd-pairs" },
        forward.mappings.map((mapping) => {
          const address = `${mapping.listens_on.includes(":") ? `[${mapping.listens_on}]` : mapping.listens_on}:${mapping.local_port}`;
          return h(
            "div",
            { class: "network-fwd-pair" },
            copyChip(address),
            icon("arrow", 15),
            h("strong", { text: `${LOOPBACK.includes(mapping.remote_host) ? forward.destination : mapping.remote_host}:${mapping.remote_port}` }),
            !LOOPBACK.includes(mapping.listens_on) && h("span", { class: "pill warn", title: "It listens on every address of this machine, so other machines on the network can use it too", text: "Open to the network" }),
            LOCAL_BROWSER && ["127.0.0.1", "localhost"].includes(mapping.listens_on) && h("a", { class: "link network-fwd-open", href: `http://127.0.0.1:${mapping.local_port}`, target: "_blank", rel: "noopener noreferrer", title: "Opens it in a new tab, which works when a website answers there" }, "Open"),
          );
        }),
        h("div", { class: "network-fwd-meta" }, h("span", { text: `through ${forward.destination || "an unnamed machine"}` }), h("span", { text: `started ${relativeTime(forward.started)}` }), pill(ORIGINS[forward.origin].label, ORIGINS[forward.origin].tone)),
      ),
      button({ label: "Stop", glyph: "stop", small: true, title: "Ends this forward", onclick: (event) => stop(forward, event.currentTarget) }),
    );

  function paintRows() {
    const accepts = FILTERS.find(([id]) => id === filter)[2];
    const found = forwards.filter((forward) => accepts(forward) && `${forward.destination} ${forward.mappings.map((mapping) => `${mapping.local_port} ${mapping.remote_host} ${mapping.remote_port}`).join(" ")}`.toLowerCase().includes(term));
    list.replaceChildren(...(found.length ? found.map(row) : [h("li", {}, notice({ glyph: "search", title: "No forward matches", body: "Try another word, or show all of them." }))]));
  }

  function paint(next) {
    forwards = next;
    count.textContent = forwards.length ? plural(forwards.length, "forward") : "";
    tools.hidden = forwards.length < FILTER_FROM;
    if (tools.hidden) [filter, term, search.input.value] = ["all", "", ""];
    chips.replaceChildren(
      ...FILTERS.map(([id, label, accepts]) =>
        h(
          "button",
          {
            class: "chip-button", type: "button", "aria-pressed": String(id === filter),
            onclick: () => {
              filter = id;
              paint(forwards);
            },
          },
          h("span", { text: label }),
          h("b", { text: String(forwards.filter(accepts).length) }),
        ),
      ),
    );
    if (forwards.length === 0) list.replaceChildren(h("li", {}, notice({ glyph: "plug", title: "Nothing is being forwarded", body: "A forward started above, or with ssh -L in any terminal on this machine, shows up here." })));
    else paintRows();
  }

  return { element: card({ class: "network-fwd-running" }, cardHead("Running now", count), tools, list), paint };
}
