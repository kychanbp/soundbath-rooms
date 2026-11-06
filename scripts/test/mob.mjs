import pw from 'playwright-core';
const { chromium, webkit, devices } = pw;
const sets = [['iphone', webkit, devices['iPhone 14'], 'webkit']];
const sets2 = [['iphone-land', webkit, devices['iPhone 14 landscape'], 'webkit'], ['android', chromium, devices['Pixel 7'], 'chromium'], ['android-land', chromium, devices['Pixel 7 landscape'], 'chromium']];
for (const [name, eng, dev, kind] of [...sets, ...sets2]) {
  const b = await eng.launch(kind === 'chromium' ? { executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless: false, args: ['--use-angle=metal'] } : { headless: true, executablePath: process.env.HOME + '/Library/Caches/ms-playwright/webkit-2227/pw_run.sh' }).catch(e => { console.log('launch fail', name, e.message.slice(0, 200)); return null; });
  if (!b) continue;
  const c = await b.newContext({ ...dev }); const p = await c.newPage();
  let errs = 0; p.on('pageerror', e => { errs++; console.log('[pageerror]', e.message.slice(0, 200)); }); p.on('console', m => { if (m.type() === 'error' && !/404/.test(m.text())) { errs++; console.log('[err]', m.text().slice(0, 240)); } });
  const urls = []; p.on('response', r => urls.push(r.url()));
  await p.goto('http://localhost:8000/index.html'); await p.tap('#enter').catch(e => console.log('tap fail', e.message.slice(0, 120)));
  const ok = await p.waitForFunction('window.__ready===true', null, { timeout: 120000 }).then(() => 1).catch(() => 0);
  if (!ok) { console.log(name, 'NOT READY', await p.textContent('#load')); await p.screenshot({ path: `../../renders/m_${name}.jpg`, type: 'jpeg', quality: 80 }); await b.close(); continue; }
  await p.waitForTimeout(2500); await p.screenshot({ path: `../../renders/m_${name}.jpg`, type: 'jpeg', quality: 80 });
  // hold forward with a touch while looking with another finger is covered by pointer ids; here check walk, room list, sound
  await p.evaluate(() => { const k = document.getElementById('stick'), r = k.getBoundingClientRect(), o = { bubbles: true, pointerId: 7, clientX: r.left + r.width / 2, clientY: r.top + 8 }; k.dispatchEvent(new PointerEvent('pointerdown', o)); });
  await p.waitForTimeout(1500); const s0 = await p.evaluate(() => window.__state.y);
  await p.evaluate(() => { document.getElementById('stick').dispatchEvent(new PointerEvent('pointerup', { bubbles: true, pointerId: 7 })); });
  await p.tap('#bRooms'); await p.waitForTimeout(250); await p.screenshot({ path: `../../renders/m_${name}_rooms.jpg`, type: 'jpeg', quality: 80 });
  await p.tap('#rooms .card[data-room="himalayan"]'); await p.waitForTimeout(9000);
  await p.tap('#bSit'); await p.waitForTimeout(800); 
  await p.waitForFunction(() => window.__audio.rooms.himalayan?.ready, null, { timeout: 40000 }).catch(() => console.log('no live room'));
  const lvl = await p.evaluate(async () => { const A = window.__audio, an = A.ctx.createAnalyser(); an.fftSize = 8192; A.master.connect(an); const d = new Float32Array(8192); let m = 0; for (let i = 0; i < 16; i++) { await new Promise(r => setTimeout(r, 400)); an.getFloatTimeDomainData(d); let s = 0; for (const v of d) s += v * v; m = Math.max(m, Math.sqrt(s / 8192)); } return +m.toFixed(4); });
  console.log(name, 'sound level', lvl);
  const st = await p.evaluate(() => ({ ctx: window.__audio.ctx?.state, sr: window.__audio.ctx?.sampleRate, live: Object.keys(window.__audio.rooms), teacher: !!window.__rooms.himalayan.teacher, x: +window.__state.x.toFixed(1), tex: window.__renderer.info.memory.textures, calls: window.__renderer.info.render.calls, over: [document.documentElement.scrollWidth, innerWidth] }));
  await p.screenshot({ path: `../../renders/m_${name}_room.jpg`, type: 'jpeg', quality: 80 });
  console.log(name, 'walkY', +s0.toFixed(2), JSON.stringify(st), 'light', urls.filter(u => u.includes('/assets/m/')).length, 'heavy', urls.filter(u => /assets\/tex\/|rooms\/[^/]+\/(lm|sky)\.jpg/.test(u)).length, 'errors', errs);
  await b.close();
}
