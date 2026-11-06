// The teacher: a skinned person (Microsoft Rocketbox, MIT licence) posed in Blender, seated or standing.
// Each frame the base pose is restored, then breathing, gaze and arm movement go on top with analytic two-bone IK.
// Every sound the teacher makes is scheduled with a lead time, so the hand arrives as the sound starts.
import * as THREE from 'three';

const b2t = (x, y, z) => new THREE.Vector3(x, z, -y);
const ease = t => { t = Math.min(1, Math.max(0, t)); return t * t * (3 - 2 * t); };
const q1 = new THREE.Quaternion(), q2 = new THREE.Quaternion(), q3 = new THREE.Quaternion();
const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), d = new THREE.Vector3();

function worldQ(o) { o.getWorldQuaternion(q2); return q2.clone(); }
function setWorldQ(bone, w) { bone.parent.getWorldQuaternion(q3); bone.quaternion.copy(q3.invert().multiply(w)); bone.updateMatrixWorld(true); }
function aim(bone, child, target) {
  bone.getWorldPosition(a); child.getWorldPosition(b);
  c.copy(b).sub(a).normalize(); d.copy(target).sub(a).normalize();
  q1.setFromUnitVectors(c, d); setWorldQ(bone, worldQ(bone).premultiply(q1));
}
function twoBone(up, lo, end, target, pole) {
  up.getWorldPosition(a); const H = a.clone(); lo.getWorldPosition(b); end.getWorldPosition(c);
  const la = H.distanceTo(b), lb = b.distanceTo(c);
  const D = target.clone().sub(H), dist = Math.min(D.length(), (la + lb) * .995), n = D.clone().normalize();
  const x = (la * la - lb * lb + dist * dist) / (2 * dist), h = Math.sqrt(Math.max(la * la - x * x, 0));
  const P = pole.clone().sub(H), perp = P.sub(n.clone().multiplyScalar(P.dot(n))).normalize();
  aim(up, lo, H.clone().addScaledVector(n, x).addScaledVector(perp, h));
  aim(lo, end, H.clone().addScaledVector(n, dist));
}
function aimHead(bone, target, k, seed) {
  bone.getWorldPosition(a); d.copy(target).sub(a).normalize();
  const q = worldQ(bone);
  if (!bone.userData.fwd) bone.userData.fwd = seed.clone().applyQuaternion(q.clone().invert());   // face direction in bone space
  c.copy(bone.userData.fwd).applyQuaternion(q).normalize();
  q1.setFromUnitVectors(c, d); q1.slerp(q3.identity(), 1 - k); setWorldQ(bone, q.premultiply(q1));
}

// Finger bends in radians for base, middle and end joints, then the thumb.
const GRIP = { rest: [.34, .42, .28, .22], fist: [1.05, 1.35, .95, .75], open: [.12, .16, .1, .1], cup: [.5, .7, .45, .4] };
const basis = (x, y) => { const z = x.clone().cross(y).normalize(); return new THREE.Matrix4().makeBasis(x, y, z); };

export class Teacher {
  constructor(gltf, R, tex, cfg) {
    this.R = R; this.cfg = cfg; this.root = gltf.scene; this.bones = {}; this.t = 0; this.stand = R.meta.teacher.pose === 'stand';
    const m = R.meta.teacher; this.pos = b2t(m.pos[0], m.pos[1], 0); this.root.position.copy(this.pos); this.root.rotation.y = m.yaw;
    this.fwd = new THREE.Vector3(-Math.sin(m.yaw), 0, -Math.cos(m.yaw)); this.right = new THREE.Vector3(Math.cos(m.yaw), 0, -Math.sin(m.yaw));
    this.mixer = new THREE.AnimationMixer(this.root);
    if (gltf.animations[0]) this.mixer.clipAction(gltf.animations[0]).play();
    const wd = b2t(R.meta.windowDir[0], R.meta.windowDir[1], R.meta.windowDir[2]).normalize();
    const key = new THREE.Color(...(R.meta.keyCol ?? [1, .86, .7])).multiplyScalar(R.meta.keyGain ?? .5);
    this.root.traverse(o => {
      if (o.isBone) this.bones[o.name.replace('Bip01_', '').replace('Bip01 ', '').replace(/_/g, ' ')] = o;
      if (!o.isMesh) return;
      o.frustumCulled = false; if (o.morphTargetDictionary) this.morph = o;
      const n = o.material.name, k = /head/.test(n) ? 'head' : /body/.test(n) ? 'body' : 'op';
      const mat = new THREE.MeshStandardMaterial({ envMap: R.env, roughness: 1, metalness: 0 });
      if (k === 'op' && tex.op) { mat.map = tex.op; mat.alphaTest = .45; mat.alphaToCoverage = true; mat.side = THREE.DoubleSide; }
      else if (k !== 'op') { mat.map = tex[k + '_c']; mat.normalMap = tex[k + '_n']; mat.roughnessMap = tex[k + '_r']; mat.normalScale.set(.8, .8); }
      mat.onBeforeCompile = sh => {
        Object.assign(sh.uniforms, { uWD: { value: wd }, uKey: { value: key } });
        sh.fragmentShader = 'uniform vec3 uWD,uKey;\n' + sh.fragmentShader.replace('#include <lights_fragment_maps>', `#include <lights_fragment_maps>
          { vec3 wn_ = inverseTransformDirection(normal, viewMatrix); float w_ = clamp(dot(wn_, uWD) * .6 + .4, 0., 1.); irradiance += uKey * PI * w_ * w_; }`);
      };
      o.material = mat;
    });
    // a wrapped sarong over the legs
    { const pts = this.stand ? [[.17, .94], [.21, .6], [.2, .08]] : [[.17, .5], [.25, .36], [.4, .19], [.46, .05], [.42, .01]];
      const lathe = new THREE.LatheGeometry(pts.map(p => new THREE.Vector2(p[0], p[1])), 28), m = new THREE.MeshStandardMaterial({ map: tex.batik, envMap: R.env, roughness: .85, side: THREE.DoubleSide, color: 0x9a9286 });
      m.onBeforeCompile = sh => { Object.assign(sh.uniforms, { uWD: { value: wd }, uKey: { value: key } }); sh.fragmentShader = 'uniform vec3 uWD,uKey;\n' + sh.fragmentShader.replace('#include <lights_fragment_maps>', `#include <lights_fragment_maps>
        { vec3 wn_ = inverseTransformDirection(normal, viewMatrix); float w_ = clamp(dot(wn_, uWD) * .6 + .4, 0., 1.); irradiance += uKey * PI * w_ * w_; }`); };
      const w = new THREE.Mesh(lathe, m); w.position.copy(this.pos); w.position.y = 0; w.frustumCulled = false; if (!this.stand) { w.position.addScaledVector(this.fwd, .1); w.scale.set(1, 1, .86); w.rotation.y = m.yaw ?? 0; } R.group.add(w); this.cloth = w; }
    R.group.add(this.root); this.root.updateMatrixWorld(true);
    const B = this.bones;
    this.arms = { R: [B['R UpperArm'], B['R Forearm'], B['R Hand']], L: [B['L UpperArm'], B['L Forearm'], B['L Hand']] };
    if (cfg.mallet) {
      this.mallet = new THREE.Group(); const L = cfg.mallet.len, r = cfg.mallet.head;
      const wood = new THREE.MeshStandardMaterial({ color: 0x5a3a22, roughness: .55, envMap: R.env }), suede = new THREE.MeshStandardMaterial({ color: cfg.mallet.col ?? 0x8a6a4a, roughness: .95, envMap: R.env });
      this.mallet.add(new THREE.Mesh(new THREE.CylinderGeometry(.011, .013, L, 10).rotateX(Math.PI / 2).translate(0, 0, L * .42), wood), new THREE.Mesh(new THREE.SphereGeometry(r, 16, 12).translate(0, 0, L * .92), suede));
      R.group.add(this.mallet);
    }
    this.setupHands(); this.idleAt = Math.random() * 40;
    if (cfg.cymbals) {
      const brass = new THREE.MeshStandardMaterial({ color: 0xb98a3e, metalness: 1, roughness: .3, envMap: R.env }), g = new THREE.CylinderGeometry(.034, .037, .007, 24).rotateX(Math.PI / 2);
      this.cym = { R: new THREE.Mesh(g, brass), L: new THREE.Mesh(g, brass) }; this.cym.R.visible = this.cym.L.visible = false; R.group.add(this.cym.R, this.cym.L);
    }
    this.q = { R: [], L: [] }; this.hand = { R: new THREE.Vector3(), L: new THREE.Vector3() };
    this.tip = new THREE.Vector3();
    this.homeGaze = this.stand ? this.pos.clone().addScaledVector(this.fwd, 2).setY(1.2) : this.pos.clone().addScaledVector(this.fwd, 2.4).setY(.45);
    this.gaze = this.homeGaze.clone(); this.gazeT = this.gaze.clone(); this.blink = 2; this.lean = 0; this.leanAmt = 0; this.leanDir = new THREE.Vector3(); this.first = true;
    const off = cfg.rest ?? (this.stand ? [.21, .06, .84] : [.19, .3, .365]);
    this.rest = { R: this.pos.clone().addScaledVector(this.right, off[0]).addScaledVector(this.fwd, off[1]).setY(off[2]), L: this.pos.clone().addScaledVector(this.right, -off[0]).addScaledVector(this.fwd, off[1]).setY(off[2]) };
    this.reach = cfg.mallet ? cfg.mallet.len * .95 : 0;
  }
  // Read the bind pose from the skeleton. Fingers are rebuilt from it every frame, so they curl about the true joint axis.
  setupHands() {
    const sk = this.morph.skeleton, B = this.bones, bind = {}, T = new THREE.Matrix4(), p = new THREE.Vector3(), q = new THREE.Quaternion(), s_ = new THREE.Vector3();
    sk.bones.forEach((b, i) => { T.copy(sk.boneInverses[i]).invert().decompose(p, q, s_); bind[b.uuid] = { p: p.clone(), q: q.clone() }; });
    const P = b => bind[b.uuid].p, Q = b => bind[b.uuid].q, down = new THREE.Vector3(0, -1, 0);
    this.handSet = {}; const yaw = this.root.quaternion.clone();
    for (const s of ['R', 'L']) {
      const H = B[s + ' Hand'], f = i => B[`${s} Finger${i}`], h0 = P(f(2)).clone().sub(P(H)).normalize();
      const n0 = down.clone().sub(h0.clone().multiplyScalar(down.dot(h0))).normalize();
      const l0 = P(f(1)).clone().sub(P(f(4))).normalize(), sigma = Math.sign(h0.clone().cross(n0).dot(l0));
      const chains = [];
      for (let i = 0; i <= 4; i++) {
        const c = [f(i), B[`${s} Finger${i}1`], B[`${s} Finger${i}2`]].filter(Boolean), thumb = i === 0;
        c.forEach((b, j) => {
          const dir = (c[j + 1] ? P(c[j + 1]).clone().sub(P(b)) : P(b).clone().sub(P(c[j - 1]))).normalize();
          const toward = thumb ? n0.clone().addScaledVector(h0, .6).normalize() : n0;
          const ax = dir.clone().cross(toward).normalize().applyQuaternion(Q(b).clone().invert());
          const parent = b.parent; const local = Q(parent).clone().invert().multiply(Q(b));
          chains.push({ b, j, thumb, ax, local, g: i === 4 ? 1.1 : 1 });
        });
      }
      this.handSet[s] = { H, chains, sigma, h0: h0.clone().applyQuaternion(yaw), n0: n0.clone().applyQuaternion(yaw), q0: yaw.clone().multiply(Q(H)), cur: [...GRIP.rest] };
    }
  }
  // Put the hand in a world frame: h is where the fingers point, n is where the palm faces.
  orientHand(s, h, n) {
    const S = this.handSet[s]; n = n.clone().sub(h.clone().multiplyScalar(n.dot(h))).normalize();
    const R = basis(h, n).multiply(basis(S.h0, S.n0).invert());
    setWorldQ(S.H, new THREE.Quaternion().setFromRotationMatrix(R).multiply(S.q0));
  }
  grip(s, g, dt) {
    const S = this.handSet[s], k = Math.min(1, dt * 7); for (let i = 0; i < 4; i++) S.cur[i] += (g[i] - S.cur[i]) * k;
    for (const c of S.chains) { const a = c.thumb ? S.cur[3] * (1 - c.j * .2) : S.cur[c.j] * c.g; c.b.quaternion.copy(c.local).multiply(q1.setFromAxisAngle(c.ax, a)); }
  }
  // When someone walks in, the teacher looks up at them for a moment
  greet() { this.greetT = 5; }
  // mv describes the gesture. when is the audio time of first contact. len is how long the sound is driven.
  act(mv, id, when, now, len) {
    const p = this.R.meta.instruments[id]; if (!p) return;
    const point = b2t(p[0], p[1], p[2]).add(new THREE.Vector3(0, mv.up ?? 0, 0)).addScaledVector(this.fwd, mv.fwd ?? 0);
    const toMe = this.pos.clone().sub(point).setY(0).normalize();
    const rim = point.clone().addScaledVector(toMe, mv.r ?? 0);
    const ev = { ...mv, t0: now, t1: when, t2: when + (mv.hold ?? len ?? 0) + (mv.tail ?? .32), rim, centre: point, toMe };
    if (mv.hand === 'both') { this.q.R.push({ ...ev, side: 1 }); this.q.L.push({ ...ev, side: -1 }); } else this.q[mv.hand ?? 'R'].push(ev);
  }
  target(s, E, now) {
    const u = (now - E.t0) / Math.max(.05, E.t1 - E.t0), tail = (E.t2 - now) / .55;
    const w = ease(u * 1.5) * ease(tail);
    let g = E.rim.clone();
    const after = now - E.t1, off = this.reach * (s === 'R' ? 1 : 0);
    if (E.kind === 'rub' && after > 0) { const a_ = Math.atan2(E.toMe.z, E.toMe.x) + Math.sin(after * 3.3) * 1.15; g = E.centre.clone().add(new THREE.Vector3(Math.cos(a_) * E.r, 0, Math.sin(a_) * E.r)); }   // the mallet travels the near side of the rim
    this.point = g.clone();                                               // where the mallet tip goes
    if (off && !E.fingers) { const to = g.clone().sub(this.shoulder(s)).normalize(); g.addScaledVector(to, -off); }   // the hand stays a mallet length short
    switch (E.kind) {
      case 'hit': g.y += .02 + (now < E.t1 ? Math.sin(ease(u) * Math.PI) * (E.lift ?? .1) : Math.exp(-after * 7) * (E.lift ?? .1) * .8); break;
      case 'rub': g.y += .03; break;
      case 'roll': if (after > 0 && after < E.hold) g.addScaledVector(this.fwd, Math.sin(after * 34) * .022).add(new THREE.Vector3(Math.sin(after * .9) * .05, Math.cos(after * 1.3) * .05, 0)); break;
      case 'both': g = E.centre.clone().addScaledVector(this.right, E.side * (E.gap ?? .03)); if (after > 0) g.y += Math.sin(after * (E.rate ?? 5)) * (E.amp ?? .01); break;
      case 'sweep': { const k = ease(after / E.hold); g = E.centre.clone().addScaledVector(this.fwd, (.1 - k * .32)).addScaledVector(this.right, E.dir ?? 0); g.y += .05; break; }
      case 'pluck': g.y += now < E.t1 ? .03 : .03 + Math.min(.03, after * .4); break;
      case 'shake': if (after > 0) g.add(new THREE.Vector3(Math.sin(after * 11) * .03, 0, Math.cos(after * 7) * .02)); break;
      case 'tube': g = E.centre.clone().addScaledVector(this.right, E.side * .03).add(new THREE.Vector3(0, E.side * .09, 0)); break;
    }
    return { g, w };
  }
  shoulder(s) { this.arms[s][0].getWorldPosition(a); return a.clone(); }
  update(dt, now) {
    if (this.first) { this.mixer.update(0); this.seat = Object.values(this.bones).map(x => [x, x.position.clone(), x.quaternion.clone()]); this.first = false; }
    for (const [x, p, q] of this.seat) { x.position.copy(p); x.quaternion.copy(q); }
    this.root.updateMatrixWorld(true); this.t += dt;
    const B = this.bones, t = this.t;
    for (const s of ['R', 'L']) { const q = this.q[s]; while (q.length && (now > q[0].t2 || (q[1] && now > q[1].t0 && now > q[0].t1 + .12 && !q[0].hold))) q.shift(); }
    const E = this.q.R[0] ?? this.q.L[0];
    if (this.cym) this.cym.R.visible = this.cym.L.visible = false;
    B['Spine2'].scale.setScalar(1 + .004 * Math.sin(t * .85));
    // natural body movement taken from video: it fades while the hands are busy
    const I = this.cfg.idle; let hy = 0, hp = 0, hr = 0;
    if (I) {
      const u = (t + this.idleAt) * I.rate, i = Math.floor(u) % I.lean.length, j = (i + 1) % I.lean.length, f = u - Math.floor(u), val = k => I[k][i] * (1 - f) + I[k][j] * f;
      const busy = 1 - .7 * this.lean, k = (this.stand ? .45 : .8) * busy;
      for (const [ax, a_] of [[this.fwd, -val('roll') * .5 * k + val('lean') * .5 * k], [this.right, val('pitch') * .5 * k], [new THREE.Vector3(0, 1, 0), val('twist') * k]]) { q1.setFromAxisAngle(ax, a_); setWorldQ(B['Spine1'], worldQ(B['Spine1']).premultiply(q1)); }
      hy = val('hyaw') * k; hp = val('hpitch') * k; hr = val('hroll') * k * .35;
    }
    let leanW = 0;
    if (E) { leanW = ease((now - E.t0) / .5) * ease((E.t2 - now) / .5); this.leanDir.copy(E.rim).sub(this.pos).setY(0).normalize(); this.leanAmt = E.lean ?? (this.stand ? .06 : .22); this.gazeT.copy(E.look ? E.centre : E.rim); }
    else this.gazeT.copy(this.homeGaze).addScaledVector(this.right, Math.tan(hy) * 2.2).add(new THREE.Vector3(0, -Math.tan(hp) * 2.2, 0));
    if (this.greetT > 0) { this.greetT -= dt; if (this.viewer) this.gazeT.copy(this.viewer); }
    this.lean += (leanW - this.lean) * Math.min(1, dt * 4);
    if (this.lean > .01) {
      const ax = a.set(0, 1, 0).cross(this.leanDir).normalize().clone();
      for (const [n, g] of [['Spine', .55], ['Spine1', .45]]) { const x = B[n]; q1.setFromAxisAngle(ax, g * this.leanAmt * this.lean); setWorldQ(x, worldQ(x).premultiply(q1)); }
    }
    this.gaze.lerp(this.gazeT, Math.min(1, dt * 2.2));
    aimHead(B['Neck'], this.gaze, .35, this.fwd); aimHead(B['Head'], this.gaze, .6, this.fwd);
    if (hr) { q1.setFromAxisAngle(this.fwd, hr); setWorldQ(B['Head'], worldQ(B['Head']).premultiply(q1)); }
    for (const s of ['R', 'L']) {
      const [u, l, h] = this.arms[s], e = this.q[s][0];
      const tgt = this.hand[s].copy(this.rest[s]);
      if (e) { const { g, w } = this.target(s, e, now); tgt.lerp(g, w); e.w = w; }
      const out = s === 'R' ? this.right : this.right.clone().negate();
      const pole = this.pos.clone().addScaledVector(out, 1.1).addScaledVector(this.fwd, -.5); pole.y = this.stand ? .9 : .35;
      twoBone(u, l, h, tgt.clone(), pole);
      // wrist and fingers
      const fa = h.getWorldPosition(new THREE.Vector3()).sub(l.getWorldPosition(new THREE.Vector3())).normalize(), down = new THREE.Vector3(0, -1, 0), w = e?.w ?? 0;
      const holds = s === 'R' && this.mallet && !(e && (e.kind === 'both' || e.kind === 'tube') && w > .3);
      if (holds) {
        h.getWorldPosition(b); const pos = b.clone();
        this.tip.copy(pos).addScaledVector(this.fwd, .8).setY(this.stand ? pos.y - .9 : .16); if (e && w) this.tip.lerp(this.point ?? e.rim, w);
        const m = this.tip.clone().sub(pos).normalize(), hd = fa.clone().addScaledVector(m, .35).normalize(), mp = m.clone().addScaledVector(hd, -m.dot(hd)).normalize();
        const n = mp.clone().cross(hd).multiplyScalar(this.handSet.R.sigma);
        this.orientHand('R', hd, n);
        const grip = pos.clone().addScaledVector(hd, .08).addScaledVector(n, .03);
        this.mallet.position.copy(grip).addScaledVector(mp, -.05); this.mallet.lookAt(this.tip); this.mallet.visible = true;
        this.grip(s, GRIP.fist, dt);
      } else {
        const inward = this.right.clone().multiplyScalar(s === 'R' ? -1 : 1);
        let hd, n;
        if (e && w > .05 && e.kind === 'tube') { hd = this.fwd.clone().multiplyScalar(-1).addScaledVector(inward, .4).normalize(); n = e.centre.clone().sub(h.getWorldPosition(new THREE.Vector3())).normalize(); this.grip(s, GRIP.fist, dt); }
        else if (e && w > .05 && e.kind === 'both' && e.gap < .1) {
          hd = fa.clone().add(new THREE.Vector3(0, .5, 0)).normalize(); n = inward; this.grip(s, GRIP.cup, dt);
          if (this.cym) { const c = this.cym[s]; c.visible = true; c.position.copy(h.getWorldPosition(new THREE.Vector3())).addScaledVector(hd, .085).addScaledVector(inward, .028); c.lookAt(c.position.clone().add(inward)); }
        }
        else if (e && w > .05 && (e.kind === 'shake')) { hd = fa.clone(); n = fa.clone().cross(this.right).multiplyScalar(-1); this.grip(s, GRIP.cup, dt); }
        else if (e && w > .05) { hd = fa.clone().addScaledVector(down, .55).normalize(); n = down; this.grip(s, GRIP.open, dt); }
        else if (this.stand) { hd = fa.clone(); n = inward.clone().addScaledVector(this.fwd, -.4); this.grip(s, GRIP.rest, dt); }
        else { hd = fa.clone().addScaledVector(down, .6).normalize(); n = down.clone().addScaledVector(inward, .25); this.grip(s, GRIP.rest, dt); }
        this.orientHand(s, hd, n);
        if (s === 'R' && this.mallet) this.mallet.visible = false;
      }
    }
    if (this.morph) {
      this.blink -= dt; const dc = this.morph.morphTargetDictionary, inf = this.morph.morphTargetInfluences;
      const v = this.blink < .14 && this.blink > 0 ? Math.sin(this.blink / .14 * Math.PI) : 0; if (this.blink < 0) this.blink = 2 + Math.random() * 5;
      const soft = E ? .3 : .18;
      ['AK_09_EyeBlinkLeft', 'AK_10_EyeBlinkRight'].forEach(k => { if (dc[k] !== undefined) inf[dc[k]] = Math.max(v, soft); });
    }
  }
}
