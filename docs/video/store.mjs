import { readFileSync } from 'node:fs';
import { C, box, text, lines } from './drawing.mjs';

const photo = `data:image/jpeg;base64,${readFileSync(new URL('../assets/stackops.jpeg', import.meta.url)).toString('base64')}`;

export function store(scene, focus) {
  return box(100, 150, 472, 624, C.panel, C.accent, 18)
    + `<image href="${photo}" x="108" y="158" width="456" height="608" preserveAspectRatio="xMidYMid meet"/>`
    + text(scene.Title[0], 640, 236, 76, C.ink, 650, false)
    + lines(scene.Statement[0], 644, 324, 42, C.ink, 1176, 500)
    + lines(scene.Payoff[0], 644, 536, 40, focus === 'done' ? C.accent : C.ink, 1176, 600)
    + lines(scene.Note[0], 644, 696, 28, C.muted, 1176, 400);
}
