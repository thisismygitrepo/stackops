import { h } from "/assets/scripts/dom.js";
import { openDialog } from "../../../overlays.js";
import { button, field, textBox } from "../../../widgets.js";

// Asks for what joining a network takes when nothing on this machine knows its password. The password goes to the server once, in the
// request that joins, and is kept nowhere: not in the page, not in a file, not in an address.
export function askForNetwork({ name }) {
  const dialog = openDialog({ label: "Join a network", size: "small" });
  const nameBox = textBox(name, { placeholder: "The network's name", "aria-label": "Network name", oninput: () => paint() });
  const passwordBox = h("input", { class: "text-input", type: "password", autocomplete: "off", placeholder: "Its password", "aria-label": "Password", oninput: () => paint() });
  const join = button({ label: "Join", tone: "primary", onclick: () => dialog.close({ name: nameBox.value.trim(), password: passwordBox.value }) });
  const paint = () => (join.disabled = nameBox.value.trim() === "" || passwordBox.value === "");
  const submit = (event) => event.key === "Enter" && !join.disabled && join.click();
  nameBox.addEventListener("keydown", submit);
  passwordBox.addEventListener("keydown", submit);
  dialog.body.append(
    h("h2", { text: name ? `Join ${name}` : "Join another network" }),
    h("p", { text: "The password is used for this one connection. To keep it for next time, save the network in the Vault." }),
    field("Network", nameBox),
    field("Password", passwordBox),
    h("div", { class: "dialog-actions" }, button({ label: "Cancel", onclick: () => dialog.close(null) }), join),
  );
  paint();
  (name ? passwordBox : nameBox).focus();
  return dialog.closed.then((answer) => answer ?? null);
}
