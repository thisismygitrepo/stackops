import { h, tildify } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { button, copyChip } from "../../widgets.js";
import { formatBytes } from "../../words.js";
import { runBanner } from "./kit.js";
import { APPLY_COMMAND } from "./words.js";

const step = (title, text, ...extra) => h("li", {}, h("div", {}, h("strong", { text: title }), text && h("p", { text }), ...extra));
const command = (text) => h("div", { class: "dotfiles-command" }, copyChip(text));

// Where the archive lies once it is made, the way a person on the other machine would type it, and the address it is offered at.
export const archivePlace = (plan, choice) => tildify(choice.elsewhere && choice.place ? choice.place.path : plan.archive.path, state.boot.home);
export const shareAddress = (plan) => `http://${plan.share.address}:${plan.share.port}`;

// What to do on the other machine, for the way that is chosen. The commands are the ones the export command prints for it.
export function stepsCard({ plan, choice }) {
  const place = archivePlace(plan, choice);
  const address = shareAddress(plan);
  const open = "In StackOps there, open Dotfiles and choose Bring settings from another machine.";
  const first = {
    file: [step("Take the archive over", `Copy ${place} into the other machine's home folder.`), step("Open it there", `${open} It lists the archives in the home folder. Or run this in a terminal:`, command(`devops config dotfiles import --url ${place}`))],
    share: [
      step("Leave this machine offering it", "Both machines have to be on the same network. This page says when it is on offer."),
      step("Fetch it there", `${open} Give it this address:`, command(address), h("p", { text: "Or run this in a terminal, which also puts every file in its place:" }), command(`devops config dotfiles import --url ${address} && ${APPLY_COMMAND}`)),
    ],
    ssh: [
      step("It arrives by itself", `The archive lands in the home folder of ${choice.remote.trim() || "the machine you choose"}, under the same name as here.`),
      step("Open it there", `${open} Or run this in a terminal:`, command(`devops config dotfiles import --url ${place}`)),
    ],
  }[choice.way];
  return h(
    "section",
    { class: "dotfiles-card" },
    h("h3", { class: "dotfiles-step-title" }, "Then, on the other machine"),
    h("p", { class: "field-hint", text: "It needs StackOps installed. Bringing the archive in replaces that machine's whole dotfiles folder." }),
    h(
      "ol",
      { class: "dotfiles-steps" },
      ...first,
      step("Give it the password", "The one you set here. It is asked for once."),
      step("Put the files in place", "Choose Apply to this machine on its Dotfiles page. Or run:", command(APPLY_COMMAND)),
      choice.way === "share" && step("Stop offering it", "Come back to this page and stop it, so the archive is no longer handed out."),
    ),
  );
}

// How a run of the export stands, over the page. `run.phase` goes from "packing" to "offering" (the network way only) to "done".
export function exportBanner({ run, plan, onReveal, onStop, onDismiss }) {
  const show = button({ label: "Show the console", glyph: "terminal", small: true, onclick: onReveal });
  const close = button({ label: "Dismiss", small: true, tone: "ghost", onclick: onDismiss });
  if (run.phase === "packing") {
    return runBanner({ tone: "", busy: true, title: run.way === "ssh" ? `Making the archive and sending it to ${run.remote}…` : "Making the archive…", text: run.needsTyping ? "Type the password in the console to go on." : "The folder is packed and encrypted. A large one takes a moment.", actions: [show] });
  }
  if (run.phase === "offering") {
    return runBanner({
      tone: "good", busy: true, title: "The archive is on offer", text: "Anyone on this network can fetch it at this address until you stop it. Only the password opens it.", extra: h("div", { class: "dotfiles-command" }, copyChip(shareAddress(plan))),
      actions: [button({ label: "Stop offering it", glyph: "stop", small: true, tone: "danger", onclick: onStop }), show],
    });
  }
  const made = plan.archive.exists || run.result !== "failed";
  const where = h("div", { class: "dotfiles-command" }, copyChip(run.place), plan.archive.exists && !run.elsewhere && h("span", { class: "dim", text: formatBytes(plan.archive.size_bytes) }));
  if (run.result === "made") return runBanner({ tone: "good", title: "The archive is ready", text: "It is protected with the password you set. The steps for the other machine are below.", extra: where, actions: [close] });
  if (run.result === "sent") return runBanner({ tone: "good", title: `Sent to ${run.remote}`, text: "It is in that machine's home folder. A copy stays here too.", extra: where, actions: [show, close] });
  if (run.result === "offered") return runBanner({ tone: "", title: "No longer on offer", text: "The archive stays on this machine, so it can be offered or carried over again.", extra: where, actions: [close] });
  return runBanner({
    tone: "bad", title: run.result === "stopped" ? "Stopped before it finished" : "The archive was not made", text: run.reason || (made ? "" : "The console has the details."),
    actions: [show, close],
  });
}
