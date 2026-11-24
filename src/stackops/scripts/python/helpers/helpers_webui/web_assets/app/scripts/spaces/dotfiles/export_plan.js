import { debounce, h, icon } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { button, pathChip } from "../../widgets.js";
import { formatBytes, relativeTime } from "../../words.js";
import { checkExportPlace } from "./api.js";
import { passwordBox, revealToggle, stepTitle } from "./kit.js";
import { INSTALL_PATH, hostOptions } from "./words.js";

const PLACE_CHECK_MILLISECONDS = 250;
const WAYS = [
  { id: "file", glyph: "folder", title: "Keep it as a file", text: "You take it over yourself, on a stick, a shared drive or a cloud folder.", go: "Make the archive" },
  { id: "share", glyph: "globe", title: "Offer it on this network", text: "This machine hands the archive to whoever asks for it at its address, until you stop it. Only the password opens it.", go: "Make it and offer it" },
  { id: "ssh", glyph: "server", title: "Send it over SSH", text: "Copies the archive into the home folder of a machine this one can sign in to.", go: "Make it and send it" },
];

// Why a way cannot work on this machine, with the app that would fix it when there is one.
export function blockOf(way, plan) {
  if (way === "share" && !plan.share.tool_installed) return { text: "Needs miniserve, which is not installed here.", install: "miniserve" };
  if (way === "share" && plan.share.address === "") return { text: "This machine has no address on a local network." };
  if (way === "share" && !plan.share.port_free) return { text: `Port ${plan.share.port} is taken by another program on this machine.` };
  if (way === "ssh" && !plan.can_transfer) return { text: "The transfer tool that comes with StackOps was not found on this machine." };
  return null;
}

// The card beside the contents: how the archive gets to the other machine, its password, and where it is saved. `choice` is kept by the page,
// so what was chosen and typed outlives a fresh reading of the plan. `problems()` says what still stands in the way of making the archive.
export function createPlanCard({ choice, tools, onChange, onGo }) {
  let plan = null;
  let ticket = 0;
  const wayButtons = WAYS.map((way) =>
    h("button", { class: "dotfiles-way", type: "button", role: "radio", onclick: () => pick(way.id) }, h("span", { class: "dotfiles-way-glyph" }, icon(way.glyph, 18)), h("span", { class: "dotfiles-way-text" }, h("strong", { text: way.title }), h("span", { text: way.text }))),
  );
  const blocks = WAYS.map(() => h("p", { class: "dotfiles-block", hidden: true }));
  const machine = createCombo({
    value: choice.remote, label: "The machine to send it to", placeholder: "A machine from your SSH settings, or user@host", glyph: "server", emptyText: "No machine in your SSH settings. Type user@host.",
    suggest: (typed) => hostOptions(plan?.hosts ?? [], typed),
    onInput: (typed) => set("remote", typed),
    onPick: (option) => set("remote", option.value),
  });
  const machineField = h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "The machine to send it to" })), machine.element);
  const first = passwordBox({ label: "Password", placeholder: "Choose one for this archive", onInput: (typed) => set("password", typed) });
  const second = passwordBox({ label: "Once more", placeholder: "The same password again", onInput: (typed) => set("again", typed) });
  const placeNote = h("p", { class: "field-hint" });
  const placeLine = h("div", { class: "dotfiles-place" });
  const elsewhere = h("button", { class: "mini-toggle", type: "button", role: "switch", onclick: () => set("elsewhere", !choice.elsewhere) }, h("i", { class: "switch" }), h("span", { text: "Save it somewhere else" }));
  const output = createCombo({
    value: choice.output, label: "Where to save the archive", placeholder: "A file name that is not taken yet", glyph: "folder", emptyText: "Nothing to suggest",
    suggest: async (typed) => (await api.paths(typed || "~/", state.settings.workingDirectory)).entries.filter((entry) => entry.endsWith("/")).map((entry) => ({ value: entry, label: entry, keepOpen: true })),
    onInput: (typed) => place(typed),
    onPick: (option) => place(option.value),
  });
  const problem = h("p", { class: "dotfiles-problem" });
  const go = button({ label: WAYS[0].go, glyph: "lock", tone: "primary", onclick: () => onGo() });
  const protect = h("div", { class: "dotfiles-block", hidden: true }, h("span", { text: "GnuPG protects the archive, and it is not installed on this machine." }), button({ label: "Install GnuPG", glyph: "download", small: true, onclick: () => tools.open(INSTALL_PATH, { preset: { which: "gpg" } }) }));

  function set(key, value) {
    choice[key] = value;
    paint();
    onChange();
  }

  function pick(way) {
    if (plan && blockOf(way, plan)) return;
    set("way", way);
  }

  // What was found belongs to the text before the change, so it is dropped at once and the place is checked again.
  const lookSoon = debounce(async (mine) => {
    const found = await checkExportPlace(choice.output).catch(() => null);
    if (mine !== ticket) return;
    choice.place = found;
    paint();
    onChange();
  }, PLACE_CHECK_MILLISECONDS);
  function place(typed) {
    choice.output = typed;
    choice.place = null;
    ticket += 1;
    if (typed.trim() !== "") lookSoon(ticket);
    paint();
    onChange();
  }

  function problems() {
    if (!plan) return ["Reading this machine…"];
    const block = blockOf(choice.way, plan);
    return [
      !plan.can_protect && "GnuPG is not installed, so the archive cannot be protected.",
      block?.text,
      choice.way === "ssh" && choice.remote.trim() === "" && "Choose the machine to send it to.",
      choice.password === "" ? "Choose a password for the archive." : choice.password !== choice.again && "The two passwords are not the same.",
      choice.elsewhere && (choice.output.trim() === "" ? "Say where to save it, or switch that off." : choice.place === null ? "Checking that place…" : choice.place.taken && "Something is already at that place, and the command will not replace it. Choose another name."),
    ].filter(Boolean);
  }

  function paint() {
    if (!plan) return;
    WAYS.forEach((way, index) => {
      const block = blockOf(way.id, plan);
      wayButtons[index].setAttribute("aria-checked", String(choice.way === way.id));
      wayButtons[index].disabled = Boolean(block);
      blocks[index].hidden = !block;
      blocks[index].replaceChildren(...(block ? [h("span", { text: block.text }), ...(block.install ? [button({ label: `Install ${block.install}`, glyph: "download", small: true, onclick: () => tools.open(INSTALL_PATH, { preset: { which: block.install } }) })] : [])] : []));
    });
    machineField.hidden = choice.way !== "ssh";
    protect.hidden = plan.can_protect;
    elsewhere.setAttribute("aria-checked", String(choice.elsewhere));
    output.element.hidden = !choice.elsewhere;
    placeLine.replaceChildren(choice.elsewhere && choice.place ? pathChip(choice.place.path) : choice.elsewhere ? h("span", { class: "dim", text: "No place chosen yet" }) : pathChip(plan.archive.path));
    placeNote.textContent = choice.elsewhere
      ? "The command saves only to a place where nothing lies yet."
      : plan.archive.exists
        ? `An archive made ${relativeTime(plan.archive.modified_at)} is there already (${formatBytes(plan.archive.size_bytes)}). The new one replaces it.`
        : "Nothing is there yet.";
    const open = problems();
    problem.textContent = choice.busy ? "" : (open[0] ?? "");
    go.disabled = choice.busy || open.length > 0;
    go.querySelector("span").textContent = WAYS.find((way) => way.id === choice.way).go;
  }

  const element = h(
    "aside",
    { class: "dotfiles-card dotfiles-plan" },
    stepTitle(2, "How it gets there"),
    h("div", { class: "dotfiles-ways", role: "radiogroup", "aria-label": "How the archive gets to the other machine" }, WAYS.flatMap((_, index) => [wayButtons[index], blocks[index]])),
    machineField,
    stepTitle(3, "Protect it"),
    protect,
    h("div", { class: "dotfiles-passwords" }, first.element, second.element),
    revealToggle([first, second]),
    h("p", { class: "field-hint", text: "The archive is encrypted with this password. Nothing else opens it, so keep it where you can reach it from the other machine." }),
    stepTitle(4, "Where it is saved"),
    placeLine,
    placeNote,
    elsewhere,
    output.element,
    h("div", { class: "dotfiles-go" }, go, problem),
  );
  return {
    element, problems,
    show(next) {
      plan = next;
      if (blockOf(choice.way, plan)) choice.way = "file";
      paint();
    },
    // What the view was opened with, by the command's parameter names: the form of a switch that is on is any value at all.
    fill(preset) {
      if (preset.serve && !blockOf("share", plan)) choice.way = "share";
      if ((preset.ssh || preset.remote) && !blockOf("ssh", plan)) choice.way = "ssh";
      if (typeof preset.remote === "string") machine.setValue((choice.remote = preset.remote));
      if (typeof preset.output === "string" && preset.output.trim() !== "") {
        choice.elsewhere = true;
        output.setValue(preset.output);
        place(preset.output);
      }
      paint();
    },
    // The password is dropped from the boxes once it has been handed to the task.
    forget() {
      first.input.value = second.input.value = "";
      choice.password = choice.again = "";
      paint();
    },
    paint,
  };
}
