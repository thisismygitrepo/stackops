import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { toneOf } from "../result_view.js";
import { createView, toolButton } from "../space_kit.js";
import { avatar, button, copyChip, notice, pill } from "../widgets.js";
import { plural, relativeTime } from "../words.js";

export function createProjectsSpace({ activity, tools }) {
  const sync = (name) =>
    activity.start({ title: `Sync ${name}`, emoji: "📥", arguments: ["devops", "repos", "sync", "--which", name], interactive: true, reveal: true }).catch((error) => toast(error.message));

  const card = (repo) =>
    h(
      "article",
      { class: "project-card lit" },
      h("header", {}, avatar(repo.name, 44), h("div", {}, h("h3", { text: repo.name }), copyChip(repo.destination, tildify(repo.destination, state.boot.home)))),
      h(
        "div",
        { class: "project-facts" },
        repo.branch && h("span", { class: "fact" }, icon("branch", 13), repo.branch),
        pill(repo.state, toneOf(repo.state) || (repo.state === "Clean" ? "good" : "warn")),
        repo.changes && repo.changes !== "0" && h("span", { class: "fact", title: "Uncommitted changes" }, repo.changes),
        repo.sync?.mode === "guard" && h("span", { class: "fact", title: `Encrypted copy kept in ${repo.sync.cloud}` }, icon("sync", 13), repo.sync.cloud),
      ),
      h("footer", {}, h("span", { class: "dim", text: repo.committed_at ? `Last commit ${relativeTime(repo.committed_at)}` : "No commits yet" }), button({ label: "Sync", glyph: "sync", small: true, onclick: () => sync(repo.name) })),
    );

  const panel = createLivePanel({
    title: "Your projects", path: "devops repos list", extra: ["--json"], skeletonShape: "card",
    render: (repos, { setCount }) => {
      if (!Array.isArray(repos) || repos.length === 0) {
        setCount("");
        return notice({ glyph: "branch", title: "No projects yet", body: "Register the repositories on this machine to track and sync them.", action: toolButton(tools, "devops repos register", { label: "Register projects", tone: "primary" }) });
      }
      const changed = repos.filter((repo) => repo.state !== "Clean").length;
      setCount(`${plural(repos.length, "project")} · ${changed ? `${changed} with changes` : "all clean"}`);
      return rise(h("div", { class: "card-grid" }, repos.map(card)));
    },
  });

  const element = createView(
    {
      title: "Projects", lede: "Every repository StackOps tracks on this machine, and where it stands.",
      actions: [
        toolButton(tools, "devops repos action", { label: "Pull everything", glyph: "download", preset: { pull: "on" } }),
        toolButton(tools, "devops repos register", { label: "Register", glyph: "plus" }),
        toolButton(tools, "devops repos sync", { label: "Sync all", glyph: "sync", tone: "primary" }),
      ],
    },
    panel.element,
  );
  return { element, show: () => panel.ensure() };
}
