import { chromium } from 'playwright-core';
const b = await chromium.launch({ executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: false, args: ['--use-angle=metal', '--autoplay-policy=no-user-gesture-required', '--window-size=1400,850'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
p.on('pageerror', e => console.log('[pageerror]', e.message)); p.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) console.log('[err]', m.text().slice(0, 500)); });
await p.goto('http://localhost:8000/index.html?room=himalayan&auto=1');
await p.waitForFunction('window.__ready===true', null, { timeout: 90000 }); await p.waitForTimeout(1500);
await p.evaluate(() => { for (const id of ['fade','hud','help','title','pad','rooms']) { const e = document.getElementById(id); e.style.transition='none'; e.style.opacity=0; } });
const views = process.argv.slice(2);
for (let i = 0; i < views.length; i++) { await p.evaluate(v => { window.__shot = v; }, views[i].split(',').map(Number)); await p.waitForTimeout(i ? 3000 : 6000); await p.screenshot({ path: `../../renders/th_${i}.jpg`, type: 'jpeg', quality: 90 }); }
await b.close();
