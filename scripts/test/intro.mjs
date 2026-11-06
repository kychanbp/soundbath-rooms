import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: true, args: ['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } }); let e = 0; p.on('pageerror', x => { e++; console.log('[pageerror]', x.message); }); p.on('console', m => { if (/Shader Error|ERROR/.test(m.text())) { e++; console.log(m.text().slice(0, 300)); } });
await p.goto('http://localhost:8000/index.html?intro=1'); await p.click('#enter'); await p.waitForFunction('window.__ready===true', null, { timeout: 120000 });
for (let i = 0; i < 4; i++) { await p.waitForTimeout(3000); await p.screenshot({ path: `../../renders/in${i}.jpg`, type: 'jpeg', quality: 84 }); }
await p.waitForTimeout(3000); console.log('after', await p.evaluate(() => [__state.intro, document.body.className, __state.x, __state.y, __state.pitch]), 'errors', e); await b.close();
