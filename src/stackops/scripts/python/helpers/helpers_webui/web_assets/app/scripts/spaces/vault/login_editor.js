import { h, tildify, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { markStale } from "../../data.js";
import { confirmAction, openDialog } from "../../overlays.js";
import { button, field, glyphTile, iconButton, segmented, textBox } from "../../widgets.js";
import { detailRow, rowList } from "./pair_rows.js";
import { detailProblem, folded, secretForm } from "./secret_form.js";
import { PLACE_BLURBS, kindOf, listOf, placeLabel } from "./words.js";

// The form for one login. With `login`, the one picked in the list, it changes that login; without, it adds a new one that starts as `preset`
// and goes to the file named by `place`. `sources` are the vault files as the server lists them, and `reveal` is how much the page shows:
// unless that is everything, what is typed into a value is covered until its row is asked to show it.
// A value the login already has is never in the form unless its row is asked to show it: left alone, it is saved as it was.
export function openLoginEditor({ login = null, preset = null, sources, place = "user", reveal, title, onSaved = () => {} }) {
  const places = sources.filter((source) => !source.problem);
  let target = login ? { name: login.source } : (places.find((source) => source.name === place) ?? places.find((source) => source.name === "user") ?? places[0]);
  if (!target) return toast("No vault file here can be read, so nothing can be added. Open the file from the Vault page and repair it first.");
  const start = login ?? preset ?? { name: "", secrets: [] };
  let dirty = false;
  let clear = null;
  // The saved login with its values as they are, fetched once, for the rows that are asked to show theirs.
  const whole = () => {
    clear ??= api.vaultLogin(state.settings.workingDirectory, login).then((answer) => answer.login);
    clear.catch(() => (clear = null));
    return clear;
  };
  const fetchKept = ([position, key]) => whole().then((saved) => saved.secrets[position].keyValues[key]);

  const leave = () => confirmAction({ title: "Leave without saving?", body: "What you typed for this login has not been saved.", confirm: "Discard", tone: "danger" }).then((yes) => yes && dialog.close());
  // Unsaved text outlives a move to another page: `holdsWork` keeps the form open over it. A reload or a closed tab is the browser's to question.
  const dialog = openDialog({
    label: title ?? (login ? `Edit ${login.name}` : "Add a login"), size: "vault-editor", holdsWork: () => dirty,
    canDismiss: () => {
      if (dirty) leave();
      return !dirty;
    },
  });
  const warnUnsaved = (event) => dirty && event.preventDefault();
  window.addEventListener("beforeunload", warnUnsaved);
  dialog.closed.then(() => window.removeEventListener("beforeunload", warnUnsaved));
  dialog.body.addEventListener("input", () => (dirty = true));

  const name = textBox(start.name ?? "", { placeholder: "Such as github or aws-production" });
  const account = textBox(start.accountName ?? "", { placeholder: "Tells two logins for one service apart" });
  const username = textBox(start.username ?? "");
  const email = textBox(start.email ?? "");
  const url = textBox(start.url ?? "", { placeholder: "https://" });
  const tags = textBox((start.tags ?? []).join(", "), { placeholder: "Separated by commas" });
  const description = textBox(start.description ?? "");
  const details = rowList({ addLabel: "Add a detail", make: detailRow });
  for (const pair of Object.entries(start.metadata ?? {})) details.add(pair);

  const secrets = [];
  const secretHolder = h("div", { class: "vault-secret-forms" });
  // A login holds at least one secret, so the only one left cannot be removed.
  const refit = () => secrets.forEach((form) => (form.remove.hidden = secrets.length === 1));
  function addSecret(secret, origin) {
    const form = secretForm(secret, origin, {
      covered: reveal !== "full", fetchKept,
      onRemove: () => {
        secrets.splice(secrets.indexOf(form), 1);
        form.element.remove();
        refit();
        dirty = true;
      },
    });
    secrets.push(form);
    secretHolder.append(form.element);
    refit();
    return form;
  }
  start.secrets.forEach((secret, position) => addSecret(secret, login ? position : null));
  if (secrets.length === 0) addSecret(null, null);

  const whereHint = h("span", { class: "field-hint" });
  const picker = segmented(places.map((source) => [source.name, placeLabel(source.name)]), (value) => {
    target = places.find((source) => source.name === value);
    showTarget();
  });
  function showTarget() {
    picker.set(target.name);
    whereHint.textContent = `${PLACE_BLURBS[kindOf(target.name)]} ${target.exists ? "Kept in" : "This creates"} ${tildify(target.path, state.boot.home)}.`;
  }
  if (!login) showTarget();

  const problem = h("span", { class: "tool-problem", role: "alert" });
  const save = button({ label: login ? "Save changes" : "Add to the vault", glyph: "check", tone: "primary", onclick: store });
  const firstProblem = () => (name.value.trim() ? (detailProblem(details) ?? secrets.map((form) => form.problem()).find(Boolean) ?? null) : ["Give the login a name.", name]);

  async function store() {
    const found = firstProblem();
    problem.textContent = found?.[0] ?? "";
    if (found) return found[1].focus();
    const optional = Object.entries({ accountName: account, username, email, url, description }).map(([key, input]) => [key, input.value.trim()]);
    const built = {
      name: name.value.trim(), ...Object.fromEntries(optional.filter(([, value]) => value)),
      ...(listOf(tags.value).length > 0 && { tags: listOf(tags.value) }),
      ...(details.rows.length > 0 && { metadata: Object.fromEntries(details.rows.map((row) => row.read())) }),
      secrets: secrets.map((form) => form.read()),
    };
    save.disabled = true;
    try {
      const saved = await api.saveVaultLogin({ base: state.settings.workingDirectory, source: target.name, index: login?.index ?? null, version: login?.version ?? null, login: built });
      dirty = false;
      dialog.close();
      toast(login ? `Saved ${built.name}.` : `Added ${built.name} to the vault.`, "info");
      onSaved({ source: target.name, index: saved.index });
      markStale();
    } catch (error) {
      save.disabled = false;
      problem.textContent = error.message;
      // The file changed under the form. The list is read again, and what was typed stays here to copy from.
      if (error.status === 409) markStale();
    }
  }

  dialog.body.append(
    h(
      "header",
      { class: "file-head" },
      glyphTile("key", 252, 46),
      h("div", { class: "file-title" }, h("span", { class: "overline", text: login ? placeLabel(login.source) : "New login" }), h("h2", { text: title ?? (login ? `Edit ${login.name}` : "Add a login") })),
      iconButton("close", "Close", () => dialog.dismiss()),
    ),
    h(
      "div",
      { class: "vault-form-scroll" },
      !login && places.length > 1 && h("div", { class: "field" }, h("span", { class: "field-label" }, h("span", { text: "Keep it in" })), picker.element, whereHint),
      h("div", { class: "vault-form-grid" }, field("Login name", name), field("Account", account)),
      h("div", { class: "vault-form-grid" }, field("Username", username), field("Email", email)),
      h("div", { class: "vault-form-grid" }, field("Web address", url), field("Tags", tags)),
      field("What it is for", description),
      folded("Other details", details.rows.length, h("div", { class: "field" }, details.element)),
      h("div", { class: "section-head vault-form-head" }, h("h2", { text: "Secrets" }), reveal !== "full" && h("span", { class: "dim", text: "What you type is covered. The eye on a row shows it." })),
      secretHolder,
      button({
        label: "Add another secret", glyph: "plus", small: true,
        onclick: () => {
          addSecret(null, null).name.focus();
          dirty = true;
        },
      }),
    ),
    h("footer", { class: "vault-form-foot" }, problem, button({ label: "Cancel", onclick: () => dialog.dismiss() }), save),
  );
  name.focus();
}

// A new login, from anywhere in the app. The files it can go to are read first, with nothing of what they hold shown.
export async function addLogin({ preset = null, place = "user", reveal = "hidden", title, onSaved }) {
  const { sources } = await api.vault(state.settings.workingDirectory, "hidden");
  openLoginEditor({ sources, preset, place, reveal, title, onSaved });
}
