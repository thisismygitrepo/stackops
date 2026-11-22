import { h, icon } from "/assets/scripts/dom.js";
import { createLivePanel } from "../../live_panel.js";
import { toneOf } from "../../result_view.js";
import { toolButton } from "../../space_kit.js";
import { copyChip, keyValue, notice } from "../../widgets.js";
import { humanize, plural, relativeTime } from "../../words.js";
import { actionBlock, areaHead, installButton, pathText, reloadAfterStart, stateCard, statusPill } from "./workbench_kit.js";

const CONTROL = "agents computer control";
const HELPER = "agent-desktop";
const PERMISSIONS = {
  accessibility: { title: "Control apps", body: "Press buttons, type, and read what a window contains.", glyph: "pointer" },
  screen_recording: { title: "See the screen", body: "Take pictures of the screen to understand what is showing.", glyph: "eye" },
  automation: { title: "Talk to other apps", body: "Ask apps such as Finder or a browser to do things.", glyph: "bolt" },
};
const GRANTS = { granted: ["Allowed", "good", "check"], denied: ["Not allowed", "bad", "close"], unknown: ["Not checked yet", "warn", "alert"] };
const SETTINGS_HINTS = { macos: "Change these in System Settings › Privacy & Security." };
const PLATFORMS = { macos: "macOS", linux: "Linux", windows: "Windows" };
const ACTIONS = [
  { path: CONTROL, blurb: "Agents can look at the screen, move the pointer and type. It stays on until you stop it." },
  { path: CONTROL, title: "Turn on in gentle mode", blurb: "Agents can press buttons and read windows, but never take over your mouse or keyboard.", preset: { headless: "on" } },
  { path: "agents add-mcp", title: "Connect an agent to it", blurb: "Add desktop control to an agent's tools so it can start using this computer.", preset: { requested_mcp_servers: HELPER } },
];

export function createComputerArea({ activity, tools }, { setStatus }) {
  const turnOn = (tone) => toolButton(tools, CONTROL, { label: "Turn it on", glyph: "power", tone });

  function endpointCard(endpoint) {
    if (endpoint.state === "running") {
      return stateCard({
        tone: "good", glyph: "power", title: "Desktop control is on",
        body: "Agents that are connected can use this computer right now. To turn it off, stop it where it was started: under Activity if that was here.",
        children: keyValue([
          ["Address for agents", copyChip(endpoint.mcp_url)],
          ["Older style address", copyChip(endpoint.sse_url)],
          ["Last used", endpoint.last_activity ? relativeTime(endpoint.last_activity) : null],
          ["Connected now", endpoint.active_sse_connections === null ? null : plural(endpoint.active_sse_connections, "agent")],
        ]),
      });
    }
    if (endpoint.state === "foreign") {
      return stateCard({
        tone: "bad", glyph: "alert", title: "Something else is using its address",
        body: `Another program already answers at ${new URL(endpoint.mcp_url).host}. Close that program, or pick a different port under Options and when you turn it on.`,
      });
    }
    return stateCard({
      glyph: "power", title: "Desktop control is off", body: "No agent can touch this computer. Turn it on when you want one to work in your apps for you.",
      actions: [turnOn("primary"), toolButton(tools, CONTROL, { label: "Gentle mode", glyph: "eye", preset: { headless: "on" } })],
    });
  }

  function permissionList(helper) {
    const entries = Object.entries(helper.permissions);
    const waiting = entries.some(([, grant]) => grant !== "granted");
    return h(
      "div",
      { class: "wb-permissions" },
      h("div", { class: "wb-line" }, h("span", { class: "stat-label", text: "What this computer lets it do" }), waiting && SETTINGS_HINTS[helper.platform] && h("span", { class: "wb-note", text: SETTINGS_HINTS[helper.platform] })),
      h(
        "ul",
        {},
        entries.map(([name, grant]) => {
          const known = PERMISSIONS[name] ?? { title: humanize(name), body: "", glyph: "shield" };
          const granted = statusPill(...(GRANTS[grant] ?? [humanize(grant), toneOf(grant), null]));
          return h("li", {}, h("header", {}, h("span", { class: "wb-permission-glyph" }, icon(known.glyph, 17)), h("strong", { text: known.title }), granted), known.body && h("p", { class: "wb-note", text: known.body }));
        }),
      ),
    );
  }

  const panel = createLivePanel({
    title: "Right now", path: "agents computer status", extra: ["--json"],
    render: (data, { setCount }) => {
      const helper = data?.agent_desktop;
      const endpoint = data?.endpoint;
      if (!helper) {
        setCount("");
        setStatus("Not set up", "warn");
        return notice({
          glyph: "monitor", title: "The desktop helper isn't installed yet",
          body: "Desktop control works through a small helper app that looks at the screen and presses keys on an agent's behalf. Install it, then come back here.",
          action: installButton(tools, HELPER, "Install the helper"),
        });
      }
      setCount(`helper ${helper.version}`);
      setStatus(endpoint.state === "running" ? "On" : endpoint.state === "foreign" ? "Address in use" : "Off", endpoint.state === "running" ? "good" : endpoint.state === "foreign" ? "bad" : "");
      return h("div", { class: "stack" }, endpointCard(endpoint), permissionList(helper), h("p", { class: "wb-note" }, `Helper app ${helper.version} for ${PLATFORMS[helper.platform] ?? helper.platform} · `, pathText(helper.executable)));
    },
  });
  reloadAfterStart(activity, CONTROL, panel);

  const element = h(
    "div",
    { class: "wb-area" },
    areaHead({ title: "Desktop control", lede: "Let an agent use this computer the way you do: look at the screen, click, type, and work in any app." }),
    panel.element,
    actionBlock(tools, "Use it", ACTIONS),
  );
  return { element, show: () => panel.ensure() };
}
