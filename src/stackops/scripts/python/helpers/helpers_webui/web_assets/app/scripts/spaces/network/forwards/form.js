import { debounce, h, icon, toast } from "/assets/scripts/dom.js";
import { api, request } from "/assets/scripts/state.js";
import { createCombo } from "../../../combo.js";
import { capture } from "../../../data.js";
import { button, field, textBox } from "../../../widgets.js";
import { card, cardHead, choiceCards } from "../kit.js";
import { API, PATHS } from "../words.js";

const SUGGESTION_LIMIT = 40;
const PORT_CHECK_MILLISECONDS = 300;
const WAYS = [
  ["task", "Watch it run (the default)", "Runs as a task in the Activity panel, where it can ask for a password. It ends when you stop the task or close StackOps."],
  ["background", "Keep it running", "Starts it and lets go of it. It keeps forwarding after StackOps is closed, until you stop it in the list below or the machine restarts. It cannot ask for a password, so the other machine has to accept your key."],
];
const portOf = (text) => (/^\d{1,5}$/.test(text.trim()) && Number(text) >= 1 && Number(text) <= 65535 ? Number(text) : null);

// A new forward: the machine is a pick from the SSH config (or any name typed), the ports are two boxes, and a small map with a sentence
// under it says what will be reachable where before anything starts.
export function createForwardForm({ activity, onStarted, preset }) {
  let hosts = [];
  let way = "task";
  let free = null;
  let ticket = 0;
  let starting = false;

  const machine = createCombo({
    value: preset.destination ?? "", placeholder: "Pick a machine, or type user@host", glyph: "server", label: "Machine",
    emptyText: "No machine in your SSH config matches. What you typed is used as it is.",
    suggest: async (term) => {
      const wanted = term.trim().toLowerCase();
      return hosts.filter((host) => `${host.name} ${host.address}`.toLowerCase().includes(wanted)).slice(0, SUGGESTION_LIMIT).map((host) => ({ value: host.name, hint: host.address }));
    },
    onInput: () => paint(),
    onPick: () => paint(),
  });
  const there = textBox(preset.remote_port ?? "", { inputmode: "numeric", placeholder: "5432", "aria-label": "Port on the other machine", oninput: () => changed() });
  const here = textBox(preset.local_port ?? "", { inputmode: "numeric", placeholder: "Same", "aria-label": "Port on this machine", oninput: () => changed() });
  const map = h("div", { class: "network-fwd-map" });
  const sentence = h("p", { class: "network-fwd-sentence" });
  const portNote = h("p", { class: "network-fwd-port" });
  const problem = h("p", { class: "network-key-bad", hidden: true });
  const start = button({ label: "Start forwarding", glyph: "play", tone: "primary", onclick: submit });
  const ways = choiceCards(WAYS, { value: way, onPick: (id) => (way = id) });

  const read = () => {
    const remote = portOf(there.value);
    const local = here.value.trim() === "" ? remote : portOf(here.value);
    return { host: machine.input.value.trim(), remote, local };
  };

  function paint() {
    const { host, remote, local } = read();
    const node = (glyph, title, port, side) => h("div", { class: `network-fwd-node ${side}` }, icon(glyph, 20), h("strong", { text: title }), h("code", { text: port }));
    map.replaceChildren(
      node("monitor", "This machine", `127.0.0.1:${local ?? "?"}`, "here"),
      h("div", { class: "network-fwd-wire" }, h("span", { text: "through SSH" }), h("i")),
      node("server", host || "The other machine", `port ${remote ?? "?"}`, "there"),
    );
    sentence.textContent =
      host && remote && local
        ? `Whatever answers on port ${remote} on ${host} will answer at 127.0.0.1:${local} on this machine, for as long as the forward runs. Nothing outside this machine can reach it.`
        : "Pick the machine and the port its service listens on. The forward makes that port answer on this machine.";
    portNote.className = `network-fwd-port ${free === null ? "" : free.free ? "good" : "bad"}`;
    portNote.replaceChildren(...(free === null || local === null ? [] : [icon(free.free ? "check" : "alert", 14), h("span", { text: free.free ? `Port ${local} is free on this machine.` : `Port ${local} cannot be used here. ${free.reason} Pick another port for this machine.` })]));
    const badPort = (there.value.trim() !== "" && remote === null) || (here.value.trim() !== "" && local === null);
    problem.hidden = !badPort;
    problem.textContent = badPort ? "A port is a number between 1 and 65535." : "";
    start.disabled = starting || !host || !remote || !local || free?.free === false;
  }

  // The port on this machine is asked about the way the command asks before it starts, so a clash shows here and not as a failed run.
  const checkPort = debounce(async () => {
    const mine = (ticket += 1);
    const { local } = read();
    const answer = local === null ? null : await request("GET", `${API}/forwards/port?port=${local}`).catch(() => null);
    if (mine !== ticket) return;
    free = answer;
    paint();
  }, PORT_CHECK_MILLISECONDS);

  function changed() {
    free = null;
    paint();
    checkPort();
  }

  // A background forward that failed says only where its log is. The log's last line is the other machine's own reason, so that is shown.
  async function explain(error) {
    const log = /see (\S+\.log)/.exec(error.message)?.[1];
    const text = log ? await api.file(log).then((file) => file.text, () => "") : "";
    const last = text.split("\n").map((line) => line.trim()).filter(Boolean).at(-1);
    return last ? `The forward did not start. SSH said: ${last}` : error.message;
  }

  async function submit() {
    const { host, remote, local } = read();
    if (starting || !host || !remote || !local) return;
    starting = true;
    paint();
    // Options first, then `--`: what was typed as the machine is always read as its name, even when it starts with a dash.
    const run = [...PATHS.mapPort.split(" "), "--local-port", String(local), ...(way === "background" ? ["--background", "--json"] : []), "--", host, String(remote)];
    try {
      if (way === "background") {
        const { json } = await capture(run);
        toast(`Forwarding. Port ${remote} on ${host} now answers at ${json?.url ?? `127.0.0.1:${local}`}.`, "info");
        onStarted({ wait: false });
      } else {
        const task = await activity.start({ title: `Forward ${host}:${remote}`, emoji: "🔀", arguments: run, interactive: true, reveal: true });
        onStarted({ wait: true });
        task.done.then(() => onStarted({ wait: false }));
      }
    } catch (error) {
      toast(way === "background" ? await explain(error) : error.message);
    } finally {
      starting = false;
      changed();
    }
  }

  const element = card(
    { class: "network-fwd-form" },
    cardHead("New forward"),
    h("div", { class: "network-fwd-fields" }, field("Machine", machine.element), field("Port there", there, "Where its service listens."), field("Port here", here, "Default: the same number.")),
    problem,
    map,
    sentence,
    portNote,
    ways.element,
    h("div", { class: "network-card-actions" }, start),
  );
  paint();
  if (read().local) checkPort();

  return {
    element,
    setHosts(next) {
      hosts = next;
      machine.input.placeholder = hosts.length ? `Pick one of ${hosts.length.toLocaleString()} machines, or type user@host` : "Type a machine, such as user@host";
    },
    adopt(given) {
      if (given.destination) machine.setValue(given.destination);
      if (given.remote_port) there.value = given.remote_port;
      if (given.local_port) here.value = given.local_port;
      changed();
    },
    disable(why) {
      for (const control of element.querySelectorAll("input, button")) control.disabled = true;
      sentence.textContent = why;
    },
  };
}
