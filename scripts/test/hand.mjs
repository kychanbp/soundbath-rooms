import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
p.on('pageerror', e => console.log('[pageerror]', e.message));
await p.goto('http://localhost:8000/index.html?auto=1');
await p.waitForFunction('window.__ready===true', null, { timeout: 90000 }); await p.waitForTimeout(800);
await p.evaluate(() => { document.body.classList.add('nohud'); for (const id of ['fade', 'help', 'title', 'home']) { const e = document.getElementById(id); e.style.transition = 'none'; e.style.opacity = 0; if (id==='title'||id==='home') e.style.display='none'; } });
const names = (process.argv[2] || 'himalayan,gong,cave').split(',');
for (const n of names) {
  await p.evaluate(n => { const m = window.__rooms[n].meta, t = m.teacher; const d = [m.door[0] - t.pos[0], m.door[1] - t.pos[1]], l = Math.hypot(...d); window.__shot = [t.pos[0] + d[0] / l * 2, t.pos[1] + d[1] / l * 2, 1.1, 0, 0]; }, n);
  await p.waitForFunction(n => window.__rooms[n].teacher?.seat, n, { timeout: 60000 }).catch(() => console.log('no', n));
  // wait for the right hand to be mid gesture, or take rest
  for (const [tag, want] of [['rest', 0], ['play', 1]]) {
    const got = await p.waitForFunction(w => { const T = window.__rooms[window.__cname]?.teacher; return true; }, want).catch(() => 0);
    await p.evaluate(([n, want]) => { window.__cname = n; }, [n, want]);
    if (want) await p.waitForFunction(n => { const T = window.__rooms[n].teacher; return (T.q.R[0]?.w ?? 0) > .9 || (T.q.L[0]?.w ?? 0) > .9; }, n, { timeout: 45000 }).catch(() => console.log('no play', n));
    else await p.waitForFunction(n => { const T = window.__rooms[n].teacher; return !T.q.R[0] && !T.q.L[0]; }, n, { timeout: 45000 }).catch(() => 0);
    const pt = await p.evaluate(n => { const T = window.__rooms[n].teacher, cam = window.__cam, out = {}; for (const s of ['R', 'L']) { const w = T.bones[s + ' Hand'].getWorldPosition(new T.pos.constructor()); out[s] = [w.x, w.y, w.z]; } return out; }, n);
    await p.evaluate(([pt, s]) => { const v = pt[s]; window.__shot = [v[0] * .55 + (window.__shot[0]) * .45 + .0, -v[2] * .55 + window.__shot[1] * .45, v[1] + .28, 0, 0]; }, [pt, 'R']);
    await p.evaluate(([pt]) => { const v = pt.R, S = window.__shot, dx = v[0] - S[0], dy = -v[2] - S[1], dz = v[1] - S[2]; S[3] = Math.atan2(-dx, dy) * 180 / Math.PI; S[4] = Math.atan2(dz, Math.hypot(dx, dy)) * 180 / Math.PI; }, [pt]);
    await p.waitForTimeout(350); await p.screenshot({ path: `../../renders/h_${n}_${tag}.jpg`, type: 'jpeg', quality: 86 });
  }
}
await b.close();
