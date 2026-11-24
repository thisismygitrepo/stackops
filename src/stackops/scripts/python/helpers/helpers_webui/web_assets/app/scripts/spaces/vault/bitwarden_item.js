import { h, icon, toast } from "/assets/scripts/dom.js";
import { avatar, button, highlight, iconButton, pill } from "../../widgets.js";
import { relativeTime } from "../../words.js";
import { readValue } from "./bitwarden_api.js";
import { hostOf } from "./bitwarden_words.js";
import { MASK, copyPending } from "./words.js";

const COPIED_MILLISECONDS = 1200;
// A value that was asked to be shown is covered again after this long, so it does not stay on a screen that was left open.
const SHOWN_MILLISECONDS = 30000;
const FIELD_WORDS = { password: "password", username: "user name", code: "one-time code", notes: "note" };

// A button that copies one value of an item. The value is fetched at the click and goes straight to the clipboard: it is never drawn.
// With `label` it is a button that says what it copies; without, an icon with that in its hint.
function copyButton(item, field, glyph, label) {
  const hint = `Copy the ${FIELD_WORDS[field]} of ${item.name}`;
  const face = () => (label ? [icon(glyph, 14), h("span", { text: label })] : [icon(glyph, 16)]);
  const copy = async (event) => {
    event.stopPropagation();
    try {
      if (!(await copyPending(() => readValue(item.id, field)))) return;
      control.replaceChildren(...(label ? [icon("check", 14), h("span", { text: "Copied" })] : [icon("check", 16)]));
      control.classList.add("copied");
      setTimeout(() => {
        control.replaceChildren(...face());
        control.classList.remove("copied");
      }, COPIED_MILLISECONDS);
    } catch (error) {
      toast(error.message);
    }
  };
  const control = label ? button({ label, glyph, small: true, title: hint, onclick: copy }) : iconButton(glyph, hint, copy);
  return control;
}

// One value in an item's details: covered until its eye is pressed, then shown for half a minute. `hide` covers it again at once.
function secretLine(item, field, label) {
  const text = h("code", { class: "vault-bw-value covered", text: MASK });
  let timer = 0;
  let open = false;
  const hide = () => {
    clearTimeout(timer);
    open = false;
    text.textContent = MASK;
    text.classList.add("covered");
    eye.replaceChildren(icon("eye", 16));
    eye.title = `Show the ${FIELD_WORDS[field]}`;
  };
  const eye = iconButton("eye", `Show the ${FIELD_WORDS[field]}`, async () => {
    if (open) return hide();
    try {
      const value = await readValue(item.id, field);
      open = true;
      text.textContent = value;
      text.classList.remove("covered");
      eye.replaceChildren(icon("eyeOff", 16));
      eye.title = `Hide the ${FIELD_WORDS[field]}`;
      timer = setTimeout(hide, SHOWN_MILLISECONDS);
    } catch (error) {
      toast(error.message);
    }
  });
  return { element: h("li", {}, h("span", { class: "dim", text: label }), text, h("span", { class: "vault-bw-line-actions" }, eye, copyButton(item, field, "copy"))), hide };
}

// One item of the Bitwarden vault: its labels in a line, the usual copy one click away, and the rest behind the line. `term` is what the search
// box holds. Returns the element and `close`, which folds the details and covers anything shown.
export function itemRow(item, term) {
  const lines = [item.has_password && secretLine(item, "password", "Password"), item.has_code && secretLine(item, "code", "One-time code"), item.has_notes && secretLine(item, "notes", "Note")].filter(Boolean);
  const details = h(
    "ul",
    { class: "vault-bw-details", hidden: true },
    item.username && h("li", {}, h("span", { class: "dim", text: "User name" }), h("code", { class: "vault-bw-value", text: item.username }), h("span", { class: "vault-bw-line-actions" }, copyButton(item, "username", "copy"))),
    lines.map((line) => line.element),
    item.urls.length > 0 && h("li", {}, h("span", { class: "dim", text: item.urls.length === 1 ? "Web address" : "Web addresses" }), h("span", { class: "vault-bw-links" }, item.urls.map((address) => (/^https?:\/\//i.test(address) ? h("a", { class: "link", href: address, target: "_blank", rel: "noreferrer", text: address }) : h("span", { text: address }))))),
    item.changed && h("li", {}, h("span", { class: "dim", text: "Changed" }), h("span", { text: relativeTime(item.changed) })),
  );
  const fold = iconButton("down", `Show more of ${item.name}`, (event) => {
    event.stopPropagation();
    toggle();
  });
  const close = () => {
    details.hidden = true;
    element.classList.remove("open");
    for (const line of lines) line.hide();
  };
  function toggle() {
    if (!details.hidden) return close();
    details.hidden = false;
    element.classList.add("open");
  }
  const element = h(
    "li",
    { class: "vault-bw-item", "data-id": item.id },
    h(
      "div",
      { class: "vault-bw-item-line", onclick: toggle },
      avatar(item.name, 36),
      h(
        "span",
        { class: "vault-bw-item-text" },
        h("strong", {}, highlight(item.name, term), item.favorite && h("span", { class: "vault-bw-star", title: "A favourite in Bitwarden", text: "★" })),
        h("span", {}, item.username ? highlight(item.username, term) : h("em", { text: item.kind === "login" ? "No user name" : "Not a login" }), item.urls[0] && h("span", { class: "dim" }, " · ", highlight(hostOf(item.urls[0]), term))),
      ),
      h("span", { class: "vault-bw-item-pills" }, item.kind !== "login" && pill(item.kind === "note" ? "Note" : item.kind === "card" ? "Card" : item.kind === "identity" ? "Identity" : "Other")),
      h(
        "span",
        { class: "vault-bw-item-actions" },
        item.has_code && copyButton(item, "code", "copy", "Code"),
        item.username && copyButton(item, "username", "copy", "User name"),
        item.has_password && copyButton(item, "password", "copy", "Password"),
        fold,
      ),
    ),
    details,
  );
  return { element, close };
}
