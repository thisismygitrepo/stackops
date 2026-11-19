import { h } from "/assets/scripts/dom.js";

const STAGGER_LIMIT = 22;
const BURST_COLORS = ["#6a5cff", "#1ea7fd", "#12c99b", "#f5a524", "#f0527a"];

const reducedMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function rise(container, selector) {
  const items = selector ? container.querySelectorAll(selector) : container.children;
  [...items].forEach((item, index) => {
    item.style.setProperty("--i", String(Math.min(index, STAGGER_LIMIT)));
    item.classList.add("rise");
  });
  return container;
}

export function replay(element, className) {
  element.classList.remove(className);
  void element.offsetWidth;
  element.classList.add(className);
}

export function countUp(element, target, format = (value) => Math.round(value).toLocaleString()) {
  const from = Number(element.dataset.value ?? 0);
  element.dataset.value = String(target);
  if (reducedMotion() || from === target) {
    element.textContent = format(target);
    return;
  }
  const started = performance.now();
  const frame = (now) => {
    const progress = Math.min((now - started) / 900, 1);
    element.textContent = format(from + (target - from) * (1 - (1 - progress) ** 4));
    if (progress < 1 && element.dataset.value === String(target)) requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}

export function burst(anchor) {
  if (reducedMotion()) return;
  const box = anchor.getBoundingClientRect();
  const origin = h("div", { class: "burst", style: `left:${box.left + box.width / 2}px;top:${box.top + box.height / 2}px` });
  for (let index = 0; index < 16; index += 1) {
    const angle = (index / 16) * Math.PI * 2 + Math.random() * 0.4;
    const reach = 46 + Math.random() * 54;
    origin.append(h("i", { style: `--dx:${Math.cos(angle) * reach}px;--dy:${Math.sin(angle) * reach}px;--tint:${BURST_COLORS[index % BURST_COLORS.length]};--spin:${Math.random() * 360}deg` }));
  }
  document.body.append(origin);
  setTimeout(() => origin.remove(), 900);
}

export function installPointerEffects() {
  let lit = null;
  document.addEventListener("pointermove", (event) => {
    const target = event.target instanceof Element ? event.target.closest(".lit") : null;
    if (lit && lit !== target) {
      lit.style.setProperty("--rx", "0deg");
      lit.style.setProperty("--ry", "0deg");
    }
    lit = target;
    if (!target) return;
    const box = target.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width;
    const y = (event.clientY - box.top) / box.height;
    target.style.setProperty("--mx", `${x * 100}%`);
    target.style.setProperty("--my", `${y * 100}%`);
    target.style.setProperty("--rx", `${(0.5 - y) * 4}deg`);
    target.style.setProperty("--ry", `${(x - 0.5) * 4}deg`);
  });
  document.addEventListener("pointerdown", (event) => {
    const target = event.target instanceof Element ? event.target.closest(".btn, .rail-item, .chip-button") : null;
    if (!target || reducedMotion()) return;
    const box = target.getBoundingClientRect();
    const size = Math.max(box.width, box.height) * 2;
    const wave = h("span", { class: "ripple", style: `width:${size}px;height:${size}px;left:${event.clientX - box.left - size / 2}px;top:${event.clientY - box.top - size / 2}px` });
    target.append(wave);
    setTimeout(() => wave.remove(), 600);
  });
}
