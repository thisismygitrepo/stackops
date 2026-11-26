import { h, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../../agent_ask.js";
import { filePlace } from "../../agent_places.js";
import { confirmAction, openSheet } from "../../overlays.js";
import { button, emojiTile, keyValue, notice, outputActions, pathChip, skeleton } from "../../widgets.js";
import { quietRun, readExample } from "./model.js";
import { FILES } from "./words.js";

const EXAMPLES_FOLDER = ".stackops/examples";

// The example StackOps ships for one settings file, to read before anything is made from it. A copy with its schema can be saved into the
// working folder, which is what `devops config export-example` does; replacing copies that are already there asks first.
// `file` is the page's record of the real file, and `onCreate` makes that file from this example while there is none.
export async function openExample({ activity, tools, file, onCreate }) {
  const words = FILES[file.id];
  const sheet = openSheet({ label: `Example of ${words.title}`, wide: true });
  const text = h("div", { class: "settings-example-text" }, skeleton(5, "row"));
  const facts = h("div");
  sheet.body.append(
    h(
      "header",
      { class: "tool-head" },
      emojiTile(words.emoji, file.id, 56),
      h("div", {}, h("span", { class: "overline", text: "Settings files" }), h("h1", { text: `${words.title}: the example` }), h("p", { text: "What StackOps ships as a starting point. A new file of this kind starts out like this." })),
    ),
    facts,
    text,
  );

  let example;
  try {
    example = await readExample(file.kind);
  } catch (error) {
    text.replaceChildren(notice({ glyph: "alert", tone: "bad", title: "The example could not be read", body: error.message }));
    return;
  }
  const folder = `${state.settings.workingDirectory}/${EXAMPLES_FOLDER}`;
  text.replaceChildren(h("pre", { class: "script-code" }, example.text.replace(/\n$/, "").split("\n").map((line) => h("span", { text: line }))));
  facts.replaceChildren(keyValue([["A copy goes to", pathChip(`${folder}/${example.file_name}`)], ["With it", `${example.schema_name}, the schema an editor checks the file against`]]));

  let saving = false;
  async function saveCopy() {
    if (saving) return;
    saving = true;
    try {
      // The folder's listing says whether copies are already there, so the question comes before the command refuses.
      const { entries } = await api.paths(`${EXAMPLES_FOLDER}/`, state.settings.workingDirectory);
      const there = [example.file_name, example.schema_name].filter((name) => entries.includes(`${EXAMPLES_FOLDER}/${name}`));
      if (there.length > 0 && !(await confirmAction({ title: "Replace the copy that is there?", body: `${there.join(" and ")} ${there.length === 1 ? "is" : "are"} already in ${folder}. Saving again overwrites ${there.length === 1 ? "it" : "them"}.`, confirm: "Replace" }))) return;
      const went = await quietRun(activity, { title: `Save the ${words.title.toLowerCase()} example`, emoji: "📦", runArguments: ["devops", "config", "export-example", file.kind, ...(there.length > 0 ? ["--overwrite"] : [])] });
      if (went) toast(`Saved ${example.file_name} and ${example.schema_name} to ${folder}.`, "info");
    } catch (error) {
      toast(error.message);
    } finally {
      saving = false;
    }
  }

  const creatable = file.available && !file.exists && !file.blocked;
  sheet.foot.hidden = false;
  sheet.foot.append(
    ...[
      agentButton(activity, filePlace({ title: words.title, kind: file.kind, path: file.path }, { notes: ["The page shows the example StackOps ships for this file; `stackops devops config export-example` writes it out."], ideas: [file.exists ? "Explain what each part of this file does" : "Create this file and set it up for me"] })),
      ...outputActions(() => example.text, example.file_name),
      button({ label: "All options", tone: "ghost", title: "Only the file, only the schema, or over your real file", onclick: () => tools.open("devops config export-example", { plain: true, preset: { which: file.kind } }) }),
      h("span", { class: "spacer" }),
      button({ label: "Save a copy in the working folder", glyph: "download", tone: creatable ? "plain" : "primary", onclick: saveCopy }),
      creatable &&
        button({
          label: "Create my file from this", glyph: "plus", tone: "primary",
          onclick: () => {
            sheet.close();
            onCreate(file);
          },
        }),
    ].filter(Boolean),
  );
}
