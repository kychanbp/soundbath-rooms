import { chromium } from 'playwright-core';
import http from 'http'; import fs from 'fs'; import path from 'path';
const WEB = path.resolve(process.cwd(), '../../web');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.m4a': 'audio/mp4' };
const srv = http.createServer((q, r) => { const p = path.join(WEB, decodeURIComponent(q.url.split('?')[0]).replace(/\/$/, '/index.html')); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream' }); r.end(d); }); }).listen(8766);
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: false, args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required', '--window-size=1400,850'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
let errs = 0; p.on('pageerror', e => { errs++; console.log('[pageerror]', e.message); }); p.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) { errs++; console.log('[err]', m.text().slice(0, 300)); } });
await p.goto('http://localhost:8766/index.html?auto=1');
await p.waitForFunction('window.__ready===true', null, { timeout: 90000 });
const R = [['himalayan', 0, 6, 90], ['crystal', 0, 6, -90], ['gong', 0, 19, 90], ['rain', 0, 19, -90], ['rin', 0, 32, 90], ['strings', 0, 32, -90], ['cave', 0, 34, 0]];
for (const [name, x, y, yaw] of R) {
  await p.evaluate(([x, y, yaw]) => { const s = window.__state; s.x = x; s.y = y; s.yaw = yaw * Math.PI / 180; s.pitch = 0; s.sit = 0; s.sitT = 0; s.target = null; }, [x, y, yaw]);
  await p.waitForTimeout(600);
  await p.keyboard.down('KeyW'); await p.keyboard.down('ShiftLeft');
  await p.waitForTimeout(name === 'cave' ? 5500 : 3200);
  await p.keyboard.up('KeyW'); await p.keyboard.up('ShiftLeft');
  const pos = await p.evaluate(() => [window.__state.x, window.__state.y]);
  await p.waitForFunction(n => window.__audio.rooms[n]?.ready, name, { timeout: 40000 }).catch(() => console.log('audio not ready', name));
  await p.keyboard.press('KeyM');
  const q = await p.evaluate(async n => {
    const A = window.__audio, an = A.ctx.createAnalyser(); an.fftSize = 8192; A.master.connect(an);
    const d = new Float32Array(8192); let frames = 0, run = true; const loop = () => { frames++; if (run) requestAnimationFrame(loop); }; loop();
    let e = 0, pk = 0, k = 0; const f = new Float32Array(4096), sp = new Float32Array(4096);
    for (let i = 0; i < 24; i++) { await new Promise(r => setTimeout(r, 500)); an.getFloatTimeDomainData(d); let s = 0; for (const v of d) { s += v * v; pk = Math.max(pk, Math.abs(v)); } e += s / 8192; k++; an.getFloatFrequencyData(f); f.forEach((v, j) => sp[j] += 10 ** (v / 10)); }
    run = false; A.master.disconnect(an); let m = 0, c = 0; sp.forEach((v, j) => { m += v; c += v * j * 24000 / 4096; });
    return { n, rms: +Math.sqrt(e / k).toFixed(4), peak: +pk.toFixed(3), centroid: Math.round(c / m), fps: Math.round(frames / 12), sit: window.__state.sit, sitT: +window.__state.sitT.toFixed(2), calls: window.__renderer.info.render.calls, tris: window.__renderer.info.render.triangles };
  }, name);
  console.log(JSON.stringify({ ...q, pos: pos.map(v => +v.toFixed(2)) }));
  await p.keyboard.press('KeyM'); await p.waitForTimeout(300);
}
console.log('errors', errs); await b.close(); srv.close();
