import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { artwork } from './artwork.mjs';
import { renderSunburst } from './sunburst.mjs';

const folder = dirname(fileURLToPath(import.meta.url));
const root = resolve(folder, '../..');
const scratch = resolve(root, '.ai/tmp_scripts/stackops-video');
mkdirSync(scratch, { recursive: true });
const scenes = [];
let scene;
for (const line of readFileSync(resolve(folder, 'stackops-concept.rst'), 'utf8').split('\n')) {
  if (/^Scene \d+/.test(line)) { scene = {}; scenes.push(scene); }
  const field = line.match(/^:([\w-]+): (.*)$/);
  if (field && scene) (scene[field[1]] ??= []).push(field[2]);
}
const manifest = { output: resolve(folder, 'stackops-concept.mp4'), scratch, scenes: [] };
for (const [index, current] of scenes.entries()) {
  if (current.Focus.length !== current.Say.length) throw new Error(`Scene ${index + 1} needs one Focus per Say field`);
  const images = [];
  const sunburst = current.Layout[0] === 'sunburst';
  const captions = current.Say.map((value, beat) => {
    const prefix = resolve(scratch, `scene-${String(index + 1).padStart(2, '0')}-${String(beat + 1).padStart(2, '0')}`);
    if (!sunburst) {
      writeFileSync(prefix + '.svg', artwork(current, index, scenes.length, beat));
      execFileSync('rsvg-convert', ['-o', prefix + '.png', prefix + '.svg']);
    }
    images.push(prefix + '.png');
    const audio = prefix + '.wav';
    return { text: value, audio };
  });
  const animations = sunburst ? renderSunburst(current, index, scenes.length, images) : images.map(() => []);
  manifest.scenes.push({ images, captions, animations });
  console.log(`Prepared scene ${index + 1}: ${current.Title[0].replaceAll('|', ' ')}`);
}
writeFileSync(resolve(scratch, 'manifest.json'), JSON.stringify(manifest, null, 2));
execFileSync('uv', ['run', '--python', '3.13', resolve(folder, 'narrate.py'), resolve(scratch, 'manifest.json')], { cwd: scratch, stdio: 'inherit' });
if (!process.argv.includes('--prepare-only')) {
  execFileSync('swiftc', ['-parse-as-library', '-O', '-module-cache-path', resolve(scratch, 'module-cache'), resolve(folder, 'encode.swift'), '-o', resolve(scratch, 'encode')], { stdio: 'inherit' });
  execFileSync(resolve(scratch, 'encode'), [resolve(scratch, 'manifest.json')], { stdio: 'inherit' });
}
