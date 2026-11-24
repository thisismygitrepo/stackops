import { h, icon } from "/assets/scripts/dom.js";
import { rise } from "../../../motion.js";
import { button, notice, skeleton } from "../../../widgets.js";
import { plural, relativeTime } from "../../../words.js";
import { shortId } from "./words.js";

const outside = (href, ...children) => h("a", { class: "link", href, target: "_blank", rel: "noopener noreferrer" }, ...children);
const stamp = (value) => h("span", { class: "dim", title: new Date(value).toLocaleString(), text: relativeTime(value) });

// What an update would bring: the commits the source folder does not have yet, or the releases newer than the installed one, newest first.
// Having nothing to list, and having no answer, are states of their own.
export function createNews({ onRetry }) {
  const count = h("span", { class: "count" });
  const list = h("div", { class: "machine-update-news-body" }, skeleton(3, "row"));
  const element = h("section", { class: "machine-update-card machine-update-news" }, h("header", { class: "machine-update-card-head" }, h("h2", { text: "What is new" }), count), list);
  const retry = () => button({ label: "Check again", glyph: "refresh", small: true, onclick: onRetry });

  function commitRow(commit) {
    return h(
      "li",
      {},
      h("i", { class: "machine-update-dot" }),
      h("div", {}, outside(commit.url, commit.title || "No message"), h("p", {}, commit.author && h("span", { text: commit.author }), stamp(commit.committed_at), h("code", { text: shortId(commit.sha) }))),
    );
  }

  function releaseRow(release, page) {
    return h("li", {}, h("i", { class: "machine-update-dot" }), h("div", {}, outside(`${page}/${release.version}/`, release.version), h("p", {}, "Came out ", stamp(release.released_at))));
  }

  function paint({ state, latest }) {
    count.textContent = "";
    if (state.route === "checkout" && state.checkout.problem !== "") {
      list.replaceChildren(notice({ glyph: "folder", title: "Nothing to compare", body: "The source folder has to be readable before the page can say what is new for it." }));
      return;
    }
    if (latest === null) {
      list.replaceChildren(...skeleton(3, "row"));
      return;
    }
    if (latest.trouble || latest.source === "none") {
      const site = latest.source === "index" ? "PyPI" : "GitHub";
      const body =
        latest.source === "none"
          ? "This branch does not follow one on GitHub, so there is no public list of its commits to read. The update itself still pulls from wherever the branch points."
          : latest.trouble === "server"
            ? `The StackOps server could not ask ${site}. It said: ${latest.problem}`
            : `${site} did not say what is new. That does not stop the update, which asks again by itself.`;
      list.replaceChildren(notice({ glyph: "globe", title: latest.source === "none" ? "Nothing online to compare with" : `No answer from ${site}`, body, action: latest.source === "none" ? undefined : retry() }));
      return;
    }
    const items = latest.source === "index" ? latest.releases : latest.commits;
    if (items.length === 0) {
      const head = state.checkout?.head;
      const body = latest.source === "index" ? `${latest.version} is the newest release and you have it.` : head ? `You are on the newest commit GitHub has, or past it. Yours is "${head.title}".` : "You have every commit GitHub has.";
      list.replaceChildren(notice({ glyph: "check", tone: "good", title: "Nothing new", body, action: outside(latest.page, icon("external", 13), h("span", { text: latest.source === "index" ? "See it on PyPI" : "See the history on GitHub" })) }));
      return;
    }
    count.textContent = `${plural(items.length, latest.source === "index" ? "release" : "commit")}${latest.more ? " or more" : ""}`;
    const page = latest.page.replace(/\/[^/]+\/$/, "");
    const rows = latest.source === "index" ? latest.releases.map((release) => releaseRow(release, page)) : latest.commits.map(commitRow);
    list.replaceChildren(
      rise(h("ol", { class: "machine-update-timeline" }, rows)),
      h("p", { class: "machine-update-more" }, latest.more && h("span", { text: latest.source === "index" ? "Older releases are left out. " : "GitHub lists the newest ones only, so there may be more. " }), outside(latest.page, icon("external", 13), h("span", { text: latest.source === "index" ? "The newest release on PyPI" : "The full history on GitHub" }))),
    );
  }

  return { element, paint };
}
