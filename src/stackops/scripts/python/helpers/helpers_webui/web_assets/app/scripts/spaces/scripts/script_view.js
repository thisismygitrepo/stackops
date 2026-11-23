import { h, icon, splitArguments, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { replay } from "../../motion.js";
import { editButton } from "../../space_kit.js";
import { button, copyChip, notice, pathChip, pill, skeleton, textBox } from "../../widgets.js";
import { formatBytes, relativeTime } from "../../words.js";
import { ONLINE, canChange, commandLine, fileOf, folderOf, kindLabel, placeLabel, runArguments, runsHere, scriptFace } from "./words.js";

// The script picked in the list: what it is, a bar to run it from, and its text to read before doing so.
export function createScriptView({ activity, onBack }) {
  // What was typed to pass on to each script, so going to another one and back does not lose it.
  const typed = new Map();
  // Each script's text, kept by the file's size and time of change: a refresh of the list reads a script again only when it is another file by then.
  const texts = new Map();
  let current = null;
  let stamp = "";

  const head = h("header", { class: "prompt-head" });
  const blurb = h("p", { class: "prompt-blurb" });
  const box = textBox("", {
    class: "text-input script-arguments", placeholder: "Arguments to pass on, if it takes any", "aria-label": "Arguments passed on to the script",
    title: "Passed on to the script as they are. Quotes keep words with spaces together.",
    oninput: () => typed.set(current.path, box.value),
    onkeydown: (event) => event.key === "Enter" && run(),
  });
  const meta = h("div", { class: "prompt-meta" });
  const scroll = h("div", { class: "prompt-scroll", tabindex: "0" });
  const element = h(
    "article",
    { class: "prompt-reader" },
    head, blurb,
    h("div", { class: "script-run" }, box, button({ label: "Run", glyph: "play", tone: "primary", title: "Runs in the activity panel, where it can also be typed into and stopped", onclick: run })),
    meta, scroll,
  );

  function run() {
    activity
      .start({ title: `Run ${fileOf(current)}`, emoji: "🚀", arguments: runArguments(current, splitArguments(box.value)), interactive: true, reveal: true })
      .catch((error) => toast(error.message));
  }

  function textOf(script) {
    const key = [script.path, script.size, script.modified].join("\n");
    if (!texts.has(key)) {
      const pending = api.scriptText(state.settings.workingDirectory, script).then((answer) => answer.text);
      texts.set(key, pending);
      pending.catch(() => texts.delete(key));
    }
    return texts.get(key);
  }

  // Each line is an element of its own, which is what numbers them. The last line break ends the file and is not a line.
  async function paintText(script, moved) {
    if (moved) scroll.replaceChildren(...skeleton(4, "row"));
    const body = await textOf(script).then(
      (text) => h("pre", { class: "script-code" }, text.replace(/\n$/, "").split("\n").map((line) => h("span", { text: line }))),
      (error) => notice({ glyph: "report", title: "Its text is not shown", body: error.message }),
    );
    if (current !== script) return;
    const online = script.source === ONLINE;
    // A script that is read again in the background stays where it was scrolled to.
    const top = moved ? 0 : scroll.scrollTop;
    scroll.replaceChildren(
      body,
      h(
        "footer",
        { class: "prompt-origin" },
        h("span", { text: online ? "Fetched from" : "Kept in" }), online ? copyChip(script.path) : pathChip(script.path),
        h("span", { text: "From a terminal" }), copyChip(commandLine(script)),
      ),
    );
    scroll.scrollTop = top;
    if (moved) replay(scroll, "prompt-in");
  }

  // Showing the same script again changes nothing, so a refresh in the background does not move the page.
  function show(script) {
    const fresh = JSON.stringify(script);
    if (fresh === stamp) return;
    stamp = fresh;
    const moved = current?.path !== script.path;
    current = script;
    if (moved) box.value = typed.get(script.path) ?? "";
    const online = script.source === ONLINE;
    head.replaceChildren(
      h("button", { class: "icon-btn prompt-back", type: "button", title: "Back to all scripts", "aria-label": "Back to all scripts", onclick: onBack }, icon("back", 16)),
      scriptFace(script, 46),
      h("div", { class: "prompt-title" }, h("span", { class: "overline", text: [placeLabel(script.source), folderOf(script)].filter(Boolean).join(" · ") }), h("h2", { text: fileOf(script) })),
      h("div", { class: "prompt-actions" }, canChange(script.source) && editButton(activity, { title: fileOf(script), kind: "script", path: script.path })),
    );
    blurb.textContent = script.summary;
    blurb.hidden = !script.summary;
    meta.replaceChildren(
      ...[
        pill(kindLabel(script)),
        !runsHere(script) && pill("Made for another system", "warn"),
        h("span", { class: "dim", text: online ? "Not on this machine: it is fetched each time it is run" : `${formatBytes(script.size)} · changed ${relativeTime(script.modified)}` }),
      ].filter(Boolean),
    );
    paintText(script, moved);
  }

  return { element, scroll, show };
}
