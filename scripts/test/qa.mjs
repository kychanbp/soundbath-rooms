import { chromium } from 'playwright-core';
import http from 'http'; import fs from 'fs'; import path from 'path';
const WEB = path.resolve(process.cwd(), '../../web');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.m4a': 'audio/mp4', '.png': 'image/png' };
const srv = http.createServer((q, r) => { const p = path.join(WEB, decodeURIComponent(q.url.split('?')[0]).replace(/\/$/, '/index.html')); fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { 'Content-Type': types[path.extname(p)] || 'application/octet-stream', 'Cache-Control': 'no-store' }); r.end(d); }); }).listen(8791);
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: false, args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required', '--window-size=1400,850'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
let errs = 0; p.on('pageerror', e => { errs++; console.log('[pageerror]', e.message); }); p.on('console', m => { if ((m.type() === 'error' && !/404/.test(m.text())) || /Shader Error/.test(m.text())) { errs++; console.log('[err]', m.text().slice(0, 400)); } });
p.on('response', r => { if (r.status() >= 400) console.log('[http]', r.status(), r.url().replace('http://localhost:8791/', '')); });
await p.goto('http://localhost:8791/index.html?auto=1');
await p.waitForFunction('window.__ready===true', null, { timeout: 90000 }); await p.waitForTimeout(2000);
await p.evaluate(() => { document.getElementById('help').style.display = 'none'; });
const seat = async n => { await p.keyboard.press('KeyM'); await p.waitForFunction(() => window.__state.sit === 1, null, { timeout: 25000 }).catch(() => console.log('NO SIT', n)); await p.waitForTimeout(3500); const s = await p.evaluate(() => [window.__state.sitT, window.__state.pitch]); await p.screenshot({ path: '../../renders/lie_' + n + '.jpg', type: 'jpeg', quality: 82 }); await p.keyboard.press('KeyM'); await p.waitForFunction(() => !window.__state.target, null, { timeout: 25000 }).catch(() => console.log('NO RETURN', n)); return s.map(v => +v.toFixed(2)); };
const secs = +process.argv[2] || 35;
const names = ['himalayan', 'crystal', 'gong', 'rain', 'rin', 'strings', 'cave'];
for (const n of names) {
  await p.click('#bRooms'); await p.click(`#rooms button[data-room="${n}"]`); await p.waitForTimeout(1200);
  await p.waitForFunction(n => window.__audio.rooms[n]?.ready && window.__rooms[n].teacher, n, { timeout: 60000 }).catch(() => console.log('NOT READY', n));
  const q = await p.evaluate(async ([n, secs]) => {
    const R = window.__rooms[n], T = R.teacher, A = window.__audio; const log = []; const orig = T.act.bind(T); T.act = (mv, id, w, nw, len) => { log.push([id, mv.kind, +(w - nw).toFixed(2)]); orig(mv, id, w, nw, len); };
    const an = A.ctx.createAnalyser(); an.fftSize = 8192; A.master.connect(an); const d = new Float32Array(8192); let e = 0, k = 0, fr = 0, run = true, miss = 0, cnt = 0, maxmiss = 0, late = 0;
    const H = new (T.hand.R.constructor)(); const loop = () => { fr++; for (const s of ['R', 'L']) { const ev = T.q[s][0]; if (ev && ev.w > .98) { T.arms[s][2].getWorldPosition(H); const m = H.distanceTo(T.hand[s]); cnt++; miss += m; maxmiss = Math.max(maxmiss, m); } if (T.q[s].length && A.ctx.currentTime > T.q[s][0].t1 + .1 && T.q[s][0].t1 - T.q[s][0].t0 > 0 && T.q[s][0] !== T.q[s].__c) { } } if (run) requestAnimationFrame(loop); }; loop();
    for (let i = 0; i < secs * 2; i++) { await new Promise(r => setTimeout(r, 500)); an.getFloatTimeDomainData(d); let s = 0; for (const v of d) s += v * v; e += s / 8192; k++; }
    run = false; A.master.disconnect(an); T.act = orig;
    return { n, rms: +Math.sqrt(e / k).toFixed(4), fps: Math.round(fr / secs), acts: log.length, kinds: [...new Set(log.map(x => x[0] + ':' + x[1]))].slice(0, 9), reachErr: cnt ? +(miss / cnt).toFixed(3) : null, reachMax: +maxmiss.toFixed(3), calls: window.__renderer.info.render.calls, tris: window.__renderer.info.render.triangles, q: [T.q.R.length, T.q.L.length] };
  }, [n, secs]);
  console.log(JSON.stringify(q));
  console.log('lie', n, JSON.stringify(await seat(n)), await p.evaluate(() => { const s = window.__state; return window.__free(s.x, s.y); }));
}
// flood fill over the walkable area from the spawn
const f = await p.evaluate(() => {
  const free = window.__free, w = window.__world, S = .1, seen = new Set(), st = [[Math.round(w.spawn[0] / S), Math.round(w.spawn[1] / S)]]; seen.add(st[0].join());
  while (st.length) { const [i, j] = st.pop(); for (const [a, b] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const k = (i + a) + ',' + (j + b); if (!seen.has(k) && free((i + a) * S, (j + b) * S)) { seen.add(k); st.push([i + a, j + b]); } } }
  const out = {}; for (const n of w.rooms) { const m = window.__rooms[n].meta; out[n] = { seats: m.seats.map(s => { const near = seen.has(Math.round(s.pos[0] / S) + ',' + Math.round(s.pos[1] / S)); return near; }), cells: 0 }; }
  let stray = 0; for (const k of seen) { const [i, j] = k.split(',').map(Number), x = i * S, y = j * S; const r = w.rooms.find(n => { const b = window.__rooms[n].meta.box; return x > b[0] && x < b[3] && y > b[1] && y < b[4]; }); if (r) out[r].cells++; }
  return { total: seen.size, stray, out };
});
console.log(JSON.stringify(f));
// leave and enter again
await p.click('#bSettings'); await p.waitForTimeout(450); await p.click('#bHome'); await p.waitForTimeout(800); await p.click('#enter'); await p.waitForTimeout(6000);
console.log('reenter', await p.evaluate(() => [window.__audio.ctx?.state, Object.keys(window.__audio.buf).length, document.body.className, window.__state.x]));
console.log('errors', errs); await b.close(); srv.close();
