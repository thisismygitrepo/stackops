import { h } from "/assets/scripts/dom.js";
import { stretchesOf } from "./model.js";
import { share, size, volumeName } from "./words.js";

const TIP_GAP = 10;
const tip = h("div", { class: "devices-tip", role: "tooltip", hidden: true });

// One readout for every bar on the page, placed over the stretch the pointer or the keyboard is on. The amount leads and the name follows:
// whoever points at a stretch already sees which one it is.
function showTip(target, amount, label) {
  if (!tip.isConnected) document.body.append(tip);
  tip.replaceChildren(h("strong", { text: amount }), h("span", { text: label }));
  tip.hidden = false;
  const box = target.getBoundingClientRect();
  const width = tip.offsetWidth;
  tip.style.left = `${Math.max(12, Math.min(box.left + box.width / 2 - width / 2, window.innerWidth - width - 12))}px`;
  tip.style.top = `${Math.max(12, box.top - tip.offsetHeight - TIP_GAP)}px`;
}

function readout(stretch, disk) {
  const of = share(stretch.bytes, disk.size);
  if (stretch.kind === "used") return [size(stretch.bytes), `${volumeName(stretch.volume)} · ${of} of this disk`];
  if (stretch.kind === "room") return stretch.volume.used === null ? [size(stretch.bytes), `${volumeName(stretch.volume)} · not mounted, so how full it is does not show`] : [`${size(stretch.bytes)} free`, `in ${volumeName(stretch.volume)}`];
  if (stretch.kind === "parts") return [size(stretch.bytes), `System parts · ${of} of this disk`];
  if (stretch.kind === "free") return [`${size(stretch.bytes)} free`, `${of} of this disk`];
  return [size(stretch.bytes), "Not in use by any volume this computer can read"];
}

// A disk from end to end as one thin bar. The rows under it carry each volume's name and amounts beside a dot of the same colour, so the bar
// prints nothing itself; the line under it names the two things no row stands for. `onPoint` hears which volume a stretch belongs to while
// the pointer or the keyboard is on it, and null when it leaves.
export function spaceMap(disk, onPoint) {
  const stretches = stretchesOf(disk);
  const total = stretches.reduce((sum, stretch) => sum + stretch.bytes, 0);
  const marks = stretches.map((stretch) => {
    const [amount, label] = readout(stretch, disk);
    const key = stretch.volume ? stretch.volume.id : stretch.kind;
    const enter = () => {
      showTip(mark, amount, label);
      onPoint(key);
    };
    const leave = () => {
      tip.hidden = true;
      onPoint(null);
    };
    const mark = h("i", { class: `devices-stretch ${stretch.kind}`, "data-slot": stretch.slot, "data-key": key, style: `--part:${(stretch.bytes / total).toFixed(6)}`, tabindex: "0", role: "img", "aria-label": `${label}: ${amount}`, onpointerenter: enter, onpointerleave: leave, onfocus: enter, onblur: leave });
    return mark;
  });
  const amountOf = (kind) => stretches.filter((stretch) => stretch.kind === kind).reduce((sum, stretch) => sum + stretch.bytes, 0);
  const legend = [["parts", "System parts"], ["free", "Free"], ["blank", "Not in use"]].filter(([kind]) => amountOf(kind) > 0);
  return h(
    "div",
    { class: "devices-map" },
    h("div", { class: "devices-bar" }, marks),
    legend.length > 0 && h("p", { class: "devices-legend" }, legend.map(([kind, label]) => h("span", {}, h("i", { class: `devices-key ${kind}` }), `${label} `, h("b", { class: "num", text: size(amountOf(kind)) })))),
  );
}

export const hideTip = () => (tip.hidden = true);
