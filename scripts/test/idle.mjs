import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); let e = 0; p.on('pageerror', x => { e++; console.log('[pageerror]', x.message); });
await p.goto('http://localhost:8000/index.html?auto=1'); await p.waitForFunction('window.__ready===true', null, { timeout: 90000 }); await p.waitForTimeout(500);
await p.evaluate(() => { document.body.classList.add('nohud'); for (const id of ['fade', 'help', 'title', 'home']) { const x = document.getElementById(id); x.style.transition = 'none'; x.style.opacity = 0; if (id !== 'fade') x.style.display = 'none'; } });
await p.evaluate(() => { const m = __rooms; }); await p.evaluate(n => { window.__shot = [-7.9, 6, 1.0, 90, -6]; }, 0);
await p.waitForFunction(() => __rooms.himalayan.teacher?.seat, null, { timeout: 60000 });
await p.evaluate(() => { const A = __audio; A.leaveRange('himalayan'); __rooms.himalayan.teacher.q.R.length = 0; __rooms.himalayan.teacher.q.L.length = 0; window.__rooms.himalayan.teacher.act = () => {}; });
const log = await p.evaluate(async () => { const T = __rooms.himalayan.teacher, h = T.bones.Head; const out = []; let prev = null, mx = 0; const V = T.pos.constructor; for (let i = 0; i < 300; i++) { await new Promise(r => requestAnimationFrame(r)); const v = h.getWorldPosition(new V()); if (prev) mx = Math.max(mx, v.distanceTo(prev)); prev = v; if (i % 30 === 0) out.push([+v.x.toFixed(3), +v.y.toFixed(3), +v.z.toFixed(3)]); } return { mx: +mx.toFixed(4), out }; });
console.log(JSON.stringify(log));
for (let i = 0; i < 4; i++) { await p.waitForTimeout(3200); await p.screenshot({ path: `../../renders/idle${i}.jpg`, type: 'jpeg', quality: 85 }); }
console.log('errors', e); await b.close();
