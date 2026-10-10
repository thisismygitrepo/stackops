import { readFileSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { C, box, text, lines, frame } from './drawing.mjs';

const graph = JSON.parse(readFileSync(new URL('../../src/stackops/scripts/python/graph/cli_graph.json', import.meta.url), 'utf8'));
const palette = ['#8b5cf6', '#319980', '#397cc4', '#ad6096', '#b68a33', '#6d80cf', '#388ca1', '#b36661'];
const center = { x: 1350, y: 456 };
const radius = 316;
const turn = Math.PI * 2;
const nodes = [];

function measure(node) {
  const children = (node.children ?? []).map(measure);
  return { name: node.name, id: node.fullPath || 'stackops', children, value: children.length ? children.reduce((sum, child) => sum + child.value, 0) : 1 };
}

function partition(node, start, end, depth, color) {
  nodes.push({ ...node, start, end, depth, color });
  let angle = start;
  node.children.forEach((child, index) => {
    const next = angle + (end - start) * child.value / node.value;
    partition(child, angle, next, depth + 1, depth === 0 ? palette[index % palette.length] : color);
    angle = next;
  });
}
partition(measure(graph.root), 0, turn, 0, C.selected);

function sector(start, end, inner, outer) {
  const a = start - Math.PI / 2;
  const b = end - Math.PI / 2;
  if (end - start >= turn - 0.001) {
    return `M0,${-outer}A${outer},${outer} 0 1 1 0,${outer}A${outer},${outer} 0 1 1 0,${-outer}`
      + (inner ? `M0,${-inner}A${inner},${inner} 0 1 0 0,${inner}A${inner},${inner} 0 1 0 0,${-inner}Z` : 'Z');
  }
  const large = end - start > Math.PI ? 1 : 0;
  const outerStart = `${Math.cos(a) * outer},${Math.sin(a) * outer}`;
  const outerEnd = `${Math.cos(b) * outer},${Math.sin(b) * outer}`;
  if (!inner) return `M0,0L${outerStart}A${outer},${outer} 0 ${large} 1 ${outerEnd}Z`;
  return `M${outerStart}A${outer},${outer} 0 ${large} 1 ${outerEnd}L${Math.cos(b) * inner},${Math.sin(b) * inner}A${inner},${inner} 0 ${large} 0 ${Math.cos(a) * inner},${Math.sin(a) * inner}Z`;
}

function chart(view) {
  let body = `<g transform="translate(${center.x},${center.y})">`;
  for (const node of nodes) {
    const start = Math.max(0, Math.min(1, (node.start - view.start) / (view.end - view.start))) * turn;
    const end = Math.max(0, Math.min(1, (node.end - view.start) / (view.end - view.start))) * turn;
    const inner = Math.max(0, Math.min(radius, (node.depth - view.depth) * radius / 3));
    const outer = Math.max(0, Math.min(radius, (node.depth + 1 - view.depth) * radius / 3));
    if (end - start < 0.0001 || outer - inner < 0.1) continue;
    body += `<path d="${sector(start, end, inner, outer)}" fill="${node.color}" fill-opacity="${inner ? 0.92 : 1}" fill-rule="evenodd" stroke="${C.bg}" stroke-width="2"/>`;
    if (!inner && end - start > turn - 0.01) {
      body += `<g text-anchor="middle">${text(node.name, 0, 7, 25, C.ink, 600, false)}</g>`;
      continue;
    }
    const middle = (start + end) / 2;
    const distance = (inner + outer) / 2;
    const size = Math.min(21, (outer - inner - 14) / (node.name.length * 0.55));
    if (size < 13 || (end - start) * distance < size + 7) continue;
    const rotation = middle * 180 / Math.PI - 90;
    body += `<g transform="rotate(${rotation}) translate(${distance},0) rotate(${middle > Math.PI ? 180 : 0})" text-anchor="middle">${text(node.name, 0, size * 0.35, size, C.ink, 500, false)}</g>`;
  }
  return body + '</g>';
}

function slide(scene, index, count, beat, view, cursor, pulse) {
  const states = [
    ['COMMAND GROUPS', 'stackops', 'Machine setup, cloud, terminals,|agents, and everyday tools.'],
    ['DEVOPS', 'stackops  ›  devops', 'Install tools · Configure settings|Networking · Security'],
    ['CONFIGURATION', 'stackops  ›  devops  ›  config', 'Public and private settings|Dotfiles · Terminal profiles'],
    ['RELATED TASKS', 'stackops  ›  devops', 'Repositories and data|Back up · Synchronize · Retrieve'],
    ['EVERYDAY WORK', 'stackops', 'Launch commands and workspaces|Orchestrate everyday processes'],
  ];
  const [label, path, detail] = states[beat];
  let body = lines(scene.Title[0], 100, 222, 61, C.ink, 750, 650)
    + text(label, 104, 408, 22, C.accent, 600, true)
    + box(100, 442, 710, 82, C.selected, C.edge, 16)
    + text(path, 122, 493, 25, C.ink, 500, true)
    + lines(detail, 104, 591, 34, C.muted, 700, 400)
    + text('Groups  ›  subgroups  ›  commands', 104, 743, 22, C.accent, 400, true)
    + chart(view);
  if (pulse) body += `<circle cx="${cursor.x}" cy="${cursor.y}" r="${pulse}" fill="none" stroke="${C.mint}" stroke-width="4" opacity="${1 - pulse / 50}"/>`;
  body += `<path transform="translate(${cursor.x},${cursor.y})" d="M0 0v39l10-10 9 18 8-4-9-17h14z" fill="white" stroke="${C.bg}" stroke-width="3" stroke-linejoin="round"/>`;
  return frame(scene, index, count, body, beat).replace('CONCEPTUAL ILLUSTRATION', 'STACKOPS COMMAND EXPLORER');
}

export function renderSunburst(scene, index, count, images) {
  const root = nodes[0];
  const devops = nodes.find(node => node.id === 'devops');
  const config = nodes.find(node => node.id === 'devops config');
  const views = [root, devops, config, devops, root];
  const animations = images.map(() => []);
  let cursor = { x: 1750, y: 722 };
  for (const [beat, imagePath] of images.entries()) {
    const previous = views[Math.max(0, beat - 1)];
    const next = views[beat];
    const svgPath = imagePath.replace(/\.png$/, '.svg');
    writeFileSync(svgPath, slide(scene, index, count, beat, previous, cursor, 0));
    execFileSync('rsvg-convert', ['-o', imagePath, svgPath]);
    if (beat === 0) continue;
    const angle = ((next.start + next.end) / 2 - previous.start) / (previous.end - previous.start) * turn - Math.PI / 2;
    const target = beat < 3 ? { x: center.x + Math.cos(angle) * radius / 2, y: center.y + Math.sin(angle) * radius / 2 } : center;
    for (let step = 0; step < 66; step++) {
      const move = Math.min(1, step / 20);
      const easedMove = move * move * (3 - 2 * move);
      const pointer = { x: cursor.x + (target.x - cursor.x) * easedMove, y: cursor.y + (target.y - cursor.y) * easedMove };
      const progress = Math.max(0, Math.min(1, (step - 24) / 32));
      const zoom = progress * progress * (3 - 2 * progress);
      const view = { start: previous.start + (next.start - previous.start) * zoom, end: previous.end + (next.end - previous.end) * zoom, depth: previous.depth + (next.depth - previous.depth) * zoom };
      const pulse = step > 22 && step < 37 ? (step - 22) * 3 : 0;
      const output = imagePath.replace(/\.png$/, `-frame-${String(step).padStart(3, '0')}.png`);
      writeFileSync(svgPath, slide(scene, index, count, beat, view, pointer, pulse));
      execFileSync('rsvg-convert', ['-o', output, svgPath]);
      animations[beat].push(output);
    }
    cursor = target;
    console.log(`Animated sunburst ${previous.id} → ${next.id}`);
  }
  return animations;
}
