// Spatial sound engine. Samples are physical-model renders made offline (scripts/render_audio.py).
// Each instrument is a point source with head-related filtering. Each room has a computed impulse response.
import { SCORES } from './score.js';

const A = 'assets/audio/';
export class Engine {
  constructor(mobile = false) { this.mobile = mobile; this.ios = /iPhone|iPad|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1); this.vol = 1; this.ctx = null; this.rooms = {}; this.buf = {}; this.onHit = null; this.muted = false; }
  // Must run inside the tap on Enter: phones only allow sound that a touch has started.
  unlock() {
    // iPhone: ask for media playback, so the silent switch does not mute the session
    try { if (navigator.audioSession) navigator.audioSession.type = 'playback'; } catch { }
    // older iPhones need a real media element playing before Web Audio is heard with the switch on silent
    if (this.ios && !this.keep) { const a = this.keep = new Audio('assets/audio/silent.m4a'); a.loop = true; a.playsInline = true; a.play().catch(() => { }); }
    if (!this.ctx) {
      const AC = window.AudioContext || window.webkitAudioContext, o = { latencyHint: 'playback' };
      if (!this.ios) o.sampleRate = this.mobile ? 32000 : 48000;   // iPhone keeps its own rate: a forced rate can fail there
      this.ctx = new AC(o);
    }
    const c = this.ctx, s = c.createBufferSource(); s.buffer = c.createBuffer(1, 1, c.sampleRate); s.connect(c.destination); s.start();
    c.resume?.();
  }
  // Phones suspend sound after a call, a lock or a tab switch. Any touch brings it back.
  wake() { const c = this.ctx; if (c && c.state !== 'running') { this.keep?.play().catch(() => { }); c.resume?.(); } }
  async start() {
    if (this.master) return;
    this.unlock();
    const c = this.ctx;
    this.master = c.createGain(); this.master.gain.value = 0;
    const lim = c.createDynamicsCompressor(); lim.threshold.value = -6; lim.ratio.value = 6; lim.attack.value = .01; lim.release.value = .4; lim.knee.value = 12;
    if (this.mobile) {
      // phone speakers lose everything below about 300 Hz, so lift the band they can play, where bowls have overtones
      const eq = c.createBiquadFilter(); eq.type = 'peaking'; eq.frequency.value = 900; eq.Q.value = .6; eq.gain.value = 7;
      const boost = c.createGain(); boost.gain.value = 1.6; lim.threshold.value = -12;
      this.master.connect(eq).connect(boost).connect(lim).connect(c.destination);
    } else this.master.connect(lim).connect(c.destination);
    this.master.gain.setValueAtTime(0, c.currentTime); this.master.gain.linearRampToValueAtTime(this.muted ? 0 : 1.7 * this.vol, c.currentTime + 3);
    this.wet = await (await fetch(A + 'rir/rooms.json')).json();
    this.manifest = await (await fetch(A + 'manifest.json')).json();
    await this.loadRoom('shared');
    this.hall = this.makeBus('hall'); this.hall.level.gain.value = 1; this.hall.lp.frequency.value = 20000;
    await this.setRir(this.hall, 'hall');
    this.loopOn(this.hall, 'wind', .04, null); this.loopOn(this.hall, 'cicada', .05, null);
    this.birds();
    this.stepBus = c.createGain(); this.stepBus.gain.value = .22; this.stepBus.connect(this.hall.in);
  }
  // Birds in the trees outdoors, made in the browser: short phrases from random places around the listener
  birds() {
    const c = this.ctx, sing = () => {
      if (this.ctx !== c) return;
      if (this.outdoors !== false) {
        const t0 = c.currentTime + .05, p = c.createStereoPanner(); p.pan.value = Math.random() * 1.8 - .9; const g = c.createGain(); g.gain.value = .012 + Math.random() * .03; p.connect(g).connect(this.hall.in);
        const base = 2200 + Math.random() * 2600, chirp = (t, f0, f1, d, v) => { const o = c.createOscillator(), e = c.createGain(); o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + d); e.gain.setValueAtTime(0, t); e.gain.linearRampToValueAtTime(v, t + d * .2); e.gain.exponentialRampToValueAtTime(.0005, t + d); o.connect(e).connect(p); o.start(t); o.stop(t + d + .02); };
        const n = 3 + Math.floor(Math.random() * 5), k = Math.random();
        for (let i = 0; i < n; i++) k < .5 ? chirp(t0 + i * .16, base * 1.2, base * .8, .12, .6) : chirp(t0 + i * .22, base * (1 + .2 * Math.sin(i)), base * 1.15, .15, .5);
      }
      setTimeout(sing, 2500 + Math.random() * 7000);
    };
    sing();
  }
  makeBus(name) {
    const c = this.ctx, b = { name };
    b.in = c.createGain(); b.lp = c.createBiquadFilter(); b.lp.type = 'lowpass'; b.lp.frequency.value = 500; b.lp.Q.value = .3;
    b.level = c.createGain(); b.level.gain.value = 0;
    b.in.connect(b.lp).connect(b.level).connect(this.master);
    b.conv = c.createConvolver(); b.wetG = c.createGain(); b.wetG.gain.value = this.wet[name]?.wet ?? .3;
    b.in.connect(b.conv); b.conv.connect(b.wetG).connect(b.lp);
    return b;
  }
  async setRir(b, name) {
    const r = await fetch(`${A}rir/${name}.m4a`); b.conv.buffer = await this.ctx.decodeAudioData(await r.arrayBuffer());
  }
  async loadRoom(name) {
    if (this.buf[name]) return;
    this.buf[name] = {};
    const list = this.manifest[name] || [];
    await Promise.all(list.map(async n => {
      const r = await fetch(`${A}${name}/${n}.m4a`); this.buf[name][n] = await this.ctx.decodeAudioData(await r.arrayBuffer());
    }));
  }
  unloadRoom(name) { delete this.buf[name]; }
  panner(pos, ref = 1.6) {
    const c = this.ctx, p = c.createPanner();
    p.panningModel = this.mobile ? 'equalpower' : 'HRTF'; p.distanceModel = 'inverse'; p.refDistance = ref; p.rolloffFactor = .9; p.maxDistance = 60;
    p.positionX.value = pos[0]; p.positionY.value = pos[2]; p.positionZ.value = -pos[1];
    return p;
  }
  loopOn(bus, name, gain, pos, room = 'shared') {
    const c = this.ctx, s = c.createBufferSource(), g = c.createGain();
    s.buffer = this.buf[room]?.[name]; if (!s.buffer) return null;
    s.loop = true; g.gain.setValueAtTime(0, c.currentTime); g.gain.linearRampToValueAtTime(gain, c.currentTime + 3);
    s.connect(g);
    if (pos) g.connect(this.panner(pos, 2.5)).connect(bus.in); else g.connect(bus.in);
    s.start(c.currentTime + Math.random() * .02, Math.random() * 10);
    return { s, g };
  }
  // A room becomes live when the listener nears its door. The session clock runs while it is live.
  async enterRange(meta) {
    const name = meta.name;
    if (this.rooms[name]) return this.rooms[name];
    const R = this.rooms[name] = { meta, score: SCORES[name], t0: 0, timers: [], loops: [], panners: {}, ready: false };
    R.bus = this.makeBus(name);
    await Promise.all([this.loadRoom(name), this.setRir(R.bus, name)]);
    for (const [id, pos] of Object.entries(meta.instruments)) { const p = this.panner(pos); p.connect(R.bus.in); R.panners[id] = p; }
    (R.score.loops || []).forEach(l => { const x = this.loopOn(R.bus, l.name, l.gain, meta.instruments[l.at], l.room ?? name); if (x) R.loops.push(x); });
    const t = this.loopOn(R.bus, 'tone', .02, null); if (t) R.loops.push(t);
    R.ready = true; R.t0 = this.ctx.currentTime;
    R.score.start(R, this);
    return R;
  }
  leaveRange(name) {
    const R = this.rooms[name]; if (!R) return;
    R.stopped = true; R.timers.forEach(clearTimeout);
    const c = this.ctx; R.bus.level.gain.setTargetAtTime(0, c.currentTime, .7);
    setTimeout(() => { R.loops.forEach(l => { try { l.s.stop(); } catch { } }); R.bus.level.disconnect(); if (!this.rooms[name]) this.unloadRoom(name); }, 5000);
    delete this.rooms[name];
  }
  // Called by scores
  after(R, sec, fn) { R.timers.push(setTimeout(() => { if (!R.stopped) fn(); }, sec * 1000)); }
  play(R, id, sample, gain = 1, opts = {}) {
    const b = this.buf[R.meta.name]?.[sample]; if (!b || R.stopped) return;
    // every session ends with one last sound and a silence, whichever way its score is written
    const pos = (this.ctx.currentTime - R.t0) % 960;
    if (!opts.touch && !opts.closing) {
      if (pos > 960 * .93) { if (!R.closed) { R.closed = true; R.score.closing?.(R, this); this.onEnd?.(R); } return; }
      R.closed = false;
    }
    const c = this.ctx, s = c.createBufferSource(), g = c.createGain();
    s.buffer = b; s.detune.value = opts.detune ?? 0; g.gain.value = gain;
    s.connect(g).connect(R.panners[id] ?? R.bus.in);
    const mv = opts.delay === undefined ? R.score.move?.(id, sample) : null;
    const delay = opts.delay ?? (mv ? mv.lead ?? R.score.lead ?? .03 : .03);
    s.start(c.currentTime + delay);
    this.onHit?.(R.meta.name, id, gain, delay, mv, b.duration);
    return s;
  }
  step(surface) {
    const n = `step_${surface}${Math.floor(Math.random() * 3)}`, b = this.buf.shared?.[n]; if (!b) return;
    const c = this.ctx, s = c.createBufferSource(), g = c.createGain(); s.buffer = b; s.detune.value = (Math.random() - .5) * 120; g.gain.value = .5 + Math.random() * .3;
    s.connect(g).connect(this.stepBus); s.start();
  }
  // Called each frame with the head pose and the state of each live room
  listener(pos, fwd, up) {
    const l = this.ctx?.listener; if (!l) return;
    if (l.positionX) {
      const t = this.ctx.currentTime + .03;
      if (this.mobile) { l.positionX.value = pos.x; l.positionY.value = pos.y; l.positionZ.value = pos.z; l.forwardX.value = fwd.x; l.forwardY.value = fwd.y; l.forwardZ.value = fwd.z; l.upX.value = up.x; l.upY.value = up.y; l.upZ.value = up.z; return; }
      l.positionX.linearRampToValueAtTime(pos.x, t); l.positionY.linearRampToValueAtTime(pos.y, t); l.positionZ.linearRampToValueAtTime(pos.z, t);
      l.forwardX.linearRampToValueAtTime(fwd.x, t); l.forwardY.linearRampToValueAtTime(fwd.y, t); l.forwardZ.linearRampToValueAtTime(fwd.z, t);
      l.upX.linearRampToValueAtTime(up.x, t); l.upY.linearRampToValueAtTime(up.y, t); l.upZ.linearRampToValueAtTime(up.z, t);
    } else { l.setPosition(pos.x, pos.y, pos.z); l.setOrientation(fwd.x, fwd.y, fwd.z, up.x, up.y, up.z); }
  }
  roomOpen(name, k) {
    // k=1 inside the room, k=0 far along the gallery behind a thick wall
    const R = this.rooms[name]; if (!R) return; const c = this.ctx, t = c.currentTime;
    R.bus.level.gain.setTargetAtTime(Math.pow(k, 1.2) * (R.score.gain ?? 1), t, .4);
    R.bus.lp.frequency.setTargetAtTime(Math.max(this.mobile ? 1500 : 700, 380 * Math.pow(52, Math.pow(Math.min(1, k), 2))), t, .3);
  }
  setOutdoor(k) { if (this.hall) this.hall.level.gain.setTargetAtTime(k, this.ctx.currentTime, .6); }
  setHallWet(k) { if (this.hall) this.hall.wetG.gain.setTargetAtTime(this.wet.hall.wet * k, this.ctx.currentTime, .3); }
  applyLevel() { if (!this.ctx) return; const g = this.master.gain, t = this.ctx.currentTime; g.cancelScheduledValues(t); g.setTargetAtTime(this.muted ? 0 : 1.7 * this.vol, t, .06); }
  setMuted(m) { this.muted = m; this.applyLevel(); }
  setVolume(v) { this.vol = v; this.applyLevel(); }
  stop() { Object.keys(this.rooms).forEach(n => this.leaveRange(n)); this.keep?.pause(); this.keep = null; this.ctx?.close(); this.ctx = null; this.master = null; this.rooms = {}; this.buf = {}; }
}
