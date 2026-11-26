import { h } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { PLACES } from "../../agent_places.js";
import { markStale } from "../../data.js";
import { confirmAction, openSheet } from "../../overlays.js";
import { button, emojiTile, notice, pathChip, sectionHead, segmented, skeleton } from "../../widgets.js";
import { plural, titleOf } from "../../words.js";
import { createPickList } from "./copy_list.js";
import { createTargetField } from "./copy_target.js";
import { copyLogins } from "./file_api.js";
import { busyButton, loadProblem, mark } from "./tools_kit.js";
import { kindOf, placeLabel, valueCount } from "./words.js";

const PATH = "devops vault subset";
const NEW_FILE = "~/vault-copy.json";
const CONFLICTS = { append: "append", a: "append", overwrite: "overwrite", o: "overwrite" };
const SOURCES = { workspace: "workspace", w: "workspace", user: "user", u: "user" };

// Copy part of the vault, as a side sheet: a job with a start and an end, done over the list it started from. Logins are chosen from their labels;
// no value is read into the page. A copy from a file of the person's own choosing goes to the command's own form.
export function open({ activity, tools }, { preset = {} }) {
  if (preset.custom_path) return tools.open(PATH, { plain: true, preset });
  const node = state.nodes.get(PATH);
  const sheet = openSheet({ label: titleOf(node), wide: true });
  const chosen = new Set();
  let sources = [];
  // The paths of every vault file the Vault page lists, to tell a copy into one of them from a copy to somewhere else.
  let listed = [];
  let source = null;

  const body = h("div", { class: "vault-copy-body" }, skeleton(4, "row"));
  const from = h("div", { class: "vault-copy-from" });
  const count = h("span", { class: "count" });
  const tally = h("span", { class: "vault-copy-tally" });
  const problem = h("span", { class: "tool-problem", role: "alert" });
  // The button is set again once it has let go: whether a copy can be made is this sheet's to say, not the button's.
  const go = busyButton({ label: "Copy", glyph: "copy", tone: "primary" }, () => copy().finally(() => setTimeout(paintFoot)));
  const list = createPickList({ chosen, onChange: paintFoot });
  const target = createTargetField({ path: typeof preset.output_path === "string" && preset.output_path ? preset.output_path : NEW_FILE, conflict: CONFLICTS[preset.on_conflict] ?? "", onChange: paintFoot });
  sheet.body.append(
    h("header", { class: "tool-head" }, emojiTile(node.icon || "📦", node.path, 56), h("div", {}, h("span", { class: "overline", text: "Vault" }), h("h1", { text: titleOf(node) }), h("p", { text: "Write the logins you choose, with their secrets and values, to another vault file. Nothing leaves this one." }))),
    body,
  );
  sheet.foot.append(agentButton(activity, { ...PLACES.vault, title: titleOf(state.nodes.get(PATH)), commands: [PATH], about: "Copies the logins a person ticks from one vault file into another." }), tally, problem, button({ label: "All options", glyph: "sliders", tone: "ghost", title: "The command's own form, with every option it has", onclick: () => tools.open(PATH, { plain: true }) }), button({ label: "Cancel", onclick: () => sheet.close() }), go);

  const picked = () => source.logins.filter((login) => chosen.has(login.index));

  function paintFoot() {
    if (!source) return;
    const logins = picked();
    const where = target.read();
    count.textContent = `${logins.length} of ${source.logins.length} chosen`;
    tally.textContent = logins.length > 0 ? `${plural(logins.length, "login")} · ${plural(logins.reduce((total, login) => total + login.secrets.length, 0), "secret")} · ${plural(logins.reduce((total, login) => total + valueCount(login), 0), "value")}` : "";
    go.querySelector("span").textContent = logins.length > 0 ? `Copy ${plural(logins.length, "login")}` : "Copy";
    go.disabled = logins.length === 0 || !where.ready;
    go.title = logins.length === 0 ? "Tick the logins to copy first." : where.why;
  }
  // What went wrong with the last try stays until the person does something about it.
  for (const kind of ["input", "click"]) body.addEventListener(kind, () => (problem.textContent = ""));

  function pick(name) {
    source = sources.find((candidate) => candidate.name === name);
    chosen.clear();
    // Logins handed over by name are ticked to start with.
    for (const login of source.logins) if ((preset.names ?? []).includes(login.name) || (preset.entry_indices ?? []).includes(login.index) || preset.all_matches === true) chosen.add(login.index);
    list.show(source.logins, source.name);
    const others = sources.filter((candidate) => candidate !== source && !candidate.problem);
    target.show(source.name, [...others.map((other) => [kindOf(other.name) === "user" ? "Your vault file" : `${placeLabel(other.name)}'s vault file`, other.path]), ["A new file in your home folder", `${state.boot.home}/vault-copy.json`]]);
    paintFoot();
  }

  async function copy() {
    const where = target.read();
    const logins = picked();
    if (logins.length === 0 || !where.ready) return;
    problem.textContent = "";
    if (where.replaces && !(await confirmAction({ title: "Replace the file that is there?", body: `Everything in ${where.shown} is replaced by the ${plural(logins.length, "chosen login")}. What it holds now cannot be brought back.`, confirm: "Replace it", tone: "danger" }))) return;
    try {
      const done = await copyLogins({ source: source.name, version: source.version, indices: logins.map((login) => login.index), path: where.path, conflict: where.conflict });
      markStale();
      showDone(done);
    } catch (error) {
      problem.textContent = error.message;
      // The vault file changed since it was read. It is read again and the choice starts over: a place in the file no longer means the same login.
      if (error.status === 409) {
        markStale();
        load();
      }
      target.look();
    }
  }

  function showDone(done) {
    sheet.foot.replaceChildren(h("span", { class: "spacer" }), button({ label: "Copy more", onclick: () => (sheet.close(), open({ activity, tools }, { preset: {} })) }), button({ label: "Done", tone: "primary", onclick: () => sheet.close() }));
    body.replaceChildren(
      h(
        "div",
        { class: "vault-copy-done" },
        mark("good", 26),
        h("h2", { text: `Copied ${plural(done.copied, "login")}` }),
        h("p", { text: `With ${plural(done.secrets, "secret")}. The file now holds ${plural(done.holds, "login")}.` }),
        pathChip(done.path),
        h("p", {
          class: "dim",
          text: listed.includes(done.path)
            ? "That file is one of the vault files the Vault page lists, so the logins are in the list now."
            : "The copy holds the values themselves. Only its permissions protect it, and they let you alone read it. Remove it once it has done its job.",
        }),
      ),
    );
  }

  async function load() {
    try {
      const answer = await api.vault(state.settings.workingDirectory, "hidden");
      sources = answer.sources.filter((candidate) => candidate.logins.length > 0);
      listed = answer.sources.map((candidate) => candidate.path);
    } catch (error) {
      body.replaceChildren(loadProblem(error, { retry: load, tools, path: PATH }));
      return;
    }
    if (sources.length === 0) {
      go.disabled = true;
      body.replaceChildren(notice({ glyph: "lock", title: "There is nothing to copy yet", body: "No vault file here holds a login. Add one on the Vault page first." }));
      return;
    }
    const wanted = SOURCES[preset.secrets_source];
    const first = sources.find((candidate) => kindOf(candidate.name) === wanted) ?? sources.find((candidate) => candidate.name === source?.name) ?? sources.find((candidate) => kindOf(candidate.name) === "user") ?? sources[0];
    const picker = segmented(sources.map((candidate) => [candidate.name, `${placeLabel(candidate.name)} · ${candidate.logins.length}`]), (name) => {
      picker.set(name);
      pick(name);
    });
    picker.set(first.name);
    from.replaceChildren(...(sources.length > 1 ? [h("span", { class: "dim", text: "From" }), picker.element] : []));
    body.replaceChildren(
      h("section", { class: "vault-copy-step" }, sectionHead("Choose the logins", count, h("span", { class: "spacer" }), from), list.element),
      h("section", { class: "vault-copy-step" }, sectionHead("Where the copy goes"), target.element),
    );
    pick(first.name);
    list.search.input.focus({ preventScroll: true });
  }

  sheet.foot.hidden = false;
  go.disabled = true;
  load();
}
