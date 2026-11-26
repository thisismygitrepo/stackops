import { h, icon, shellQuote } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { filePlace } from "../../agent_places.js";
import { markStale } from "../../data.js";
import { editButton } from "../../space_kit.js";
import { avatar, button, copyChip, iconButton, keyValue, pathChip, pill } from "../../widgets.js";
import { MASK, copyPending, kindOf, placeLabel, rotationNote, telling, valueText } from "./words.js";

const COPIED_MILLISECONDS = 1200;

// One value of a secret: its name, as much of the value as the page was sent, and two ways to the rest. Show fetches the value into this row
// until it is hidden again; Copy puts it on the clipboard without showing it. `read` gives a promise of the whole value as text.
function valueRow(row, read, covered) {
  const text = h("code", { class: "vault-value" });
  let open = false;
  const paint = (shown) => {
    text.textContent = shown === "" ? "Empty" : (shown ?? MASK);
    text.classList.toggle("covered", shown === null);
    text.classList.toggle("blank", shown === "");
  };
  const eye = iconButton("eye", `Show ${row.key}`, telling(async () => {
    const whole = open ? null : await read();
    open = !open;
    paint(open ? whole : row.text);
    eye.replaceChildren(icon(open ? "eyeOff" : "eye", 16));
    eye.title = `${open ? "Hide" : "Show"} ${row.key}`;
    eye.setAttribute("aria-label", eye.title);
  }));
  const copy = iconButton("copy", `Copy ${row.key}`, telling(async () => {
    if (!(await copyPending(read))) return;
    copy.replaceChildren(icon("check", 16));
    setTimeout(() => copy.replaceChildren(icon("copy", 16)), COPIED_MILLISECONDS);
  }));
  paint(row.text);
  return h("li", { class: "vault-row" }, h("span", { class: "vault-key" }, copyChip(row.key), row.json && pill("JSON")), text, h("span", { class: "vault-row-actions" }, covered && eye, copy));
}

function secretBlock(login, secret, position, reveal, whole) {
  const note = rotationNote(secret.rotation);
  // With everything shown the page already holds each value, so nothing is fetched to show or copy one.
  const reader = (row) => (reveal === "full" ? () => Promise.resolve(row.text) : () => whole().then((clear) => valueText(clear.secrets[position].keyValues[row.key])));
  const command = ["devops", "vault", "load", "--source", kindOf(login.source), "--name", login.name, "--secret-name", secret.name].map(shellQuote).join(" ");
  return h(
    "section",
    { class: "vault-secret" },
    h("header", {}, h("h3", { text: secret.name }), secret.tags.map((tag) => pill(tag)), secret.scopes.map((scope) => h("span", { class: "fact", title: "A scope this secret is meant for" }, scope)), h("span", { class: "spacer" }), note && pill(note.text, note.tone)),
    secret.description && h("p", { class: "vault-note", text: secret.description }),
    secret.values.length > 0 ? h("ul", { class: "vault-values" }, secret.values.map((row) => valueRow(row, reader(row), reveal !== "full"))) : h("p", { class: "vault-note", text: "This secret holds no values yet." }),
    keyValue([["Rotated by", secret.rotation?.owner], ...Object.entries(secret.metadata ?? {})]),
    h("footer", { class: "vault-use", title: "Defines these values as environment variables in the terminal the command is run in" }, h("span", { text: "Load into a terminal" }), copyChip(command)),
  );
}

// The login picked in the list, in full: what it is, and each of its secrets with their values.
export function createLoginView({ activity, onEdit, onDelete, onBack }) {
  const head = h("header", { class: "prompt-head" });
  const scroll = h("div", { class: "prompt-scroll vault-scroll", tabindex: "0" });
  const element = h("article", { class: "prompt-reader" }, head, scroll);
  let stamp = "";

  // Showing the same login again changes nothing, so a refresh in the background neither hides a value that was opened nor moves the page.
  function show(login, reveal) {
    const fresh = JSON.stringify([login, reveal]);
    if (fresh === stamp) return;
    stamp = fresh;
    let clear = null;
    // The login with its values as they are, asked for once and shared by every row. A file that has changed since the list was read is
    // answered with a refusal, and the list is read again.
    const whole = () => {
      if (!clear) {
        const pending = api.vaultLogin(state.settings.workingDirectory, login).then((answer) => answer.login);
        clear = pending;
        pending.catch((error) => {
          if (clear === pending) clear = null;
          if (error.status === 409 || error.status === 404) markStale();
        });
      }
      return clear;
    };
    const remove = button({ label: "Delete", glyph: "trash", title: "Remove this login and its secrets from the vault. You are asked first.", onclick: () => onDelete(login) });
    remove.classList.add("caution");
    head.replaceChildren(
      h("button", { class: "icon-btn prompt-back", type: "button", title: "Back to all logins", "aria-label": "Back to all logins", onclick: onBack }, icon("back", 16)),
      avatar(login.name, 46),
      h("div", { class: "prompt-title" }, h("span", { class: "overline", text: [placeLabel(login.source), login.accountName].filter(Boolean).join(" · ") }), h("h2", { text: login.name })),
      h("div", { class: "prompt-actions" }, button({ label: "Edit", glyph: "pencil", title: "Change this login, its secrets or their values", onclick: () => onEdit(login) }), remove),
    );
    const address = login.url && (/^https?:\/\//i.test(login.url) ? h("a", { class: "link", href: login.url, target: "_blank", rel: "noreferrer", text: login.url }) : copyChip(login.url));
    scroll.replaceChildren(
      ...[
        login.description && h("p", { class: "vault-blurb", text: login.description }),
        keyValue([
          ["Account", login.accountName], ["Username", login.username && copyChip(login.username)], ["Email", login.email && copyChip(login.email)], ["Address", address],
          ["Tags", (login.tags ?? []).length > 0 && h("span", { class: "app-detail-pills" }, login.tags.map((tag) => pill(tag)))],
          ...Object.entries(login.metadata ?? {}),
        ]),
        ...login.secrets.map((secret, position) => secretBlock(login, secret, position, reveal, whole)),
        h("footer", { class: "prompt-origin" }, h("span", { text: "Kept in" }), pathChip(login.path), agentButton(activity, filePlace({ title: "the vault file", kind: "secrets", path: login.path }), { small: true }), editButton(activity, { title: "the vault file", kind: "secrets", path: login.path }, { label: "Open the file", small: true })),
      ].filter(Boolean),
    );
    scroll.scrollTop = 0;
  }

  return { element, scroll, show };
}
