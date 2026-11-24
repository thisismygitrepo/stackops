import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { button, segmented, textBox } from "../../widgets.js";
import { formatBytes, relativeTime } from "../../words.js";
import { receiveArchive } from "./api.js";
import { passwordBox, revealToggle, stepTitle } from "./kit.js";
import { INSTALL_PATH, hostOptions } from "./words.js";

const FROM = [["file", "An archive file"], ["address", "A machine offering it"], ["ssh", "Straight over SSH"]];

// The card beside the listing: where the settings come from and, for an archive, its password. `choice` is kept by the page. `onLook` asks
// for the look inside, `onCopy` for the copy over SSH, and `onReceived` says an archive was saved on this machine and the list is out of date.
export function createSourceCard({ choice, tools, onChange, onLook, onCopy, onReceived }) {
  let machine = null;
  const set = (key, value) => {
    choice[key] = value;
    paint();
    onChange();
  };
  const picker = segmented(FROM, (value) => set("from", value));
  const found = h("div", { class: "dotfiles-archives", role: "radiogroup", "aria-label": "Archives in the home folder" });
  const typed = createCombo({
    value: choice.source, label: "Where the archive is", placeholder: "Or type where the archive is", glyph: "folder", emptyText: "Nothing to suggest",
    suggest: async (text) => (await api.paths(text || "~/", state.settings.workingDirectory)).entries.map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") })),
    onInput: (text) => set("source", text),
    onPick: (option) => set("source", option.value),
  });
  const chooser = h("input", { type: "file", hidden: true, onchange: () => chooser.files[0] && receive(chooser.files[0]) });
  const drop = h("button", { class: "dotfiles-drop", type: "button", onclick: () => chooser.click() }, icon("download", 18), h("span", {}, h("strong", { text: "Drop the archive here, or choose it" }), h("span", { text: "It is saved in the home folder of the machine this page shows." })));
  drop.addEventListener("dragover", (event) => {
    event.preventDefault();
    drop.classList.add("over");
  });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (event) => {
    event.preventDefault();
    drop.classList.remove("over");
    if (event.dataTransfer.files[0]) receive(event.dataTransfer.files[0]);
  });
  const address = textBox(choice.address, { placeholder: "http://192.168.1.20:8888", "aria-label": "The address the other machine shows", oninput: () => set("address", address.value) });
  const remote = createCombo({
    value: choice.remote, label: "The machine to copy from", placeholder: "A machine from your SSH settings, or user@host", glyph: "server", emptyText: "No machine in your SSH settings. Type user@host.",
    suggest: (text) => hostOptions(machine?.hosts ?? [], text),
    onInput: (text) => set("remote", text),
    onPick: (option) => set("remote", option.value),
  });
  const password = passwordBox({ label: "Password", placeholder: "The one set when the archive was made", onInput: (text) => set("password", text) });
  password.input.autocomplete = "off";
  password.input.addEventListener("keydown", (event) => event.key === "Enter" && !look.disabled && onLook());
  const protect = h("div", { class: "dotfiles-block", hidden: true }, h("span", { text: "GnuPG opens the archive, and it is not installed on this machine." }), button({ label: "Install GnuPG", glyph: "download", small: true, onclick: () => tools.open(INSTALL_PATH, { preset: { which: "gpg" } }) }));
  const problem = h("p", { class: "dotfiles-problem" });
  const look = button({ label: "Look inside", glyph: "eye", tone: "primary", onclick: () => onLook() });
  const copy = button({ label: "Copy from that machine", glyph: "download", tone: "primary", onclick: () => onCopy() });
  const panes = {
    file: h("div", { class: "dotfiles-pane" }, found, typed.element, drop, chooser),
    address: h("div", { class: "dotfiles-pane" }, address, h("p", { class: "field-hint", text: "The other machine shows this address while it offers its archive. Both have to be on the same network." })),
    ssh: h("div", { class: "dotfiles-pane" }, remote.element, h("p", { class: "field-hint", text: "This machine signs in to the other one and copies its dotfiles folder over this one. There is no archive and no password for one, and nothing can be shown first." })),
  };
  const secret = h("div", { class: "dotfiles-pane" }, stepTitle(2, "Its password"), protect, password.element, revealToggle([password]));

  async function receive(file) {
    drop.classList.add("busy");
    try {
      const saved = await receiveArchive(file);
      typed.setValue("");
      choice.source = saved.path;
      await onReceived();
    } catch (error) {
      toast(error.message);
    }
    drop.classList.remove("busy");
    paint();
    onChange();
  }

  // What is looked into or fetched: the archive that is picked or typed, or the address.
  const sourceOf = () => (choice.from === "address" ? choice.address.trim() : choice.source.trim());
  function problems() {
    if (!machine) return ["Reading this machine…"];
    if (choice.from === "ssh") return [!machine.can_transfer && "The transfer tool that comes with StackOps was not found on this machine.", choice.remote.trim() === "" && "Choose the machine to copy from."].filter(Boolean);
    return [
      !machine.can_protect && "GnuPG is not installed, so the archive cannot be opened.",
      sourceOf() === "" && (choice.from === "address" ? "Type the address the other machine shows." : "Choose the archive."),
      choice.from === "address" && sourceOf() !== "" && !/^https?:\/\/\S+$/.test(sourceOf()) && "The address starts with http:// or https://.",
      choice.password === "" && "Type the archive's password.",
    ].filter(Boolean);
  }

  function paint() {
    if (!machine) return;
    picker.set(choice.from);
    for (const [name, pane] of Object.entries(panes)) pane.hidden = name !== choice.from;
    secret.hidden = choice.from === "ssh";
    protect.hidden = machine.can_protect;
    found.replaceChildren(
      ...(machine.archives.length > 0
        ? machine.archives.map((archive) =>
            h(
              "button",
              { class: "dotfiles-archive", type: "button", role: "radio", "aria-checked": String(choice.source === archive.path), onclick: () => (typed.setValue(""), set("source", archive.path)) },
              icon("lock", 16), h("strong", { text: tildify(archive.path, state.boot.home) }), h("span", { class: "dim", text: `${formatBytes(archive.size_bytes)} · ${relativeTime(archive.modified_at)}` }),
            ),
          )
        : [h("p", { class: "field-hint", text: "No archive lies in this machine's home folder yet. Make one on the other machine with Move to a new machine, then bring it here." })]),
    );
    const open = problems();
    problem.textContent = choice.busy ? "" : (open[0] ?? "");
    look.hidden = choice.from === "ssh";
    copy.hidden = choice.from !== "ssh";
    look.disabled = copy.disabled = choice.busy || open.length > 0;
  }

  const element = h("aside", { class: "dotfiles-card dotfiles-plan" }, stepTitle(1, "Where it comes from"), picker.element, Object.values(panes), secret, h("div", { class: "dotfiles-go" }, look, copy, problem));
  return {
    element, problems, sourceOf, paint,
    show(next) {
      machine = next;
      // With nothing chosen yet, the newest archive in the home folder is: the usual case is then one password and one click.
      if (choice.source === "" && machine.archives.length > 0) choice.source = machine.archives[0].path;
      paint();
    },
    fill(preset) {
      if (preset.ssh || preset.remote) choice.from = "ssh";
      if (typeof preset.remote === "string") remote.setValue((choice.remote = preset.remote));
      if (typeof preset.url === "string" && /^https?:\/\//.test(preset.url)) address.value = choice.address = preset.url.trim();
      else if (typeof preset.url === "string" && preset.url.trim() !== "") typed.setValue((choice.source = preset.url.trim()));
      if (typeof preset.url === "string") choice.from = /^https?:\/\//.test(preset.url) ? "address" : "file";
      paint();
    },
    forget() {
      password.input.value = "";
      choice.password = "";
      paint();
    },
  };
}
