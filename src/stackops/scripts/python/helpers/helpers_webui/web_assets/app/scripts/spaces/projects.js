import { h, icon, tildify, toast } from "/assets/scripts/dom.js";
import { state } from "/assets/scripts/state.js";
import { agentButton } from "../agent_ask.js";
import { filePlace, PLACES } from "../agent_places.js";
import { createLivePanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { toneOf } from "../result_view.js";
import { createView, editButton, toolButton } from "../space_kit.js";
import { avatar, button, copyChip, iconButton, notice, pill } from "../widgets.js";
import { plural, relativeTime } from "../words.js";

const CHANGE_WORDS = { m: "modified", n: "new", d: "deleted", r: "renamed", u: "conflicted" };
const PROJECT_LIST = { title: "the project list", kind: "repos" };

export function createProjectsSpace({ activity, tools }) {
  // Every card action names the repository by its full path: two registered repositories may share a name.
  const run = (title, emoji, runArguments) => activity.start({ title, emoji, arguments: runArguments, interactive: true, reveal: true }).catch((error) => toast(error.message));

  async function push(repo) {
    const target = repo.sync.mode === "guard" ? `its encrypted copy in ${repo.sync.cloud}` : "every remote of this repository";
    const sure = await confirmAction({ title: `Push “${repo.name}”?`, body: `What is committed${repo.branch ? ` on ${repo.branch}` : ""} is sent to ${target}.`, confirm: "Push" });
    if (sure) run(`Push ${repo.name}`, "📤", ["devops", "repos", "action", repo.destination, "--push"]);
  }

  function card(repo) {
    const present = repo.state === "Clean" || repo.state === "Changed";
    const guarded = repo.sync.mode === "guard";
    return h(
      "article",
      { class: "project-card lit" },
      h(
        "header",
        {},
        avatar(repo.name, 44),
        h(
          "div",
          {},
          h(
            "div",
            { class: "project-title" },
            h("h3", { text: repo.name }),
            guarded
              ? h("span", { class: "pill accent", title: `Kept as an encrypted copy in ${repo.sync.cloud}, not on Git remotes` }, icon("lock", 12), "Guarded")
              : h("span", { class: "pill", title: "Synced through its Git remotes" }, icon("branch", 12), "Git"),
          ),
          copyChip(repo.destination, tildify(repo.destination, state.boot.home)),
        ),
      ),
      h(
        "div",
        { class: "project-facts" },
        repo.branch && h("span", { class: "fact" }, icon("branch", 13), repo.branch),
        pill(repo.state, toneOf(repo.state)),
        repo.changes && h("span", { class: "fact", title: "Uncommitted changes" }, repo.changes.split("/").map((part) => `${part.slice(0, -1)} ${CHANGE_WORDS[part.at(-1)]}`).join(" · ")),
        guarded && h("span", { class: "fact", title: `Encrypted copy kept in ${repo.sync.cloud}` }, icon("sync", 13), repo.sync.cloud),
        repo.committed_at && h("span", { class: "fact", title: "Last commit" }, icon("clock", 13), relativeTime(repo.committed_at)),
      ),
      h(
        "footer",
        {},
        h(
          "div",
          {},
          present && iconButton("download", "Pull", () => run(`Pull ${repo.name}`, "📥", ["devops", "repos", "action", repo.destination, "--pull"])),
          present && iconButton("up", "Push", () => push(repo)),
          // The command commits what is already staged and says so when nothing is; the app has no way to stage files.
          repo.state === "Changed" && iconButton("check", "Commit what is staged", () => tools.open("devops repos action", { preset: { directory: repo.destination, commit: "on" } })),
        ),
        // Sync only does something for a guarded repository or a missing one: a cloned Git repository is skipped by the command.
        guarded
          ? button({ label: "Sync", glyph: "sync", small: true, onclick: () => run(`Sync ${repo.name}`, "🔄", ["devops", "repos", "sync", "--which", repo.destination]) })
          : repo.state === "Missing" && button({ label: "Clone", glyph: "download", small: true, onclick: () => run(`Clone ${repo.name}`, "📥", ["devops", "repos", "sync", "--which", repo.destination]) }),
      ),
    );
  }

  const panel = createLivePanel({
    title: "Your projects", path: "devops repos list", extra: ["--json"], surface: { guarded: "Guarded only" }, skeletonShape: "card",
    actions: [agentButton(activity, filePlace(PROJECT_LIST, { ideas: PLACES.projects.ideas }), { small: true }), editButton(activity, PROJECT_LIST, { label: "Edit list", small: true })],
    render: (repos, { setCount }) => {
      if (!Array.isArray(repos) || repos.length === 0) {
        setCount("");
        return notice({ glyph: "branch", title: "No projects yet", body: "Register the repositories on this machine to track and sync them.", action: toolButton(tools, "devops repos register", { label: "Register projects", tone: "primary" }) });
      }
      const changed = repos.filter((repo) => repo.state === "Changed").length;
      const guarded = repos.filter((repo) => repo.sync.mode === "guard").length;
      setCount(`${plural(repos.length, "project")} · ${repos.length - guarded} Git · ${guarded} guarded · ${changed ? `${changed} with changes` : "no changes"}`);
      return rise(h("div", { class: "card-grid" }, repos.map(card)));
    },
  });

  const element = createView(
    {
      title: "Projects", lede: "Every repository StackOps tracks on this machine, and where it stands.",
      actions: [
        agentButton(activity, PLACES.projects),
        toolButton(tools, "devops repos action", { label: "Pull working folder", glyph: "download", preset: { pull: "on" } }),
        toolButton(tools, "devops repos register", { label: "Register", glyph: "plus" }),
        toolButton(tools, "devops repos sync", { label: "Sync all", glyph: "sync", tone: "primary" }),
      ],
    },
    panel.element,
  );
  return { element, show: () => panel.ensure() };
}
