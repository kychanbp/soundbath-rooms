// Generative scores. No session repeats. A slow arc rises and falls over about 16 minutes, then a silence, then again.
const rnd = (a, b) => a + Math.random() * (b - a);
const pick = a => a[Math.floor(Math.random() * a.length)];
const ARC = 960;
// 0 at the start, 1 at the top of the arc, 0 near the end
function arc(R, E) { const t = (E.ctx.currentTime - R.t0) % ARC; return Math.sin(Math.PI * Math.min(1, t / (ARC * .93))) ** 1.2; }

// One person plays each room, so a score is one line of actions. step() plays one and returns the seconds until the next.
function line(R, E, wait, step) { const go = () => E.after(R, step(arc(R, E)), go); E.after(R, wait, go); }

function bowls(R, E, ids) {
  let i = Math.floor(ids.length / 2), n = 0;
  line(R, E, 4, a => {
    i = Math.max(0, Math.min(ids.length - 1, i + Math.round(rnd(-2.4, 2.4)))); n++;
    if (n % 41 === 0) { E.play(R, 'tingsha', 'tingsha', .22); return 12; }
    const id = ids[i];
    if (Math.random() < .10 + a * .24) { E.play(R, id, `${id}_r`, .55 + .3 * a); return 27 + rnd(0, 6); }   // the hand stays on the rim
    E.play(R, id, `${id}_s${Math.random() < .25 + .5 * a ? 1 : 0}`, rnd(.5, .85));
    return rnd(7, 15) * (1.5 - .75 * a);
  });
}

const closeWith = (id, sample, gain = .5) => (R, E) => E.play(R, id, sample, gain, { closing: true });
export const SCORES = {
  himalayan: {
    closing: closeWith('tingsha', 'tingsha', .4),
    gain: 1, lead: .85, loops: [{ name: 'wind', room: 'shared', gain: .010, at: 'tingsha' }],
    teacher: { who: 'Female_Adult_09', cymbals: true, mallet: { len: .26, head: .03 } },
    move: (id, s) => id === 'tingsha' ? { kind: 'both', hand: 'both', hold: .5, gap: .085, up: -.14, fwd: .16 }
      : s.endsWith('_r') ? { kind: 'rub', r: .17, drive: .52 } : { kind: 'hit', r: .16 },
    start(R, E) {
      E.after(R, 1.5, () => { E.play(R, 'tingsha', 'tingsha', .4); });
      bowls(R, E, ['b0', 'b1', 'b2', 'b3', 'b4', 'b5', 'b6']);
    },
  },
  crystal: {
    closing: closeWith('c0', 'c0_s', .5),
    gain: .5, lead: .85, teacher: { who: 'Female_Adult_14', mallet: { len: .34, head: .028, col: 0xd9d2c0 } },
    move: (id, s) => id === 'fork' ? { kind: 'shake', hand: 'L', fingers: true, hold: 3, up: -.1, fwd: .1 }
      : s.endsWith('_r') ? { kind: 'rub', r: .18, drive: .58 } : { kind: 'hit', r: .17, lift: .06 },
    start(R, E) {
      const chain = [0, 4, 2, 6, 1, 5, 3]; let k = 0, n = 0;
      line(R, E, 3, a => {
        n++;
        if (n % 17 === 0) { E.play(R, 'fork', 'fork', .18); return 9; }
        if (n % 3 === 0) { const i = Math.floor(Math.random() * 7); E.play(R, `c${i}`, `c${i}_s`, rnd(.35, .6)); return rnd(7, 15); }
        const i = chain[k++ % 7]; E.play(R, `c${i}`, `c${i}_r`, .5 + .25 * a); return 35 + rnd(0, 6);   // bowls still ring when the next starts
      });
    },
  },
  gong: {
    closing: closeWith('g40', 'g40_h0', .4),
    gain: 1.4, lead: .9, teacher: { who: 'Male_Adult_03', mallet: { len: .7, head: .065, col: 0x7a3a2a } },
    move: (id, s) => s.endsWith('_w') ? { kind: 'roll', hold: 22, look: true, r: .05 } : { kind: 'hit', look: true, lift: .14, r: .05 },
    start(R, E) {
      const ids = ['g40', 'g32', 'g24'];
      let n = 0;
      line(R, E, 3, a => {
        const id = pick(ids);
        if (n++ % 3 < 2) { E.play(R, id, `${id}_w`, .45 + .4 * a); return 24 + rnd(1, 5); }
        E.play(R, id, `${id}_h${Math.random() < a * .7 ? 1 : 0}`, rnd(.35, .7)); return rnd(8, 14);
      });
    },
  },
  rain: {
    closing: closeWith('earth', 'ch_earth0', .35),
    gain: 1.8, lead: .6, teacher: { who: 'Male_Adult_11', rest: [.2, .28, .43] },
    move: (id, s) => id === 'ocean' ? { kind: 'both', hand: 'both', hold: 13, gap: .19, rate: 1.2, amp: .03, up: .03, lean: .1 }
      : id === 'stick' ? { kind: 'shake', hand: 'L', fingers: true, hold: 5 }
      : /earth|water/.test(id) ? { kind: 'shake', hand: 'R', fingers: true, hold: 4, lean: .12 }
      : /air|fire/.test(id) ? { kind: 'shake', hand: 'L', fingers: true, hold: 4, lean: .12 } : null,
    loops: [{ name: 'rainloop', gain: .10, at: 'glassE' }, { name: 'rainloop', gain: .08, at: 'glassW' }],
    start(R, E) {
      const S = ['earth', 'water', 'air', 'fire']; let n = 0;
      line(R, E, 4, a => {
        n++;
        if (n % 7 === 0) { E.play(R, 'stick', `stick${Math.floor(Math.random() * 2)}`, rnd(.2, .34)); return 17; }
        if (n % 3 === 0) { E.play(R, 'ocean', `ocean${Math.floor(Math.random() * 3)}`, .25 + .3 * a); return 16 + rnd(1, 5); }
        const c = pick(S); E.play(R, c, `ch_${c}${Math.floor(Math.random() * 3)}`, rnd(.3, .6)); return rnd(6, 13);
      });
    },
  },
  rin: {
    closing: closeWith('r0', 'r0_s0', .5),
    gain: 2.2, lead: .8, teacher: { who: 'Male_Adult_05', mallet: { len: .2, head: .018, col: 0x2a2018 } },
    move: (id, s) => /^r\d/.test(id) ? { kind: 'hit', r: .1, lift: .07 } : null,
    loops: [{ name: 'stream', gain: .018, at: 'jar' }],
    start(R, E) {
      const ids = ['r0', 'r1', 'r2', 'r3', 'r4'];
      const ring = () => { const a = arc(R, E), id = pick(ids); E.play(R, id, `${id}_s${Math.random() < a * .6 ? 1 : 0}`, rnd(.4, .75)); E.after(R, rnd(10, 22) * (1.3 - .5 * a), ring); }; E.after(R, 2, ring);
      const dr = () => { E.play(R, 'jar', `drip${Math.floor(Math.random() * 6)}`, rnd(.12, .3)); E.after(R, rnd(1.6, 6.5), dr); }; E.after(R, 1, dr);
      const kn = () => { E.play(R, 'jar', 'knock', .35); E.after(R, rnd(170, 260), kn); }; E.after(R, 60, kn);
    },
  },
  strings: {
    closing: closeWith('mono', 'mono0', .4),
    gain: .6, lead: .5, teacher: { who: 'Female_Adult_13' },
    move: (id, s) => id === 'mono' ? { kind: 'sweep', fingers: true, hold: 7.5, up: .04, dir: .1, lean: .3 } : id === 'tanpura' ? { kind: 'pluck', hand: 'L', fingers: true, tail: .12, lead: .22 } : null,
    start(R, E) {
      let n = 0;
      const beat = 2.3, pat = [0, 1, 2, 3];
      const tan = () => { const v = pat[n % 4]; E.play(R, 'tanpura', `tan${v}${Math.floor(Math.random() * 2)}`, v === 3 ? .55 : .42, { detune: rnd(-1.5, 1.5) }); n++; E.after(R, beat * rnd(.97, 1.03) * (n % 4 ? 1 : 1.25), tan); }; E.after(R, 1, tan);
      const mono = () => { const a = arc(R, E); E.play(R, 'mono', `mono${Math.floor(Math.random() * 3)}`, .45 + .35 * a); E.after(R, rnd(15, 25), mono); }; E.after(R, 6, mono);
    },
  },
  cave: {
    closing: closeWith('drum', 'd3', .4),
    gain: 1.6, lead: .28, teacher: { who: 'Male_Adult_09', mallet: { len: .3, head: .04, col: 0x3a2a20 } },
    move: (id, s) => id === 'drum' ? { kind: 'hit', r: .01, lift: .05 } : id === 'didge' ? { kind: 'tube', hand: 'both', fingers: true, hold: 24, lean: .26, look: true, lead: 1.1 } : null,
    start(R, E) {
      // one player: drum for a while, then the didgeridoo, then the drum again
      let beats = 0;
      const hit = () => {
        const a = arc(R, E), per = 60 / (52 + 18 * a);
        E.play(R, 'drum', `d${Math.floor(Math.random() * 3) + 3}`, .5 + .3 * a);
        E.after(R, per * .4, () => E.play(R, 'drum', `d${Math.floor(Math.random() * 3)}`, .28 + .2 * a));
        beats++;
        if (beats % 26 === 0) { E.after(R, per * 2 + 2, () => E.play(R, 'didge', `didge${Math.floor(Math.random() * 3)}`, .3 + .2 * a)); E.after(R, per * 2 + 31, hit); } else E.after(R, per * 2, hit);
      };
      E.after(R, 6, hit);
      const dr = () => { const id = pick(['drip1', 'drip2', 'drip3']); E.play(R, id, `drip${Math.floor(Math.random() * 4)}`, rnd(.1, .3)); E.after(R, rnd(3, 11), dr); }; E.after(R, 2, dr);
    },
  },
};
