// Usage: node shot.mjs out.jpg "room" x y z yaw pitch
import { chromium } from 'playwright-core';
import http from 'http'; import fs from 'fs'; import path from 'path';
const WEB = path.resolve(process.cwd(), '../../web');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.gltf': 'model/gltf+json', '.m4a': 'audio/mp4', '.png': 'image/png' };
const srv = http.createServer((q, r) => { const p = path.join(WEB, decodeURIComponent(q.url.split('?')[0]).replace(/\/$/, '/index.html')); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); }).listen(8765);
const [out, room, ...views] = process.argv.slice(2);
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: false, args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required', '--window-size=1400,850'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
p.on('console', m => { const t = m.text(); if (m.type() === 'error' || m.type() === 'warning' && /shader|THREE|WebGL/i.test(t)) console.log('[' + m.type() + ']', t.slice(0, 1600)); });
p.on('pageerror', e => console.log('[pageerror]', e.message));
await p.goto(`http://localhost:8765/index.html?room=${room}&auto=1`);
await p.waitForFunction('window.__ready===true', null, { timeout: 90000 }).catch(e => console.log('not ready'));
await p.waitForTimeout(1500);
await p.evaluate(() => { document.getElementById('fade').style.transition='none'; document.getElementById('fade').style.opacity = 0; document.getElementById('hud').style.display='none'; document.getElementById('help').style.display='none'; document.getElementById('title').style.display='none'; });
for (let i = 0; i < views.length; i++) {
  const v = views[i].split(',').map(Number);
  await p.evaluate(v => { window.__shot = v; }, v);
  await p.waitForTimeout(2500);
  const f = out.replace('.jpg', `_${i}.jpg`);
  await p.screenshot({ path: f, type: 'jpeg', quality: 90 }); console.log('saved', f);
}
const st = await p.evaluate(() => ({ calls: window.__renderer.info.render.calls, tris: window.__renderer.info.render.triangles, geos: window.__renderer.info.memory.geometries, tex: window.__renderer.info.memory.textures, audio: Object.keys(window.__audio?.rooms ?? {}) }));
console.log(JSON.stringify(st));
await b.close(); srv.close();
