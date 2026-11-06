import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const url = process.argv[2] || 'http://localhost:8793/index.html?auto=1';
const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); let e = 0; p.on('pageerror', x => { e++; console.log('[pageerror]', x.message.slice(0, 200)); }); p.on('console', m => { if (/Shader Error|ERROR:/.test(m.text())) { e++; console.log(m.text().slice(0, 400)); } });
const t0 = Date.now(); await p.goto(url); await p.waitForFunction('window.__ready===true', null, { timeout: 150000 }); console.log('ready', Math.round((Date.now() - t0) / 1000), 's'); await p.waitForTimeout(1500);
console.log(JSON.stringify(await p.evaluate(() => __world.fieldStats)));
await p.evaluate(() => { document.getElementById('help').style.display = 'none'; });
const r = await p.evaluate(async () => { const s = __state; s.x = 3.2; s.y = -58; s.yaw = 0; const T = []; let last = performance.now(); return await new Promise(res => { let n = 0; const go = () => { const now = performance.now(); T.push(now - last); last = now; s.y += .03; n++; if (n < 420) requestAnimationFrame(go); else { T.shift(); T.sort((a, b) => a - b); res({ frames: T.length, p50: +T[T.length >> 1].toFixed(1), p99: +T[Math.floor(T.length * .99)].toFixed(1), max: +T[T.length - 1].toFixed(1), y: +s.y.toFixed(1), calls: __renderer.info.render.calls, tris: __renderer.info.render.triangles }); } }; requestAnimationFrame(go); }); });
console.log('walking frame ms', JSON.stringify(r));
for (const [i, v] of [[-1, -30, 1.65, 50, -4], [2, 14, 1.65, 0, -3], [-20, 40, 1.65, 30, -3]].entries()) { await p.evaluate(v => { window.__shot = [v[0], v[1], v[2] + __heightAt(v[0], v[1]), v[3], v[4]]; }, v); await p.waitForTimeout(1500); await p.screenshot({ path: `../../renders/g${i}.jpg`, type: 'jpeg', quality: 84 }); }
console.log('errors', e); await b.close();
