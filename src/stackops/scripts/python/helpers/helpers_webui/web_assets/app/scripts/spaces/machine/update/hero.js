import { h, icon } from "/assets/scripts/dom.js";
import { button, copyChip, pill } from "../../../widgets.js";

// The top of the page: the version installed here, how it stands against the newest one, and the one button that updates.
// When the update cannot work as things stand, the button is off and the reason, with the way forward, takes the place of the note under it.
export function createHero({ onUpdate }) {
  const overline = h("span", { class: "overline" });
  const mark = h("span", { class: "machine-update-mark" });
  const figure = h("div", { class: "machine-update-figure num" });
  const title = h("h2");
  const detail = h("p");
  const go = button({ label: "Update StackOps", glyph: "download", tone: "primary", onclick: onUpdate });
  const note = h("p", { class: "machine-update-act-note" });
  const reason = h("div", { class: "machine-update-reason" });
  const caution = h("p", { class: "machine-update-caution" });
  const element = h(
    "section",
    { class: "machine-update-hero" },
    h("div", { class: "machine-update-hero-text" }, h("div", { class: "machine-update-hero-top" }, overline, mark), figure, title, detail, caution),
    h("div", { class: "machine-update-act" }, go, note),
    reason,
  );

  function paint({ state, verdict, blocker, caution: remark, options, busy }) {
    const version = state.installed?.version ?? state.started_version;
    element.dataset.tone = blocker ? "warn" : verdict.tone;
    overline.textContent = state.installed ? "Installed on this machine" : "Running on this machine";
    mark.replaceChildren(verdict.busy ? h("span", { class: "pill machine-update-checking" }, h("i", { class: "ring" }), verdict.pill) : pill(verdict.pill, verdict.tone));
    figure.replaceChildren(h("span", { text: version }), ...(verdict.target ? [h("span", { class: "machine-update-to" }, icon("arrow", 26), h("span", { class: "machine-update-target", text: verdict.target }))] : []));
    title.textContent = verdict.title;
    detail.textContent = verdict.detail;
    caution.hidden = !remark || Boolean(blocker);
    caution.replaceChildren(icon("alert", 15), h("span", { text: remark }));
    go.disabled = Boolean(blocker) || busy;
    go.className = `btn ${verdict.available && !blocker ? "primary" : "plain"}`;
    go.querySelector("span").textContent = busy ? "Updating" : verdict.target ? `Update to ${verdict.target}` : verdict.settled ? "Update anyway" : "Update StackOps";
    // What the choices further down add to the one click, said next to the button so it is not missed up here.
    const extras = [options.developer && "commits and pushes your changes first", options.settings && "replaces your app settings"].filter(Boolean);
    note.hidden = Boolean(blocker);
    note.classList.toggle("risky", extras.length > 0);
    note.textContent = extras.length > 0 ? `With your choices it also ${extras.join(" and ")}. It asks before it starts.` : verdict.settled ? "Runs the same steps. It still brings uv and the packages StackOps uses up to date." : "It runs in the Activity panel, where you can watch it.";
    reason.hidden = !blocker;
    reason.replaceChildren(...(blocker ? [icon("alert", 18), h("div", {}, h("strong", { text: blocker.title }), h("p", { text: blocker.body }), blocker.command && copyChip(blocker.command))] : []));
  }

  return { element, paint };
}
