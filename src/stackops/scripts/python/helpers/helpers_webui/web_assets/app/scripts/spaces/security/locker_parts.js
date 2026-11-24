import { h, icon } from "/assets/scripts/dom.js";
import { createCombo } from "../../combo.js";
import { button, field, iconButton, pill } from "../../widgets.js";
import { keysNamed } from "./locker_keys.js";
import { pathWord } from "./tools_kit.js";

// What a password and a key each mean, in a sentence, for locking and for opening.
export const METHOD_WORDS = {
  encrypt: {
    password: "Anyone who knows the password can open the file, on any machine. Nothing can recover it if the password is lost.",
    key: "Only whoever holds the private half of the chosen key can open the file. No password is asked for.",
  },
  decrypt: {
    password: "Type the password the file was locked with.",
    key: "GPG opens it with the private half of the key it was made for. If that key has a passphrase of its own, GPG asks for it in the console.",
  },
};

// A box for a password: what is typed shows as dots until the eye is pressed, and the browser is told it is a new one, so it does not offer
// a saved password for the site. The value lives in the box alone: it is read when the run starts and written nowhere else on the page.
export function secretBox({ label, onInput }) {
  const input = h("input", { class: "text-input", type: "password", autocomplete: "new-password", spellcheck: "false", autocapitalize: "off", "aria-label": label, placeholder: label, oninput: onInput });
  return { input, element: input };
}

// One eye for all the password boxes of a form: it uncovers and covers them together.
export function eyeFor(boxes) {
  const eye = iconButton("eye", "Show what is typed", () => {
    const hide = boxes[0].input.type !== "password";
    for (const box of boxes) box.input.type = hide ? "password" : "text";
    eye.replaceChildren(icon(hide ? "eye" : "eyeOff", 16));
    eye.title = hide ? "Show what is typed" : "Hide what is typed";
    eye.setAttribute("aria-label", eye.title);
  });
  return eye;
}

// The marks beside a picked file's name: how it is locked, read from what is in it.
export function lockMarks(look, mode) {
  const method = look.encrypted.method;
  if (method === "password") return [pill("Locked with a password", "accent")];
  if (method === "key") return [pill("Locked for a key", "accent")];
  if (method === "unknown") return [pill("Encrypted", "accent")];
  return mode === "decrypt" && look.source.kind === "file" ? [pill("Not encrypted", "warn")] : [];
}

// What stands under a picked file when the other tool fits it better, with the button that switches to it.
export function crossHint(look, mode, onSwitch) {
  const locked = look.encrypted.method !== "none";
  if (mode === "encrypt" && locked) {
    return h("p", { class: "sec-tool-status warn" }, icon("info", 14), h("span", { text: "This file is already encrypted. Encrypting it again puts a second lock on it." }), button({ label: "Decrypt it instead", small: true, onclick: () => onSwitch("decrypt") }));
  }
  if (mode === "decrypt" && look.source.kind !== "missing" && !locked && look.problem !== null) {
    return h("p", { class: "sec-tool-status" }, icon("info", 14), h("span", { text: look.source.kind === "folder" ? "A folder is locked by encrypting it." : "This file is not encrypted." }), button({ label: "Encrypt it instead", small: true, onclick: () => onSwitch("encrypt") }));
  }
  if (mode === "decrypt" && look.problem === null && !locked) {
    return h("p", { class: "sec-tool-status warn" }, icon("alert", 14), h("span", { text: "It is named like an encrypted file but does not look like one inside, so opening it will most likely fail." }));
  }
  return null;
}

// For opening a file locked for a key: whose key that is, and whether its private half is here. Returns a tone and a sentence.
export function madeFor(look, locker) {
  const lock = look.encrypted;
  if (lock.method !== "key") return ["", ""];
  const names = keysNamed(locker, lock.key_ids);
  if (lock.have_key) return ["good", names ? `Made for ${names}. The private half of that key is on this machine.` : "The private half of the key it was made for is on this machine."];
  const ids = lock.key_ids.map((id) => id.slice(-8)).join(", ");
  return ["bad", `Made for ${names || `a key this machine does not have${ids ? `, ID ${ids}` : ""}`}. Without the private half of that key it cannot be opened here.`];
}

// What the run makes and where, and what stays. `look.output` is the full path of the result.
export function resultLine(look, mode) {
  const cut = look.output.lastIndexOf("/");
  const name = h("strong", { text: look.output.slice(cut + 1) });
  const place = pathWord(look.output.slice(0, cut) || "/");
  if (mode === "encrypt") {
    return look.source.kind === "folder"
      ? h("p", { class: "sec-tool-line" }, "Packs the folder into one archive, encrypts that, and makes ", name, " in ", place, ". The folder stays where it is.")
      : h("p", { class: "sec-tool-line" }, "Makes ", name, " in ", place, ". The original stays where it is.");
  }
  return look.unpacks
    ? h("p", { class: "sec-tool-line" }, `The ${look.unpacks} archive inside is unpacked, and what it holds comes out as `, name, " in ", place, ". The encrypted file stays where it is.")
    : h("p", { class: "sec-tool-line" }, "Makes ", name, " in ", place, ". The encrypted file stays where it is.");
}

// The archive a folder is packed into before it is encrypted, as a dropdown that shows which one is the default.
export function compressionPicker({ choices, value, onPick }) {
  const label = (choice) => (choice === choices[0] ? `Default: ${choice}` : choice);
  const combo = createCombo({
    value: label(value), label: "Archive the folder is packed into", glyph: "cube", readOnly: true,
    suggest: async () => choices.map((choice) => ({ value: label(choice), label: label(choice), choice })),
    onPick: (option) => onPick(option.choice),
  });
  return field("Pack the folder as", combo.element);
}

// A switch for replacing what is already at the result's place. It only shows when something is there.
export function replaceSwitch({ on, onToggle }) {
  return h(
    "button",
    { class: "toggle-row", type: "button", role: "switch", "aria-checked": String(on), onclick: onToggle },
    h("span", {}, h("strong", { text: "Replace what is there" }), h("span", { class: "sec-toggle-note", text: " Something already has that name. Leave this off to keep it, and choose another place below." })),
    h("i", { class: "switch" }),
  );
}
