import { debounce, h, tildify, toast } from "/assets/scripts/dom.js";
import { request, state } from "/assets/scripts/state.js";
import { capture } from "../../../data.js";
import { confirmAction } from "../../../overlays.js";
import { button, field, notice, pill, segmented, textBox } from "../../../widgets.js";
import { plural } from "../../../words.js";
import { card, cardHead } from "../kit.js";
import { API, PATHS } from "../words.js";
import { keyFacts } from "./keys.js";

const CHECK_DELAY_MILLISECONDS = 350;
const WAYS = [["pasted", "Paste a key"], ["file", "From a file"], ["github", "From GitHub"]];
const GITHUB_NAME = /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$/;
// How a private key begins, in OpenSSH's and PuTTY's formats. Text like that is refused in the page and never sent anywhere.
const PRIVATE_KEY = /PRIVATE KEY-----|PUTTY-USER-KEY-FILE-/i;
const PRIVATE_KEY_REFUSAL = "That is a private key, and it must never leave the machine it belongs to. Paste the public one: a single line that starts with ssh-ed25519 or ssh-rsa.";

// Adding a key, three ways. What is pasted or picked is checked by the server the way the CLI's add command checks it, and the answer is
// shown before anything is written: which keys they are, by type and fingerprint, and whether each one is already allowed.
export function createAddKey({ onAdded }) {
  let way = "pasted";
  let user = "";
  let candidates = [];
  let checked = null;
  let ticket = 0;
  let adding = false;

  const ways = segmented(WAYS, (id) => {
    way = id;
    paintWay();
  });
  const pasteBox = h("textarea", { class: "text-input network-key-box", rows: "4", spellcheck: "false", autocomplete: "off", placeholder: "ssh-ed25519 AAAA… name", "aria-label": "Public key", oninput: () => checkSoon() });
  const pathBox = textBox("", { placeholder: "~/Downloads/laptop.pub", "aria-label": "Path of a public key file", oninput: () => checkSoon() });
  const githubBox = textBox("", { placeholder: "A GitHub user name", "aria-label": "GitHub user name", oninput: () => paintAction() });
  const picks = h("div", { class: "network-key-picks" });
  const verdict = h("div", { class: "network-key-check" });
  const add = button({ label: "Allow this key", glyph: "plus", tone: "primary", onclick: submit });
  const panes = {
    pasted: h("div", { class: "network-add-pane" }, field("The public key", pasteBox, "One line that starts with ssh-ed25519 or ssh-rsa, as it stands in a file ending in .pub. Several lines add several keys.")),
    file: h("div", { class: "network-add-pane" }, picks, field("Another file", pathBox, "A public key file anywhere on this machine.")),
    github: h("div", { class: "network-add-pane" }, field("GitHub user", githubBox, "Every public key on that account is allowed at once. This asks github.com, so it needs the network.")),
  };

  const offered = () => (way === "pasted" ? { source: "pasted", text: pasteBox.value } : { source: "file", path: pathBox.value.trim() });
  const hasInput = () => (way === "pasted" ? pasteBox.value.trim() !== "" : way === "file" ? pathBox.value.trim() !== "" : GITHUB_NAME.test(githubBox.value.trim()));

  function paintAction() {
    const fresh = checked?.keys?.filter((key) => !key.allowed).length ?? 0;
    add.disabled = adding || !hasInput() || (way !== "github" && fresh === 0);
    add.querySelector("span").textContent = way === "github" ? "Allow every key on that account" : fresh > 1 ? `Allow these ${fresh} keys` : "Allow this key";
  }

  function paintVerdict() {
    if (way === "github" || !hasInput() || checked === null) verdict.replaceChildren();
    else if (checked.error) verdict.replaceChildren(h("p", { class: "network-key-bad", text: checked.error }));
    else {
      verdict.replaceChildren(
        ...checked.keys.map((key) => h("div", { class: "network-key-found" }, h("strong", { text: key.name || "No name" }), h("div", { class: "network-key-facts" }, keyFacts(key), key.allowed ? pill("Already allowed", "") : pill("New", "good")))),
      );
    }
    paintAction();
  }

  async function check() {
    const mine = (ticket += 1);
    checked = null;
    if (way === "github" || !hasInput()) return paintVerdict();
    if (way === "pasted" && PRIVATE_KEY.test(pasteBox.value)) {
      checked = { error: PRIVATE_KEY_REFUSAL };
      return paintVerdict();
    }
    try {
      const answer = await request("POST", `${API}/ssh/keys/check`, offered());
      if (mine === ticket) checked = answer;
    } catch (error) {
      if (mine === ticket) checked = { error: error.message };
    }
    if (mine === ticket) paintVerdict();
  }
  const checkSoon = debounce(check, CHECK_DELAY_MILLISECONDS);

  function paintPicks() {
    picks.replaceChildren(
      ...(candidates.length
        ? [
            h("span", { class: "field-label", text: "This machine's own public keys" }),
            ...candidates.map((file) =>
              h(
                "button",
                {
                  class: "network-key-pick", type: "button", disabled: Boolean(file.problem) || file.keys.every((key) => key.allowed), "aria-pressed": String(pathBox.value === file.path),
                  onclick: () => {
                    pathBox.value = file.path;
                    paintPicks();
                    check();
                  },
                },
                h("strong", { text: tildify(file.path, state.boot.home) }),
                file.problem ? h("span", { class: "dim", text: file.problem }) : h("div", { class: "network-key-facts" }, file.keys.flatMap((key) => keyFacts(key)), file.keys.every((key) => key.allowed) && pill("Already allowed", "")),
              ),
            ),
          ]
        : []),
    );
  }

  function paintWay() {
    ways.set(way);
    for (const [id, pane] of Object.entries(panes)) pane.hidden = id !== way;
    check();
  }

  async function submit() {
    if (adding) return;
    const account = githubBox.value.trim();
    if (way === "github" && !(await confirmAction({ title: `Allow every key on ${account}?`, body: `Whoever holds a key that is on the GitHub account ${account} right now will be able to sign in to this machine as ${user}. Check the name: a typo allows a stranger's keys.`, confirm: "Allow them" }))) return;
    adding = true;
    paintAction();
    try {
      // The GitHub way runs the CLI's own command: it fetches the keys, checks them and writes them in one go.
      const result = way === "github" ? await addFromGithub(account) : await request("POST", `${API}/ssh/keys`, offered());
      toast(result.added > 0 ? `${plural(result.added, "key")} added. ${result.added === 1 ? "Its owner" : "Their owners"} can now sign in as ${user}.` : "Nothing was added: every one of those keys was already allowed.", "info");
      pasteBox.value = pathBox.value = githubBox.value = "";
      checked = null;
      onAdded();
    } catch (error) {
      toast(error.message);
    } finally {
      adding = false;
      paintVerdict();
    }
  }

  async function addFromGithub(account) {
    const { text } = await capture([...PATHS.addKey.split(" "), "--github", account]);
    return { added: Number(/New records:\s*(\d+)/.exec(text)?.[1] ?? 0) };
  }

  const element = card(
    { class: "network-ssh-add" },
    cardHead("Add a key"),
    ways.element,
    ...Object.values(panes),
    verdict,
    h("div", { class: "network-card-actions" }, add),
  );
  paintWay();

  return {
    element,
    paint(overview) {
      user = overview.user;
      candidates = overview.candidates;
      if (overview.problem) element.replaceChildren(cardHead("Add a key"), notice({ glyph: "alert", tone: "bad", title: "Keys cannot be added right now", body: "The file that holds the allowed keys could not be read, so nothing is written to it." }));
      paintPicks();
      // What was checked before a key was added may be allowed by now.
      if (hasInput()) check();
    },
    focus() {
      element.scrollIntoView({ block: "center", behavior: "smooth" });
      (way === "pasted" ? pasteBox : way === "file" ? pathBox : githubBox).focus({ preventScroll: true });
    },
  };
}
