import { h, tildify, toast } from "/assets/scripts/dom.js";
import { api, state } from "/assets/scripts/state.js";
import { agentButton } from "../agent_ask.js";
import { filePlace, LOGIN_PLACE, PLACES } from "../agent_places.js";
import { markStale } from "../data.js";
import { partLoaders } from "../features.js";
import { createPanel } from "../live_panel.js";
import { rise } from "../motion.js";
import { confirmAction } from "../overlays.js";
import { createParts, editButton, viewHead } from "../space_kit.js";
import { button, callout, notice, searchInput, segmented } from "../widgets.js";
import { plural } from "../words.js";
import { addLogin, openLoginEditor } from "./vault/login_editor.js";
import { loginRow } from "./vault/login_list.js";
import { createLoginView } from "./vault/login_view.js";
import { createToolSections } from "./vault/overview_tools.js";
import { listRequest } from "./vault/tools_kit.js";
import { EVERYWHERE, REVEALS, haystackOf, keyOf, placeLabel, valueCount } from "./vault/words.js";

const STEP_KEYS = { ArrowDown: 1, ArrowUp: -1 };

// The secrets StackOps keeps: a list of logins on one side, the chosen one in full on the other. The layout and its class names are the saved
// prompts' (agents_prompts.css); what is the vault's own is in vault.css.
// The page reads and changes the vault files through the server's /api/vault, not through the CLI: no command lists values with their file and
// place, and one that printed them would put every secret in a command's output.
// Under the list sit the tool cards (vault/overview_tools.js). Their views that are pages of their own, the vault file's and Bitwarden's, swap
// in at #/vault/file and #/vault/bitwarden (feature_lists/vault.js).
export function createVaultSpace(context) {
  const { activity, tools } = context;
  // Kept outside the panel's render, so a refresh leaves the page as it was. How much is shown is not remembered: every start of the app begins hidden.
  let reveal = "hidden";
  let term = "";
  let place = EVERYWHERE;
  let selected = null;
  let vault = { sources: [], logins: [] };
  let placePicker = null;

  const list = h("div", { class: "prompt-list", role: "listbox", "aria-label": "Logins in the vault" });
  const blank = h("div", { class: "prompt-blank" });
  const places = h("div", { class: "prompt-places" });
  const panes = h("div", { class: "prompt-panes", "data-pane": "list" });
  const toolSections = createToolSections({ tools });
  const view = createLoginView({ activity, onEdit: edit, onDelete: remove, onBack: () => (panes.dataset.pane = "list") });
  panes.append(list, view.element, blank);
  const search = searchInput({
    placeholder: "Search logins, tags and value names",
    oninput: (value) => {
      term = value.trim().toLowerCase();
      paint();
    },
  });
  const revealPicker = segmented(REVEALS, (value) => {
    reveal = value;
    revealPicker.set(reveal);
    panel.load();
  });

  const shownLogins = () => vault.logins.filter((login) => (place === EVERYWHERE || login.source === place) && (!term || login.haystack.includes(term)));
  // The login a save just wrote is the one to look at once the list is back.
  const pick = (saved) => (selected = keyOf(saved));
  const add = () => addLogin({ place: place === EVERYWHERE ? "user" : place, reveal, ask: agentButton(activity, LOGIN_PLACE, { small: true }), onSaved: pick }).catch((error) => toast(error.message));

  function edit(login) {
    openLoginEditor({ login, sources: vault.sources, reveal, ask: agentButton(activity, LOGIN_PLACE, { small: true }), onSaved: pick });
  }

  async function remove(login) {
    const source = vault.sources.find((candidate) => candidate.name === login.source);
    const last = source.logins.length === 1 ? " It is the last login in that file, so the file is removed as well." : "";
    const sure = await confirmAction({
      title: `Delete “${login.name}”?`, confirm: "Delete", tone: "danger",
      body: `Its ${plural(login.secrets.length, "secret")} and ${plural(valueCount(login), "value")} are removed from ${tildify(source.path, state.boot.home)}.${last} This cannot be undone.`,
    });
    if (!sure) return;
    await api.deleteVaultLogin(state.settings.workingDirectory, login).then(() => toast(`Deleted ${login.name}.`, "info"), (error) => toast(error.message));
    markStale();
  }

  // A deliberate pick, a click or Enter, also moves a narrow window over to the login.
  function select(login, deliberate) {
    selected = keyOf(login);
    for (const item of list.children) {
      item.setAttribute("aria-selected", String(item.dataset.key === selected));
      item.tabIndex = item.dataset.key === selected ? 0 : -1;
    }
    view.show(login, reveal);
    if (deliberate) panes.dataset.pane = "reader";
  }

  function showAll() {
    term = "";
    search.input.value = "";
    place = EVERYWHERE;
    placePicker?.set(place);
    paint();
  }

  function paint() {
    const shown = shownLogins();
    const several = vault.sources.filter((source) => source.logins.length > 0).length > 1;
    list.replaceChildren(...shown.map((login) => loginRow(login, { term, several, chosen: keyOf(login) === selected, onPick: (picked) => select(picked, true) })));
    panes.classList.toggle("empty", shown.length === 0);
    if (shown.length > 0) return select(shown.find((login) => keyOf(login) === selected) ?? shown[0], false);
    blank.replaceChildren(
      vault.logins.length > 0
        ? notice({ glyph: "search", title: "No login matches", body: "Try a different word, or look in every place.", action: button({ label: "Show everything", small: true, onclick: showAll }) })
        : notice({
            glyph: "lock", title: "The vault is empty",
            body: "Keep API keys, tokens and passwords here. A login holds one or more secrets, and each secret holds named values that can be loaded into a terminal or a program.",
            action: button({ label: "Add a login", glyph: "plus", tone: "primary", onclick: add }),
          }),
    );
  }

  function step(event) {
    const move = STEP_KEYS[event.key];
    if (move === undefined) return;
    const shown = shownLogins();
    const next = shown[Math.max(0, Math.min(shown.length - 1, shown.findIndex((login) => keyOf(login) === selected) + move))];
    if (!next) return;
    event.preventDefault();
    select(next, false);
    const chosen = list.querySelector(`[aria-selected="true"]`);
    chosen.scrollIntoView({ block: "nearest" });
    if (event.currentTarget === list) chosen.focus();
  }
  search.input.addEventListener("keydown", step);
  list.addEventListener("keydown", step);

  const panel = createPanel({
    title: "Logins",
    actions: [h("div", { class: "panel-quick vault-reveal", title: "How much of every secret value this page shows" }, h("span", { class: "dim", text: "Values" }), revealPicker.element)],
    load: () => api.vault(state.settings.workingDirectory, reveal),
    render: (data, { setCount }) => {
      const first = vault.logins.length === 0;
      // The panes are moved into what this returns, which sends their scrolling back to the top.
      const kept = [list.scrollTop, view.scroll.scrollTop];
      vault = {
        sources: data.sources,
        logins: data.sources.flatMap((source) => source.logins.map((login) => ({ ...login, source: source.name, path: source.path, version: source.version, haystack: haystackOf(login, source.name) }))),
      };
      const filled = data.sources.filter((source) => source.logins.length > 0);
      setCount(vault.logins.length > 0 ? `${plural(vault.logins.length, "login")} · ${plural(vault.logins.reduce((total, login) => total + valueCount(login), 0), "value")}` : "");
      toolSections.paintFiles(data.sources);
      if (!filled.some((source) => source.name === place)) place = EVERYWHERE;
      // A choice of place is only offered when the logins come from more than one.
      placePicker =
        filled.length > 1
          ? segmented([[EVERYWHERE, `All · ${vault.logins.length}`], ...filled.map((source) => [source.name, `${placeLabel(source.name)} · ${source.logins.length}`])], (value) => {
              place = value;
              placePicker.set(place);
              paint();
            })
          : null;
      places.replaceChildren(...(placePicker ? [placePicker.element] : []));
      placePicker?.set(place);
      revealPicker.set(reveal);
      paint();
      if (first) rise(list);
      requestAnimationFrame(() => ([list.scrollTop, view.scroll.scrollTop] = kept));
      const unread = data.sources.filter((source) => source.problem);
      return h(
        "div",
        { class: "prompts vault" },
        unread.map((source) =>
          callout({
            tone: "bad", title: `The vault file under “${placeLabel(source.name)}” cannot be read`, text: source.problem,
            extra: h("div", { class: "view-actions" }, agentButton(activity, filePlace({ title: "the vault file", kind: "secrets", path: source.path }), { small: true }), editButton(activity, { title: "the vault file", kind: "secrets", path: source.path }, { label: "Open the file", small: true })),
          }),
        ),
        h("div", { class: "prompt-tools" }, search.element, places),
        panes,
      );
    },
  });
  panel.element.classList.add("prompts-panel");

  const overview = h(
    "div",
    {},
    viewHead({
      title: "Vault", lede: "The logins, keys and tokens StackOps keeps for you, ready to load into a terminal or a program.",
      actions: [agentButton(activity, PLACES.vault), button({ label: "Add a login", glyph: "plus", tone: "primary", onclick: add })],
    }),
    panel.element,
    toolSections.elements,
  );
  const element = h("section", { class: "view", hidden: true }, overview);

  // What a tool's view asked the list to show on the way here: a search word, or one login.
  function takeRequest() {
    if (listRequest.term === null && listRequest.key === null) return;
    term = (listRequest.term ?? "").toLowerCase();
    search.input.value = listRequest.term ?? "";
    place = EVERYWHERE;
    if (listRequest.key) selected = listRequest.key;
    Object.assign(listRequest, { term: null, key: null });
    if (vault.logins.length > 0) paint();
    if (selected && shownLogins().some((login) => keyOf(login) === selected)) panes.dataset.pane = "reader";
  }

  function showOverview() {
    panes.dataset.pane = "list";
    takeRequest();
    panel.ensure();
    toolSections.readBitwarden();
    revealPicker.set(reveal);
    placePicker?.set(place);
  }

  return { element, show: createParts({ element, built: { "": { element: overview, show: showOverview } }, loaders: partLoaders("vault"), context }) };
}
