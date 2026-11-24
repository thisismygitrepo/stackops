import { h, icon, shellQuote } from "/assets/scripts/dom.js";
import { openSheet } from "../../../overlays.js";
import { button, callout, copyChip, glyphTile, keyValue, notice, pathChip, pill, skeleton } from "../../../widgets.js";
import { hueOf, plural } from "../../../words.js";
import { readDetail } from "./api.js";
import { ancestors } from "./model.js";
import { HEAVY_CPU, HEAVY_MEMORY, LOCKS, ROLES, ageText, cpuText, memoryText, processCount, startedText, statusOf } from "./words.js";

const REACH = { local: "this machine only", network: "open to the network" };
const UNREAD = {
  ended: "It has ended, so there is nothing more to read.",
  foreign: "It belongs to another account. Its command, folder and files can only be read when StackOps runs as an administrator.",
};

function figure(label) {
  const value = h("strong");
  const bar = h("i", { class: "procs-bar" });
  const note = h("small", { class: "dim" });
  return { value, bar, note, element: h("div", { class: "procs-detail-figure" }, h("span", { class: "overline", text: label }), value, bar, note) };
}

function relative(process, onShow) {
  const cpu = h("span", { class: "num" });
  const memory = h("span", { class: "num" });
  const element = h("li", {}, h("button", { type: "button", onclick: () => onShow(process.key) }, h("strong", { text: process.name }), h("span", { class: "dim", text: `ID ${process.pid}` }), h("span", { class: "spacer" }), cpu, memory, icon("arrow", 13)));
  return { element, cpu, memory };
}

function restOf(detail, lock) {
  const command = detail.arguments.map(shellQuote).join(" ");
  const sockets = detail.waiting.map((socket) => h("li", {}, h("strong", { class: "num", text: String(socket.port) }), h("span", { class: "dim", text: `${socket.protocol} · ${REACH[socket.reach] ?? `on ${socket.address}`}` })));
  return [
    lock in UNREAD && !detail.readable && h("p", { class: "procs-aside", text: UNREAD[lock] }),
    command && h("section", {}, h("h3", { text: "Command" }), h("pre", { class: "procs-command-block", text: command }), copyChip(command, "Copy the command")),
    keyValue([
      ["Program", detail.program && pathChip(detail.program)],
      ["Folder", detail.folder && pathChip(detail.folder)],
      ["Threads", detail.threads !== null && detail.threads.toLocaleString()],
      ["Connections", detail.connections > 0 && `${plural(detail.connections, "connection")} open to other programs or machines`],
    ]),
    sockets.length > 0 && h("section", {}, h("h3", { text: "Listening on" }), h("ul", { class: "procs-sockets" }, sockets)),
    detail.open_file_count > 0 &&
      h(
        "details",
        { class: "fold" },
        h("summary", {}, icon("chevron", 13), h("span", { text: "Open files" }), h("b", { text: detail.open_file_count.toLocaleString() })),
        h("ul", { class: "procs-files" }, detail.open_files.map((path) => h("li", {}, pathChip(path)))),
        detail.open_file_count > detail.open_files.length && h("p", { class: "dim", text: `The first ${detail.open_files.length} are listed.` }),
      ),
  ];
}

// Everything about one process, beside the list. Its figures and its relatives follow the page's readings; the command, the folder, the
// ports and the files are read once when it is shown. `page` gives the current reading, a way to hear of new ones, and the page's actions.
export function openDetail({ process, page }) {
  const sheet = openSheet({ label: process.name, wide: true });
  const title = h("h1");
  const line = h("p");
  const pills = h("div", { class: "procs-detail-pills" });
  const tile = h("span", { class: "procs-detail-tile" });
  const warnings = h("div", { class: "procs-detail-warnings" });
  const cpu = figure("CPU");
  const memory = figure("Memory");
  const parents = h("ol", { class: "procs-relatives" });
  const children = h("ul", { class: "procs-relatives" });
  const parentsBlock = h("section", {}, h("h3", { text: "Started by" }), parents);
  const childrenTitle = h("h3");
  const childrenBlock = h("section", {}, childrenTitle, children);
  const rest = h("div", { class: "procs-detail-rest" });
  const quit = button({ label: "Stop", glyph: "stop", tone: "primary", onclick: () => page.stop([current()], false) });
  const force = button({ label: "Force stop", onclick: () => page.stop([current()], true) });
  const find = button({
    label: "Show in the tree", glyph: "branch", tone: "ghost",
    onclick: () => {
      sheet.close();
      page.reveal(key);
    },
  });
  let key = process.key;
  let known = process;
  let relatives = { signature: "", rows: [] };
  let ticket = 0;
  const current = () => page.model().byKey.get(key) ?? null;

  function paint() {
    const found = current();
    known = found ?? known;
    const status = statusOf(found ? known.status : "zombie");
    const role = ROLES[known.role];
    const lock = found ? LOCKS[known.lock] : "It has ended.";
    title.textContent = known.name;
    line.textContent = `ID ${known.pid} · ${known.user} · started ${ageText(known.started, page.model().taken_at)}`;
    line.title = startedText(known.started);
    pills.replaceChildren(pill(found ? status.label : "Ended", found && status.tone === "busy" ? "good" : ""), ...(role ? [pill(role.label, role.tone)] : []));
    warnings.replaceChildren(
      ...(found ? [] : [callout({ tone: "", title: "This process has ended", text: "What is below is how it was when it was last read." })]),
      ...(found && role ? [callout({ tone: role.risky ? "warn" : "", title: role.warning })] : []),
      ...(found && known.lock ? [callout({ tone: "", title: "It cannot be stopped from here", text: LOCKS[known.lock] })] : []),
    );
    const scale = page.scale();
    cpu.value.textContent = found ? cpuText(known.cpu) : "—";
    cpu.bar.style.setProperty("--share", String(found ? Math.min((known.cpu ?? 0) / scale.cpu, 1) : 0));
    cpu.element.classList.toggle("heavy", found !== null && (known.cpu ?? 0) >= HEAVY_CPU);
    cpu.note.textContent = found && known.groupSize > 0 && known.groupCpu !== null ? `${cpuText(known.groupCpu)} with the ${processCount(known.groupSize)} it started` : "";
    memory.value.textContent = found ? memoryText(known.memory) : "—";
    memory.bar.style.setProperty("--share", String(found ? Math.min((known.memory ?? 0) / scale.memory, 1) : 0));
    memory.element.classList.toggle("heavy", found !== null && (known.memory ?? 0) >= HEAVY_MEMORY);
    memory.note.textContent = found && known.groupSize > 0 && known.groupMemory !== null ? `${memoryText(known.groupMemory)} with the ${processCount(known.groupSize)} it started` : "";
    const chain = found ? ancestors(found) : [];
    const started = found ? [...found.children].sort((left, right) => (right.groupMemory ?? 0) - (left.groupMemory ?? 0)) : [];
    // The lines are only made again when the relatives changed. Their figures are filled in at every reading.
    const signature = [...chain, null, ...started].map((item) => item?.key ?? "|").join(" ");
    if (signature !== relatives.signature) {
      relatives = { signature, rows: [...chain, ...started].map((item) => ({ key: item.key, ...relative(item, show) })) };
      parents.replaceChildren(...relatives.rows.slice(0, chain.length).map((row) => row.element));
      children.replaceChildren(...relatives.rows.slice(chain.length).map((row) => row.element));
    }
    for (const row of relatives.rows) {
      const item = page.model().byKey.get(row.key);
      row.cpu.textContent = cpuText(item.groupCpu);
      row.memory.textContent = memoryText(item.groupMemory);
    }
    parentsBlock.hidden = chain.length === 0;
    childrenBlock.hidden = started.length === 0;
    childrenTitle.textContent = `It started ${processCount(started.length)}`;
    quit.disabled = force.disabled = Boolean(lock);
    quit.title = force.title = lock ?? "";
    find.disabled = !found;
  }

  async function show(nextKey) {
    key = nextKey;
    known = current() ?? known;
    const mine = (ticket += 1);
    sheet.panel.setAttribute("aria-label", known.name);
    tile.replaceChildren(glyphTile("cpu", hueOf(known.name), 56));
    rest.replaceChildren(...skeleton(3, "row"));
    paint();
    sheet.body.scrollTo(0, 0);
    try {
      const detail = await readDetail(known);
      if (mine === ticket) rest.replaceChildren(...restOf(detail, known.lock).filter(Boolean));
    } catch (error) {
      if (mine !== ticket) return;
      // A process that ended before it could be read is already said to have ended, above.
      rest.replaceChildren(...(error.status === 404 ? [] : [notice({ glyph: "alert", tone: "bad", title: "The rest could not be read", body: error.message })]));
    }
  }

  sheet.body.classList.add("procs-detail");
  sheet.body.append(
    h("header", { class: "tool-head" }, tile, h("div", {}, h("span", { class: "overline", text: "Process" }), title, line, pills)),
    warnings,
    h("div", { class: "procs-detail-figures" }, cpu.element, memory.element),
    rest,
    parentsBlock,
    childrenBlock,
  );
  sheet.foot.hidden = false;
  sheet.foot.append(find, h("span", { class: "spacer" }), force, quit);
  sheet.closed.then(page.watch(paint));
  show(key);
}
