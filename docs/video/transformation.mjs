import { readFileSync } from 'node:fs';
import { C, box, text, lines } from './drawing.mjs';

const before = `data:image/png;base64,${readFileSync(new URL('../assets/before.png', import.meta.url)).toString('base64')}`;
const after = `data:image/png;base64,${readFileSync(new URL('../assets/after.png', import.meta.url)).toString('base64')}`;

export function transformation(scene, focus) {
  const minutes = focus === 'minutes';
  let body = lines(scene.Title[0], 100, 218, 64, C.ink, 1100, 650)
    + text(scene.Subtitle[0], 104, 384, 29, C.muted, 400, false);
  const panels = [
    { x: 100, image: before, label: 'BEFORE', detail: 'A bare machine', active: focus === 'bare', opacity: focus === 'familiar' ? 0.4 : 1 },
    { x: 1008, image: after, label: 'AFTER', detail: 'The familiar setup you made yours', active: focus !== 'bare', opacity: focus === 'bare' ? 0.3 : 1 },
  ];
  for (const panel of panels) {
    body += `<g opacity="${panel.opacity}">`
      + box(panel.x, 432, 812, 340, C.panel, panel.active ? C.accent : C.edge, 18)
      + `<image href="${panel.image}" x="${panel.x + 16}" y="448" width="780" height="272" preserveAspectRatio="xMidYMid meet"/>`
      + text(panel.label, panel.x + 24, 752, 19, panel.active ? C.accent : C.muted, 600, true)
      + text(panel.detail, panel.x + 124, 752, 23, C.ink, 500, false)
      + '</g>';
  }
  body += `<path d="M934 595h47m-16-16 16 16-16 16" fill="none" stroke="${focus === 'bare' ? C.edge : C.accent}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>`;
  if (minutes) {
    body += box(1250, 176, 570, 152, C.selected, C.accent, 18)
      + text('THE GOAL', 1280, 218, 22, C.accent, 600, true)
      + text('1 command + 5 minutes', 1280, 284, 38, C.ink, 600, false);
  }
  return body;
}
