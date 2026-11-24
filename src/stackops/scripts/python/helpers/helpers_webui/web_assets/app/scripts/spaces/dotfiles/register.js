import { debounce, h, icon, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { createCombo } from "../../combo.js";
import { markStale } from "../../data.js";
import { openSheet } from "../../overlays.js";
import { button, emojiTile, field, segmented, textBox } from "../../widgets.js";
import { checkRegister } from "./api.js";
import { reasonOf, runBanner } from "./kit.js";
import { CONFLICTS, METHODS, METHOD_WORDS, STOPS, factsLine, outcomeCard, remarks } from "./register_words.js";
import { REGISTER_PATH } from "./words.js";

const CHECK_DELAY_MILLISECONDS = 250;
const SYSTEM_OF = { macOS: "darwin", Linux: "linux", Windows: "windows" };

// Add one file: a side sheet over the Dotfiles page. The file is typed or picked, and at once the sheet says what is there, whether it is
// managed already, where its copy will be kept and the entry that will be written. Adding runs the register command as a task out of sight.
// `preset` holds values by the command's parameter names.
export async function open({ activity, tools }, { preset }) {
  const sheet = openSheet({ label: "Add one file", wide: true });
  const systems = (await api.choices(REGISTER_PATH).catch(() => ({ fields: {} }))).fields.os_filter ?? { choices: [], labels: {} };
  const given = typeof preset.os_filter === "string" ? preset.os_filter.split(",").map((name) => name.trim()).filter((name) => systems.choices.includes(name)) : [];
  const choice = {
    file: preset.file ?? "", method: preset.method === "symlink" || preset.method === "s" ? "symlink" : "copy", systems: new Set(given.length > 0 ? given : systems.choices), group: preset.group ?? "", name: preset.name ?? "",
    destination: preset.destination ?? "", shared: Boolean(preset.shared), note: typeof preset.note === "string" ? preset.note : null, conflict: "",
  };
  let check = null;
  let failure = "";
  let ticket = 0;
  let busy = false;
  let outcome = null;

  const set = (key, value, wait = false) => {
    choice[key] = value;
    ask(wait);
  };
  const paths = (onlyFolders) => async (typed) => (await api.paths(typed || "~/", state.settings.workingDirectory)).entries.filter((entry) => !onlyFolders || entry.endsWith("/")).map((entry) => ({ value: entry, label: entry, keepOpen: entry.endsWith("/") }));
  const file = createCombo({ value: choice.file, label: "The file or folder", placeholder: "Type a path, or pick one", glyph: "folder", emptyText: "Nothing to suggest", suggest: paths(false), onInput: (typed) => set("file", typed, true), onPick: (option) => set("file", option.value) });
  const fileStatus = h("span", { class: "dotfiles-status" });
  const method = segmented(METHODS, (value) => set("method", value));
  const methodHint = h("span", { class: "field-hint" });
  const systemChips = systems.choices.map((name) =>
    h("button", {
      class: "chip-button", type: "button", text: `${systems.labels[name] ?? name}${SYSTEM_OF[state.boot.platform] === name ? " · this machine" : ""}`,
      onclick: () => (choice.systems.delete(name) || choice.systems.add(name), ask(false)),
    }),
  );
  const group = createCombo({
    value: choice.group, label: "Group", placeholder: "Default: default", emptyText: "Type a name to start a new group",
    suggest: (typed) => (check?.groups ?? []).filter((name) => name.toLowerCase().includes(typed.trim().toLowerCase())).map((name) => ({ value: name, label: name })),
    onInput: (typed) => set("group", typed, true),
    onPick: (option) => set("group", option.value),
  });
  const name = textBox(choice.name, { "aria-label": "Name on the list", oninput: () => set("name", name.value, true) });
  const destination = createCombo({ value: choice.destination, label: "Keep it somewhere else", placeholder: "Default: inside your dotfiles folder", glyph: "folder", emptyText: "Nothing to suggest", suggest: paths(true), onInput: (typed) => set("destination", typed, true), onPick: (option) => set("destination", option.value) });
  const shared = h("button", { class: "field toggle-row", type: "button", role: "switch", onclick: () => set("shared", !choice.shared) }, h("div", {}, h("span", { class: "field-label" }, h("span", { text: "In a folder named shared" })), h("span", { class: "field-hint", text: "Inside the place above, for a copy several setups use." })), h("i", { class: "switch" }));
  const note = textBox(choice.note ?? "", { "aria-label": "Note", oninput: () => set("note", note.value, true) });
  const conflict = createCombo({
    label: "Which one to keep", placeholder: `Default: ${CONFLICTS[0].label}`, readOnly: true,
    suggest: () => CONFLICTS.map((option) => ({ value: option.value, label: option.label, hint: option.value === CONFLICTS[0].value && "Default" })),
    onPick: (option) => ((choice.conflict = option.value === CONFLICTS[0].value ? "" : option.value), conflict.setValue(choice.conflict ? option.label : ""), paint()),
  });
  const conflictField = field("Both exist and differ. Which one to keep", conflict.element);
  const moreToggle = h("button", { class: "more-toggle", type: "button", "aria-expanded": "false" }, icon("sliders", 15), h("span", { text: "More options" }), icon("down", 14));
  const moreBody = h("div", { class: "more-body" }, h("div", { class: "fields" }, field("Keep it somewhere else", destination.element, "A folder of your choice in place of the usual one. The file keeps its name there."), shared, field("Note", note, "A line of your own, stored with the entry.")));
  moreToggle.addEventListener("click", () => {
    const open = moreToggle.getAttribute("aria-expanded") !== "true";
    moreToggle.setAttribute("aria-expanded", String(open));
    moreBody.classList.toggle("open", open);
  });
  const remarkHolder = h("div", { class: "dotfiles-remarks" });
  const outcomeHolder = h("div");
  const bannerHolder = h("div");
  const problem = h("span", { class: "dotfiles-problem" });
  const add = button({ label: "Add this file", glyph: "plus", tone: "primary", onclick: run });

  function problems() {
    if (choice.file.trim() === "") return ["Choose the file to add."];
    if (systems.choices.length > 0 && choice.systems.size === 0) return ["Choose at least one system."];
    if (failure) return [failure];
    if (!check) return ["Checking…"];
    return [check.list_problem && "Your list of managed files cannot be read, so nothing can be added to it.", STOPS[check.state], check.state === "conflict" && choice.conflict === "" && "Choose which one to keep."].filter(Boolean);
  }

  function paint() {
    method.set(choice.method);
    methodHint.textContent = METHOD_WORDS[choice.method];
    systemChips.forEach((chip, index) => chip.setAttribute("aria-pressed", String(choice.systems.has(systems.choices[index]))));
    shared.setAttribute("aria-checked", String(choice.shared));
    shared.hidden = choice.destination.trim() === "";
    name.placeholder = check ? `Default: ${choice.name.trim() === "" ? check.name : "from the file's name"}` : "Default: from the file's name";
    note.placeholder = check?.note && choice.note === null ? `Kept as it is: ${check.note}` : "Nothing";
    const line = check ? factsLine(check.file, check.kept) : { tone: failure ? "bad" : "", text: failure || (choice.file.trim() === "" ? "A settings file, or a whole folder of them." : "Checking…") };
    fileStatus.className = `dotfiles-status ${line.tone}`;
    fileStatus.textContent = line.text;
    conflictField.hidden = check?.state !== "conflict";
    remarkHolder.replaceChildren(...(check ? remarks(check) : []));
    outcomeHolder.replaceChildren(...(check ? [outcomeCard(check, choice)] : []));
    bannerHolder.replaceChildren(
      ...(outcome
        ? [
            runBanner({
              tone: outcome.done ? "good" : "bad", title: outcome.done ? `Added to your list as ${outcome.group} · ${outcome.name}` : "It was not added", text: outcome.done ? "The Dotfiles page shows it under Yours." : outcome.reason || "The console has the details.",
              actions: [!outcome.done && button({ label: "Show the console", glyph: "terminal", small: true, onclick: () => (sheet.close(), activity.reveal(outcome.id)) }), outcome.done && button({ label: "Done", small: true, onclick: () => sheet.close() })],
            }),
          ]
        : []),
    );
    const open = problems();
    problem.textContent = busy ? "Adding it…" : (open[0] ?? "");
    add.disabled = busy || open.length > 0;
  }

  // Whatever was found belongs to the values before the change, so it is dropped at once and asked for again.
  const askNow = async (mine) => {
    try {
      const found = await checkRegister({
        file: choice.file, method: choice.method, destination: choice.destination, shared: choice.shared ? "1" : "", name: choice.name, group: choice.group, os: [...choice.systems].join(","),
        ...(choice.note !== null && { note: choice.note }),
      });
      if (mine === ticket) check = found;
    } catch (error) {
      if (mine === ticket) failure = error.message;
    }
    if (mine === ticket) paint();
  };
  const askSoon = debounce(askNow, CHECK_DELAY_MILLISECONDS);
  function ask(wait) {
    ticket += 1;
    check = null;
    failure = "";
    outcome = null;
    if (choice.file.trim() !== "" && choice.systems.size > 0) (wait ? askSoon : askNow)(ticket);
    paint();
  }

  async function run() {
    if (busy || problems().length > 0) return;
    const asked = check;
    const runArguments = [
      "devops", "config", "dotfiles", "register", asked.file.path, "--method", choice.method, "--group", asked.group, "--name", asked.name, "--os", [...choice.systems].join(","),
      ...(choice.conflict ? ["--on-conflict", choice.conflict] : []), ...(choice.destination.trim() ? ["--destination", choice.destination.trim()] : []), ...(choice.shared && choice.destination.trim() ? ["--shared"] : []),
      ...(choice.note !== null ? ["--note", choice.note] : []),
    ];
    busy = true;
    paint();
    let task;
    try {
      task = await activity.start({ title: `Add ${asked.name} to dotfiles`, emoji: "📇", arguments: runArguments, interactive: false, reveal: false });
    } catch (error) {
      busy = false;
      paint();
      return toast(error.message);
    }
    const ended = await task.done;
    // A task that runs out of sight does not tell the pages to read again, and the list behind the sheet has one more entry now.
    markStale();
    busy = false;
    if (ended.exit_code === 0) {
      file.setValue("");
      choice.file = "";
      ask(false);
    }
    outcome = { done: ended.exit_code === 0, id: task.id, group: asked.group, name: asked.name, reason: ended.exit_code === 0 ? "" : reasonOf(task) };
    paint();
    sheet.body.scrollTo({ top: 0, behavior: "smooth" });
  }

  sheet.body.classList.add("dotfiles-sheet");
  sheet.body.append(
    ...[
    h("header", { class: "dotfiles-sheet-head" }, emojiTile(state.nodes.get(REGISTER_PATH)?.icon || "📇", REGISTER_PATH, 46), h("div", {}, h("h2", { text: "Add one file" }), h("p", { text: "Keep one more settings file in your dotfiles folder and on your list of managed files." }))),
    bannerHolder,
    h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "The file or folder" })), file.element, fileStatus),
    remarkHolder,
    h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "How it is kept" })), method.element, methodHint),
    systems.choices.length > 0 && h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "The systems it is for" })), h("div", { class: "chip-row" }, systemChips), h("span", { class: "field-hint", text: "On the others it is left alone when settings are applied." })),
    h("div", { class: "dotfiles-pair" }, field("Group", group.element, "Files that belong together are saved and applied together."), field("Name on the list", name)),
    conflictField,
    h("div", { class: "more" }, moreToggle, moreBody),
    outcomeHolder,
    ].filter(Boolean),
  );
  sheet.foot.hidden = false;
  sheet.foot.append(
    button({ label: "Every option", glyph: "sliders", tone: "ghost", title: "The command's own form, with everything it can do", onclick: () => (sheet.close(), tools.open(REGISTER_PATH, { plain: true, preset: { ...(choice.file.trim() && { file: choice.file.trim() }), method: choice.method, ...(choice.group.trim() && { group: choice.group.trim() }), ...(choice.name.trim() && { name: choice.name.trim() }) } })) }),
    h("span", { class: "spacer" }),
    problem,
    add,
  );
  ask(false);
  if (choice.file === "") file.input.focus();
}
