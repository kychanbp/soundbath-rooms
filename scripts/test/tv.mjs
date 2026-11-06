import { chromium } from 'playwright-core';
import http from 'http'; import fs from 'fs'; import path from 'path';
const WEB = path.resolve(process.cwd(), '../../web');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.m4a': 'audio/mp4', '.png': 'image/png' };
const srv = http.createServer((q, r) => { const p = path.join(WEB, decodeURIComponent(q.url.split('?')[0]).replace(/\/$/, '/index.html')); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(d); }); }).listen(8768);
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: false, args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required', '--window-size=1400,850'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
p.on('pageerror', e => console.log('[pageerror]', e.message));
await p.goto('http://localhost:8768/index.html?auto=1');
await p.waitForFunction('window.__ready===true', null, { timeout: 90000 }); await p.waitForTimeout(1000);
await p.evaluate(() => { document.body.classList.add('nohud'); for (const id of ['fade', 'help', 'title']) { const e = document.getElementById(id); e.style.transition = 'none'; e.style.opacity = 0; } });
const names = (process.argv[2] || 'himalayan,crystal,gong,rain,rin,strings,cave').split(',');
for (const n of names) {
  await p.evaluate(n => { const m = window.__rooms[n].meta, t = m.teacher; const d = [m.door[0] - t.pos[0], m.door[1] - t.pos[1]], l = Math.hypot(...d), f = t.pose === 'stand' ? -1 : 1; 
    const dist = 2.0; const x = t.pos[0] + d[0] / l * dist, y = t.pos[1] + d[1] / l * dist; window.__shot = [x, y, 1.1, Math.atan2(d[0], -d[1]) * 180 / Math.PI, -8]; }, n);
  await p.waitForFunction(n => window.__rooms[n].teacher, n, { timeout: 60000 }).catch(() => console.log('no teacher', n));
  await p.waitForTimeout(9000); await p.screenshot({ path: `../../renders/t_${n}.jpg`, type: 'jpeg', quality: 88 });
}
await b.close(); srv.close();
