import { h, toast } from "/assets/scripts/dom.js";
import { button } from "../../widgets.js";
import { lookAt, runWithPassword } from "./tools_api.js";
import { failureIn, fileCard } from "./tools_kit.js";
import { bringIntoView, outcomeCard, runCard, startWatched } from "./tools_run.js";
import { RUN_FAILURES } from "./tools_words.js";

const EMOJI = { encrypt: "🔐", decrypt: "🔓" };

// What the command is given for a run with a key. No password is among it, so it can stand in a task's command line.
function keyArguments(view, tokens, recipient) {
  const { look, mode } = view;
  return [
    ...tokens, look.source.path, "--encryption", "asymmetric",
    ...(mode === "encrypt" && recipient ? ["--recipient", recipient] : []),
    ...(mode === "encrypt" && look.source.kind === "folder" ? ["--compression", view.compression] : []),
    ...(view.output.trim() ? ["--output", look.output] : []),
    ...(view.overwrite ? ["--overwrite"] : []),
  ];
}

// Runs what the sheet has set up, one of three ways.
// With a password: the password goes to the server in the body of one request and from there to the command on its standard input. It is
// in no address, no command line and no log, and the boxes are emptied once it has worked.
// Encrypting for a key asks nothing, so it runs as a task this sheet watches.
// Decrypting with a key may make GPG ask for that key's own passphrase, which it does in a terminal: the sheet makes way for the Activity panel.
export async function runLocker({ context, sheet, view, isOpen, runHolder, paint, refresh, startOver, tokens, secrets, recipient }) {
  const { activity } = context;
  const { mode, look, method } = view;
  const name = look.source.name;
  const verb = mode === "encrypt" ? "Encrypt" : "Decrypt";
  if (method === "key" && mode === "decrypt") {
    sheet.close();
    await activity.start({ title: `${verb} ${name}`, emoji: EMOJI[mode], arguments: keyArguments(view, tokens, recipient), interactive: true, reveal: true });
    return;
  }

  const succeeded = async (result) => {
    await refresh();
    const kept = mode === "decrypt" ? "The encrypted file was left as it is." : method === "password" ? "The original was left as it is. Keep the password somewhere safe, since nothing can recover it." : "The original was left as it is.";
    runHolder.replaceChildren(
      outcomeCard({
        tone: "good", title: `${name} is ${mode}ed`, body: kept, extra: [fileCard(result)],
        actions: [button({ label: `${verb} another`, small: true, onclick: startOver }), button({ label: "Done", small: true, tone: "primary", onclick: () => sheet.close() })],
      }),
    );
    bringIntoView(runHolder);
  };
  const failed = (title, body, actions) => {
    paint();
    runHolder.replaceChildren(outcomeCard({ tone: "bad", title, body, actions }));
    bringIntoView(runHolder);
  };

  if (method === "password") {
    view.busy = true;
    paint();
    runHolder.replaceChildren(h("div", { class: "sec-run", role: "status" }, h("i", { class: "ring" }), h("div", { class: "sec-run-text" }, h("strong", { text: `${verb}ing ${name}` }), h("span", { class: "sec-run-note", text: mode === "encrypt" && look.source.kind === "folder" ? "Packing the folder, then encrypting it" : "This takes a moment for a large file" }))));
    let outcome;
    try {
      outcome = await runWithPassword({ mode, path: look.source.path, password: secrets[0].value, compression: view.compression, output: view.output, overwrite: view.overwrite });
    } catch (error) {
      outcome = { failure: "failed", detail: error.message, result: null };
    }
    view.busy = false;
    const reason = outcome.failure === null ? "" : (RUN_FAILURES[outcome.failure] ?? outcome.detail) || "GPG gave no reason.";
    if (outcome.failure === null) for (const input of secrets) input.value = "";
    // The sheet was closed while it ran. The result is said where it can still be seen.
    if (!isOpen()) return toast(outcome.failure === null ? `${name} is ${mode}ed.` : `${name} was not ${mode}ed. ${reason}`, outcome.failure === null ? "info" : "error");
    if (outcome.failure === null) return succeeded(outcome.result);
    failed(`${name} was not ${mode}ed`, reason, []);
    if (outcome.failure === "wrong_password") secrets[0].select();
    return;
  }

  const card = runCard({ title: `Encrypting ${name}`, onShow: () => sheet.close(), onStop: () => view.running?.stop() });
  card.say(look.source.kind === "folder" ? "Packing the folder, then encrypting it" : "Encrypting for the chosen key");
  runHolder.replaceChildren(card.element);
  view.running = await startWatched(activity, { title: `${verb} ${name}`, emoji: EMOJI[mode], arguments: keyArguments(view, tokens, recipient) });
  paint();
  const watched = view.running;
  const end = await watched.ended;
  view.running = null;
  card.end();
  if (!isOpen()) return;
  if (!end.ok) return failed(end.stopped ? "It was stopped" : `${name} was not encrypted`, end.stopped ? "Nothing was put in place." : failureIn(end.text) || "It gave no reason.", [button({ label: "Show the console", glyph: "terminal", small: true, tone: "ghost", onclick: () => (sheet.close(), watched.show()) })]);
  await succeeded((await lookAt({ mode: "encrypt", path: look.output, compression: view.compression, output: "" })).source);
}
