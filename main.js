import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { VRButton } from 'three/addons/webxr/VRButton.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { Engine } from './audio.js';
import { Teacher } from './teacher.js';
import { SCORES } from './score.js';
import { STR, pickLang } from './i18n.js';

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
THREE.Cache.enabled = true;
// ---- language
let lang = pickLang(params.get('lang')), L10 = STR[lang];
const roomName = n => n ? L10.t[n] ?? n : L10.path;
function applyLang() {
  L10 = STR[lang]; document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en'; document.title = L10.appTitle;
  document.querySelectorAll('[data-t]').forEach(e => { e.textContent = L10[e.dataset.t] ?? ''; });
  $('langHome').textContent = lang === 'zh' ? 'English' : '简体中文';
  $('lEn').classList.toggle('on', lang === 'en'); $('lZh').classList.toggle('on', lang === 'zh');
}
function setLang(l) { lang = l; try { localStorage.setItem('lang', l); } catch { } applyLang(); refreshText?.(); }
let refreshText = null;
// Phones get lighter images, one room at a time, and fewer pixels. Headsets count as full devices.
const MOBILE = (params.get('mobile') ?? '') === '1' || (matchMedia('(pointer:coarse)').matches && Math.min(screen.width, screen.height) < 900 && !/OculusBrowser|Quest|Pico/i.test(navigator.userAgent));
if (MOBILE) THREE.DefaultLoadingManager.setURLModifier(u => u.replace(/^.*\/tex\/([^/]+\.jpg)$/, 'assets/m/tex/$1').replace(/assets\/rooms\/([^/]+)\/(lm|sky)\.jpg/, 'assets/m/rooms/$1/$2.jpg').replace(/assets\/teacher\/([^/]+)\/([^/]+\.jpg)/, 'assets/m/teacher/$1/$2'));
const renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, MOBILE ? 1.5 : 2));
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1;
renderer.xr.enabled = true; renderer.xr.setReferenceSpaceType('local-floor');
renderer.xr.setFoveation?.(.6);
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene(); scene.background = new THREE.Color(0);
const camera = new THREE.PerspectiveCamera(56, innerWidth / innerHeight, .05, 1200);
const rig = new THREE.Group(); rig.add(camera); scene.add(rig);
const audio = new Engine(MOBILE);
// ---- film-style image on desktop: soft bloom, colour grade, vignette and fine grain. Phones and headsets skip it.
let composer = null, gradePass = null;
if (!MOBILE && params.get('fx') !== '0') {
  const rt = new THREE.WebGLRenderTarget(innerWidth, innerHeight, { type: THREE.HalfFloatType, samples: 4 });
  composer = new EffectComposer(renderer, rt); composer.setPixelRatio(Math.min(devicePixelRatio, 2)); composer.setSize(innerWidth, innerHeight);
  composer.addPass(new RenderPass(scene, camera));
  composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), .16, .75, .92));
  composer.addPass(new OutputPass());
  gradePass = new ShaderPass({ uniforms: { tDiffuse: { value: null }, uT: { value: 0 } }, vertexShader: 'varying vec2 vU;void main(){vU=uv;gl_Position=vec4(position.xy,0.,1.);}',
    fragmentShader: `varying vec2 vU;uniform sampler2D tDiffuse;uniform float uT;
      float R(vec2 p){return fract(sin(dot(p,vec2(12.9898,78.233)))*43758.5453);}
      void main(){vec3 c=texture2D(tDiffuse,vU).rgb;float l=dot(c,vec3(.3,.59,.11));
        if (!(l >= 0.)) { c = vec3(0.); l = 0.; }
        c=mix(vec3(l),c,1.26);                                            // a little more colour
        c=mix(c,c*c*(3.-2.*c),.5);                                       // film contrast curve
        c+=(vec3(.018,.02,.012))*(1.-l)*(1.-l);                           // shadows lifted slightly warm-green
        c*=mix(vec3(1.),vec3(1.03,1.,.96),smoothstep(.3,.9,l));           // warm highlights
        vec2 q=vU-.5;c*=1.-.3*smoothstep(.28,.82,length(q*vec2(1.1,.95)));// vignette
        c+=(R(vU*vec2(1920.,1080.)+uT)-.5)*.012;                          // fine grain
        gl_FragColor=vec4(c,1.);}` });
  composer.addPass(gradePass);
}
const loader = new GLTFLoader();
const pmrem = new THREE.PMREMGenerator(renderer);
const clock = new THREE.Clock();
const keys = {}, rooms = {}; let world = null, cur = null, started = false;
const state = { pose: 'lie', poseH: .24, aim: 0, resting: false, x: 0, y: 1.5, yaw: 0, pitch: 0, sit: 0, sitT: 0, target: null, stepD: 0, seat: null };
const FOOTSTEPS = false;   // footstep sounds stay off; set to true to hear them
const standH = 1.62, POSE = { sit: { h: .86, pitch: -.04 }, lie: { h: .24, pitch: 1.15 } };
const shared = { uTime: { value: 0 }, uFlick: { value: 1 } };

const b2t = (p, q = new THREE.Vector3()) => q.set(p[0], p[2], -p[1]);

// ---- baked light shader. Light comes from the lightmap or from vertex colours, reflections from a box-projected probe.
function patch(m, R) {
  const lm = m.aoMap; const useLm = !!lm; const hasVC = m.vertexColors;
  if (R.meta.land && m.name === 'rock') m.color.setRGB(.5, .5, .42);
  if (useLm) { lm.colorSpace = THREE.SRGBColorSpace; lm.needsUpdate = true; m.lightMap = lm; m.lightMap.channel = lm.channel; m.aoMap = null; m.lightMapIntensity = 1; }
  m.envMap = R.env; m.envMapIntensity = /wool|velvet|linen|herring|terry|rug|tatami/.test(m.name) ? .18 : /gong|bronze/.test(m.name) ? 3 : (R.meta.envSpec ?? 1);
  const box = R.meta.box, lo = new THREE.Vector3(box[0], box[2], -box[4]), hi = new THREE.Vector3(box[3], box[5], -box[1]);
  const probe = b2t(R.meta.probe);
  const range = R.meta.lmRange;
  const wd = b2t(R.meta.windowDir).normalize();
  if (/bronze|gong|brass_|^brass|steel/.test(m.name) && !/_0|pot|vase|diya/.test(m.name)) m.metalnessMap = null; else if (m.metalness < .01) m.metalnessMap = null;
  m.defines = { ...(m.defines || {}), BAKED: 1 };
  m.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, { uBoxLo: { value: lo }, uBoxHi: { value: hi }, uProbe: { value: probe }, uRange: { value: range }, uWD: { value: wd }, uFlick: shared.uFlick, uAmb: { value: new THREE.Color(...(R.meta.amb ?? [0, 0, 0])) } });
    sh.vertexShader = 'varying vec3 vWp;\n' + sh.vertexShader.replace('#include <fog_vertex>', '#include <fog_vertex>\n vWp=(modelMatrix*vec4(transformed,1.)).xyz;');
    sh.fragmentShader = 'varying vec3 vWp;uniform vec3 uBoxLo,uBoxHi,uProbe,uWD;uniform float uRange,uFlick;uniform vec3 uAmb;\n' + sh.fragmentShader
      .replace('#include <color_fragment>', '')
      .replace('#include <lights_fragment_maps>', `
        ${useLm ? 'vec3 bakedL = texture2D(lightMap, vLightMapUv).rgb * uRange;' : hasVC ? 'vec3 bakedL = vColor;' : 'vec3 bakedL = vec3(.2);'}
        bakedL *= uFlick;
        float relief = 1.0;
        #ifdef USE_NORMALMAP_TANGENTSPACE
          vec3 wn = inverseTransformDirection(normal, viewMatrix), wg = inverseTransformDirection(nonPerturbedNormal, viewMatrix);
          relief = clamp(1.0 + .5 * (dot(wn, uWD) - dot(wg, uWD)), .6, 1.4);
        #endif
        irradiance += (bakedL + uAmb) * PI * relief;
        float lv = dot(bakedL, vec3(.3, .6, .1));
        float occ = smoothstep(.0, .55, lv) * .9 + .1;
        #if defined(USE_ENVMAP) && defined(RE_IndirectSpecular)
          radiance += getIBLRadiance(geometryViewDir, geometryNormal, material.roughness) * occ;
        #endif
      `);
    sh.fragmentShader = sh.fragmentShader.replace('#include <envmap_physical_pars_fragment>',
      THREE.ShaderChunk.envmap_physical_pars_fragment.replace(
        'reflectVec = inverseTransformDirection( reflectVec, viewMatrix );\n\n\t\t\tvec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );',
        `reflectVec = inverseTransformDirection( reflectVec, viewMatrix );
         { vec3 rmax = (uBoxHi - vWp) / reflectVec, rmin = (uBoxLo - vWp) / reflectVec; vec3 rf = max(rmax, rmin); float d = min(min(rf.x, rf.y), rf.z);
           reflectVec = normalize(vWp + reflectVec * d - uProbe); }
         vec4 envMapColor = textureCubeUV( envMap, envMapRotation * reflectVec, roughness );`));
  };
  m.needsUpdate = true;
}

const skyVS = 'varying vec3 vWp;void main(){vec4 w=modelMatrix*vec4(position,1.);vWp=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}';
const skyFS = `varying vec3 vWp;uniform sampler2D map;uniform float gain;
void main(){vec3 d=normalize(vWp-cameraPosition);vec2 uv=vec2(atan(d.z,d.x)/6.2831853+.5,asin(clamp(d.y,-1.,1.))/3.1415927+.5);
 gl_FragColor=vec4(texture2D(map,uv).rgb*gain,1.);
#include <colorspace_fragment>
}`;

// Rain on glass. Beads sit on the pane and runners slide down it. Each one bends the view behind it.
const rainFS = `varying vec3 vWp;uniform sampler2D map;uniform float gain,uTime;
float H(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float beads(vec2 u,float s){vec2 g=u*s,c=floor(g),f=fract(g)-.5;float r=.14+.24*H(c+3.);vec2 o=(vec2(H(c),H(c+7.))-.5)*.4;
 float on=step(.8,H(c+11.));float q=clamp(1.-dot(f-o,f-o)/(r*r),0.,1.);return on*sqrt(q)*.9;}
float runner(vec2 u,float t){float w=7.;float col=floor(u.x*w),x=fract(u.x*w)-.5;float a=H(vec2(col,1.)),sp=.11+.2*a;
 float y=fract(u.y*.6+t*sp+a*9.);float wob=sin(u.y*17.+a*40.)*.1;
 float head=smoothstep(.3,.08,length(vec2((x-wob)*1.,(y-.1)*5.)));
 float trail=smoothstep(.1,.02,abs(x-wob))*smoothstep(.1,.16,y)*smoothstep(.85,.2,y)*.5;
 return head*step(.35,a)+trail*step(.35,a);}
float h(vec2 u,float t){return max(beads(u,16.)*.8,max(beads(u+3.1,31.)*.5,runner(u,t)));}
vec3 eq(vec3 d){return texture2D(map,vec2(atan(d.z,d.x)/6.2831853+.5,asin(clamp(d.y,-1.,1.))/3.1415927+.5)).rgb;}
void main(){vec2 u=vec2(vWp.x+vWp.z,vWp.y);float t=uTime;
 float e=.012,c=h(u,t);float fd=smoothstep(7.,1.5,length(vWp-cameraPosition));vec2 n=vec2(h(u+vec2(e,0.),t)-c,h(u+vec2(0.,e),t)-c)/e;
 float gl=clamp(length(n)*.012,0.,1.)*fd; gl_FragColor=vec4(mix(vec3(.8,.86,.88),vec3(1.),gl),.035+.14*gl+.02*fd);
#include <colorspace_fragment>
}`;

// ---- the valley: ground paint, sky, trees and plants as crossed cards, rocks
const groundFS = t => t
  .replace('#include <map_fragment>', `
    vec2 wuv = vWp.xz * vec2(1., -1.);
    vec2 suv = (wuv - uB.xy) / uB.zw;
    vec3 sp = texture2D(uSplat, suv).rgb;
    vec2 tc = wuv / 3.2; vec2 tc2 = wuv / 11.;
    vec3 grass = mix(texture2D(uT0, tc).rgb, texture2D(uT0, tc2).rgb, .4), floor_ = mix(texture2D(uT1, tc).rgb, texture2D(uT1, tc2).rgb, .35);
    vec3 trail = texture2D(uT2, wuv / 2.6).rgb, rock = texture2D(uT3, wuv / 7.).rgb;
    vec3 s2 = texture2D(uSplat2, suv).rgb; float rice = s2.r, bund = s2.g;
    float g0 = max(1. - sp.r - sp.g - sp.b, 0.);
    vec3 lawn = grass * vec3(.5, .9, .22) * 1.35;
    float fl = sp.r * .35; g0 += sp.r * .65;
    vec3 c_ = lawn * g0 + floor_ * vec3(.42, .6, .3) * fl + trail * .78 * sp.g + rock * .32 * vec3(.75, .92, .62) * sp.b;
    float dCam = length(vWp - cameraPosition), rowF = smoothstep(46., 12., dCam);
    float stage = s2.b, rows = mix(.5, smoothstep(.15, .85, sin(wuv.x * 11. + wuv.y * 3. + 3. * sin(wuv.y * .4)) * .5 + .5), rowF) * .5 + .5 * texture2D(uT0, wuv / 9.).g;
    vec3 young = vec3(.20, .40, .05), deep = vec3(.09, .24, .04), ripe = vec3(.32, .34, .09), water = vec3(.02, .03, .03);
    vec3 paddy = stage < .9 ? mix(young, deep, stage / .9) : mix(deep, ripe, smoothstep(.9, .97, stage));
    paddy *= .78 + .36 * rows;
    { vec3 fn_ = normalize(cross(dFdx(vWp), dFdy(vWp))); flood = stage < .13 ? rice * (1. - smoothstep(.15, .7, s2.g)) * smoothstep(.992, .9995, abs(fn_.y)) : 0.; }
    if (stage < .13) paddy = mix(young, mix(water, young * .9, rows * .12), flood);                  // a freshly flooded paddy
    vec3 ridge = mix(vec3(.30, .23, .15), vec3(.27, .42, .13), texture2D(uT0, wuv / 1.6).g * 1.4) * (.8 + .4 * texture2D(uT1, wuv / 2.).g);
    diffuseColor.rgb = mix(c_, mix(paddy, ridge, smoothstep(.15, .7, s2.g)), rice);
  `)
  .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\n    roughnessFactor = mix(roughnessFactor, .07, flood);')
  .replace('bakedL *= uFlick;', `bakedL *= uFlick;
    { vec2 cw = vWp.xz * .006 + vec2(uTime2 * .006, uTime2 * .0024); float cl = sin(cw.x * 3.1 + sin(cw.y * 2.3)) * sin(cw.y * 2.7 + 1.3 * sin(cw.x * 1.7)); bakedL *= .9 + .13 * smoothstep(-.5, .6, cl); }`)
  .replace('#include <opaque_fragment>', `
    if (flood > .01) { vec3 vd = normalize(vWp - cameraPosition); vec2 w3 = vWp.xz * 2.4 + uTime2 * .25; vec3 nw = normalize(vec3(sin(w3.x + sin(w3.y * 1.3)) * .012, 1., cos(w3.y * .9 + sin(w3.x)) * .012));
      vec3 rf = reflect(vd, nw); vec3 sky = texture2D(uSkyT, vec2(atan(rf.z, rf.x) / 6.2831853 + .5, asin(clamp(rf.y, -1., 1.)) / 3.1415927 + .5)).rgb; float fr = .06 + .94 * pow(1. - max(dot(-vd, nw), 0.), 4.);
      outgoingLight = mix(outgoingLight, sky * 1.1, flood * clamp(fr + .22, 0., 1.)); }
    #include <opaque_fragment>`)
  .replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
    { vec2 w2 = vWp.xz * vec2(1., -1.); vec3 n1 = texture2D(uN0, w2 / 3.2).xyz * 2. - 1., n2 = texture2D(uN1, w2 / 2.6).xyz * 2. - 1.;
      vec3 sp2 = texture2D(uSplat, (w2 - uB.xy) / uB.zw).rgb; vec3 dn = mix(n1, n2, sp2.g) * vec3(.85, .85, 1.);
      normal = normalize(normal + (viewMatrix * vec4(dn.x, 0., -dn.y, 0.)).xyz); }`)
  .replace('void main() {', 'uniform sampler2D uSplat,uSplat2,uT0,uT1,uT2,uT3,uN0,uN1,uSkyT;uniform float uTime2;uniform vec4 uB;float flood;\nvoid main() {');
// ---- real blades near you: rice in the paddies and grass on the banks are drawn as 3D blades, and follow you as you walk.
function bladeClump(n, H, w, bend) {
  const pos = [], col = [], idx = []; let v = 0, r = new THREE.Vector3();
  for (let b = 0; b < n; b++) {
    const a = b * 2.4 + Math.sin(b * 7.1), o = .018 + .05 * Math.abs(Math.sin(b * 3.7)), h = H * (.72 + .28 * Math.abs(Math.sin(b * 5.3))), lean = bend * (.5 + .5 * Math.abs(Math.cos(b * 2.1))), dx = Math.cos(a), dz = Math.sin(a), sx = -dz * w, sz = dx * w, tone = .78 + .3 * Math.abs(Math.sin(b * 9.7));
    const seg = 3;
    for (let k = 0; k <= seg; k++) { const t = k / seg, x = dx * (o + lean * t * t), z = dz * (o + lean * t * t), y = h * t * (1 - .14 * t), wd = 1 - t * t; const sh = (.26 + .74 * t * t ** .3) * tone; pos.push(x - sx * wd, y, z - sz * wd, x + sx * wd, y, z + sz * wd); col.push(sh, sh, sh, sh, sh, sh); }
    for (let k = 0; k < seg; k++) { const p = v + k * 2; idx.push(p, p + 1, p + 2, p + 1, p + 3, p + 2); } v += (seg + 1) * 2;
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx); return g;
}
async function addNearField(R, L, base) {
  const img = await L.loadAsync(base + 'splat2.webp'), sp1 = await L.loadAsync(base + 'splat.png'), cv = document.createElement('canvas'); cv.width = cv.height = 1024; const cx = cv.getContext('2d', { willReadFrequently: true });
  cx.drawImage(img.image, 0, 0, 1024, 1024); const s2 = cx.getImageData(0, 0, 1024, 1024).data; cx.clearRect(0, 0, 1024, 1024); cx.drawImage(sp1.image, 0, 0, 1024, 1024); const s1 = cx.getImageData(0, 0, 1024, 1024).data;
  const B = R.meta.bounds, sample = (d, x, y, c) => { const i = Math.min(1023, Math.max(0, Math.round((x - B[0]) / (B[2] - B[0]) * 1023))), j = Math.min(1023, Math.max(0, Math.round((B[3] - y) / (B[3] - B[1]) * 1023))); return d[(j * 1024 + i) * 4 + c] / 255; };
  // All blades are built once here, in map chunks. Walking only switches chunks on and off, and the shader
  // grows and shrinks each blade with distance, so nothing appears suddenly and nothing is rebuilt.
  const blades = (amp, Rout, fadeOut, Rin = 0, fadeIn = 1) => { const m = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide, toneMapped: false }); m.onBeforeCompile = sh => { sh.uniforms.uTime = shared.uTime; sh.vertexShader = 'uniform float uTime;\n' + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
      { vec4 ip = instanceMatrix[3]; float ph = ip.x * .7 + ip.z * .9, k = position.y * position.y; float g = sin(uTime * .8 + ip.x * .12 + ip.z * .09); transformed.x += (sin(uTime * 1.7 + ph) * .3 + g) * k * ${amp}; transformed.z += cos(uTime * 1.3 + ph) * k * ${amp} * .6;
        float dc = distance(ip.xz, cameraPosition.xz); float fd = (1. - smoothstep(${(Rout - fadeOut).toFixed(1)}, ${Rout.toFixed(1)}, dc))${Rin ? ` * smoothstep(${Rin.toFixed(1)}, ${(Rin + fadeIn).toFixed(1)}, dc)` : ''}; transformed *= fd; }`); }; return m; };
  const Rn = MOBILE ? 10 : 17, Rf = MOBILE ? 24 : 46, Rg = MOBILE ? 7 : 15;
  const layers = [
    { geo: bladeClump(13, .8, .012, .28), mat: blades('.16', Rn, 5), R: Rn },
    { geo: bladeClump(6, .84, .028, .32), mat: blades('.16', Rf, 12, Rn - 6, 4), R: Rf },
    { geo: bladeClump(9, .2, .012, .12), mat: blades('.5', Rg, 4), R: Rg },
  ];
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), Y = new THREE.Vector3(0, 1, 0), P = new THREE.Vector3(), S = new THREE.Vector3(), C = new THREE.Color();
  const stageCol0 = st => st < .9 ? C.setRGB(.22 - st * .14, .50 - st * .2, .08) : C.setRGB(.34, .40, .08);
  const J = new THREE.Color(); const stageCol = (st, x = 0, y = 0) => { const c = stageCol0(st); c.multiplyScalar(composer ? 1.08 : 1); const lf = .9 + .16 * Math.sin(x * .19 + 1.7 * Math.sin(y * .13)), q = lf * (.88 + .2 * Math.abs(Math.sin(x * 3.7 + y * 5.3))), w = (.95 + .1 * Math.sin(y * .23 - x * .11)) * (.92 + .16 * Math.abs(Math.cos(x * 2.1 - y * 4.7))); return c.setRGB(c.r * q, c.g * w, c.b * .8); };
  const CH = 28, key = (x, y) => Math.floor(x / CH) + ',' + Math.floor(y / CH), pd_ = R.meta.pond, wet = (x, y) => Math.hypot(x - pd_.x, (y - pd_.y) * 1.25) < pd_.r + 2.6;
  // only ground within reach of the walkable area needs blades
  const near = new Set(), reach = Rf + 4;
  for (let x = B[0]; x <= B[2]; x += 6) for (let y = B[1]; y <= B[3]; y += 6) if (outdoorOk(x, y)) for (let i = -Math.ceil(reach / CH); i <= Math.ceil(reach / CH); i++) for (let j = -Math.ceil(reach / CH); j <= Math.ceil(reach / CH); j++) near.add(key(x + i * CH, y + j * CH));
  const sets = layers.map(() => new Map());
  const add = (li, x, y, z, s, c) => { const k = key(x, y); let a = sets[li].get(k); if (!a) sets[li].set(k, a = []); a.push(x, z, -y, s, (x * 13.1 + y * 7.7) % 6.28, c.r, c.g, c.b); };
  const scan = (step, fn) => { for (let x = B[0] + 2; x < B[2] - 2; x += step) for (let y = B[1] + 2; y < B[3] - 2; y += step) if (near.has(key(x, y)) && !inHut(x, y) && !wet(x, y)) fn(x, y); };
  const rice = (x, y) => sample(s2, x, y, 0) >= .5 && sample(s2, x, y, 1) <= .45 && sample(s1, x, y, 1) <= .2;
  const nearStep = MOBILE ? .34 : .22, farStep = MOBILE ? .62 : .44, grassStep = MOBILE ? .4 : .26;
  scan(nearStep, (x, y) => { const xx = x + Math.sin(x * 9.1) * .07, yy = y + Math.cos(y * 8.3) * .07; if (!rice(xx, yy)) return; const st = sample(s2, xx, yy, 2); if (st < .13) return; add(0, xx, yy, heightAt(xx, yy) - .03, .8 + .4 * Math.abs(Math.sin(x * 2.2 + y * 3.1)), stageCol(st, x, y)); });
  scan(farStep, (x, y) => { if (!rice(x, y)) return; const st = sample(s2, x, y, 2); if (st < .13) return; add(1, x, y, heightAt(x, y) - .04, 1.15 + .15 * Math.sin(x * 3.3 + y), stageCol(st, x, y)); });
  scan(grassStep, (x, y) => { if (sample(s2, x, y, 0) > .35 || sample(s1, x, y, 1) > .35 || sample(s1, x, y, 2) > .35 || !outdoorOk(x, y)) return; add(2, x + Math.sin(y * 7.3) * .1, y + Math.cos(x * 6.7) * .1, heightAt(x, y) - .02, 1 + .7 * Math.abs(Math.sin(x * 4.1 + y * 2.7)), C.setRGB(.17 + .05 * Math.sin(x * .9), .3 + .05 * Math.cos(y * 1.1), .06)); });
  const group = new THREE.Group(); R.group.add(group); world.fieldGroup = [group]; const chunks = []; let total = 0;
  sets.forEach((map, li) => { const L_ = layers[li]; for (const [k, a] of map) {
    const n = a.length / 8, im = new THREE.InstancedMesh(L_.geo, L_.mat, n); total += n;
    im.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 3);
    for (let i = 0; i < n; i++) { const o = i * 8; P.set(a[o], a[o + 1], a[o + 2]); Q.setFromAxisAngle(Y, a[o + 4]); S.setScalar(a[o + 3]); M.compose(P, Q, S); im.setMatrixAt(i, M); im.instanceColor.setXYZ(i, a[o + 5], a[o + 6], a[o + 7]); }
    const [ci, cj] = k.split(',').map(Number), cx_ = (ci + .5) * CH, cy_ = (cj + .5) * CH, cz = heightAt(cx_, cy_);
    im.boundingSphere = new THREE.Sphere(new THREE.Vector3(cx_, cz, -cy_), CH * .8 + 14); im.visible = false; group.add(im); chunks.push({ im, x: cx_, y: cy_, r: L_.R + CH * .75 });
  } map.clear(); });
  world.fieldStats = { chunks: chunks.length, blades: total };
  world.field = (x0, y0) => { for (const c of chunks) c.im.visible = Math.hypot(c.x - x0, c.y - y0) < c.r; };
  // send every chunk to the graphics card once while the page loads, so walking never waits for an upload
  world.fieldWarm = () => { for (const c of chunks) { c.im.visible = true; c.im.frustumCulled = false; } renderer.compile(scene, camera); renderer.render(scene, camera); for (const c of chunks) { c.im.frustumCulled = true; c.im.visible = false; } world.fx = world.fy = undefined; };
}

// ---- living things: butterflies near you, egrets over the terraces
function addLife(R) {
  const wing = new THREE.BufferGeometry(); wing.setAttribute('position', new THREE.Float32BufferAttribute([0, 0, -.5, 0, 0, .5, -1, 0, .3, 0, 0, -.5, 0, 0, .5, 1, 0, .3], 3)); wing.setAttribute('side_', new THREE.Float32BufferAttribute([0, 0, 1, 0, 0, -1], 1)); wing.computeVertexNormals();
  const mk = (n, col, flap, s) => { const m = new THREE.MeshBasicMaterial({ color: col, side: THREE.DoubleSide }); m.onBeforeCompile = sh => { sh.uniforms.uTime = shared.uTime; sh.vertexShader = 'uniform float uTime;attribute float side_;\n' + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>\n float ph = instanceMatrix[3][0] * 3.1; transformed.y += abs(side_) * sin(uTime * ${flap} + ph) * .75;`); }; const im = new THREE.InstancedMesh(wing, m, n); im.frustumCulled = false; for (let i = 0; i < n; i++) { const k = .75 + .4 * ((i * 53 % 97) / 97); im.setColorAt(i, new THREE.Color(k, k, k)); } R.group.add(im); return im; };
  const fly = mk(MOBILE ? 18 : 42, 0xf2a93b, '16.', .05), egret = mk(9, 0xf3f1ea, '5.2', .5);
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), E = new THREE.Euler(), P = new THREE.Vector3(), S = new THREE.Vector3(), base = Array.from({ length: fly.count }, (_, i) => [Math.sin(i * 12.9) * 34, Math.cos(i * 7.3) * 34, i * 1.7]);
  let t = 0;
  world.life = dt => {
    t += dt;
    base.forEach((b, i) => { const x = state.x + b[0] + Math.sin(t * .7 + b[2]) * 2.4, y = state.y + b[1] + Math.cos(t * .5 + b[2] * 1.3) * 2.4, z = heightAt(x, y) + .7 + .4 * Math.sin(t * 1.1 + b[2]); P.set(x, z, -y); E.set(0, t * .4 + b[2], 0); Q.setFromEuler(E); S.setScalar(.055); M.compose(P, Q, S); fly.setMatrixAt(i, M); }); fly.instanceMatrix.needsUpdate = true;
    for (let i = 0; i < egret.count; i++) { const a = t * .045 + i * .09, r = 96 + 8 * Math.sin(i * 2.1), x = Math.cos(a) * r * 1.2 + Math.sin(i * 3.) * 6, y = 20 + Math.sin(a) * r + Math.cos(i * 2.) * 7; P.set(x, 26 + 3 * Math.sin(t * .2 + i), -y); E.set(0, -a - Math.PI / 2 + Math.PI / 2, 0); Q.setFromEuler(E); S.setScalar(.62); M.compose(P, Q, S); egret.setMatrixAt(i, M); } egret.instanceMatrix.needsUpdate = true;
  };
}

async function addLand(R, sceneGl) {
  const base = 'assets/rooms/hall/', L = new THREE.TextureLoader(), T = 'assets/tex/';
  const [hb, st] = await Promise.all([fetch(base + 'height.f32').then(r => r.arrayBuffer()), fetch(base + 'steep.u8').then(r => r.arrayBuffer())]);
  const B = R.meta.bounds, nx = B[2] - B[0] + 1, ny = B[3] - B[1] + 1;
  world.land = { h: new Float32Array(hb), steep: new Uint8Array(st), x0: B[0], y0: B[1], nx, ny };
  const skyEarly = await L.loadAsync(base + 'sky.jpg'); skyEarly.colorSpace = THREE.SRGBColorSpace; skyEarly.generateMipmaps = false; skyEarly.minFilter = THREE.LinearFilter; skyEarly.wrapS = THREE.RepeatWrapping;
  const g0 = await loader.loadAsync(base + 'ground.gltf');
  const tex = async (f, c) => { const t = await L.loadAsync(T + f); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = c; t.anisotropy = MOBILE ? 4 : 8; return t; };
  const [t0, t1, t2, t3, sp] = await Promise.all([tex('sparse_grass_c.jpg', THREE.SRGBColorSpace), tex('forest_leaves_02_c.jpg', THREE.SRGBColorSpace), tex('mossy_cobblestone_c.jpg', THREE.SRGBColorSpace), tex('rock_face_03_c.jpg', THREE.SRGBColorSpace), L.loadAsync(base + 'splat.png')]);
  const nrm = async f => { const t = await L.loadAsync(T + f); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.colorSpace = THREE.NoColorSpace; t.anisotropy = MOBILE ? 2 : 4; return t; }; const [n0, n1] = await Promise.all([nrm('sparse_grass_n.jpg'), nrm('mossy_cobblestone_n.jpg')]);
  const sp2 = await L.loadAsync(base + 'splat2.webp'); sp.colorSpace = sp2.colorSpace = THREE.NoColorSpace; sp.flipY = sp2.flipY = false; sp2.anisotropy = 8;
  g0.scene.traverse(o => {
    if (!o.isMesh) return; o.frustumCulled = false; const m = o.material; m.side = THREE.FrontSide;
    R.meta.lmRange = R.meta.gmax; patch(m, R); R.meta.lmRange = R.meta.lmRangeShell ?? R.meta.lmRange;
    const old = m.onBeforeCompile;
    m.onBeforeCompile = sh => { old(sh); Object.assign(sh.uniforms, { uSplat: { value: sp }, uTime2: shared.uTime, uSkyT: { value: skyEarly }, uSplat2: { value: sp2 }, uN0: { value: n0 }, uN1: { value: n1 }, uT0: { value: t0 }, uT1: { value: t1 }, uT2: { value: t2 }, uT3: { value: t3 }, uB: { value: new THREE.Vector4(B[0], B[1], B[2] - B[0], B[3] - B[1]) } }); sh.fragmentShader = groundFS(sh.fragmentShader);
      // the ground sinks under each hut, so that it never shows through a room floor
      const huts = world.rooms.map(n => { const m = rooms[n].meta, b = m.box; return new THREE.Vector4(Math.min(b[0], m.door[0]) - .3, Math.min(b[1], m.door[1]) - .3, Math.max(b[3], m.door[0]) + .3, Math.max(b[4], m.door[1]) + .3); });
      sh.uniforms.uHuts = { value: huts };
      sh.vertexShader = `uniform vec4 uHuts[${huts.length}];\n` + sh.vertexShader.replace('#include <begin_vertex>', `#include <begin_vertex>
        for (int i = 0; i < ${huts.length}; i++) { vec4 b = uHuts[i]; if (position.x > b.x && position.x < b.z && -position.z > b.y && -position.z < b.w) transformed.y -= .35; }`); };
    m.needsUpdate = true;
  });
  R.group.add(g0.scene);
  // sky at infinity
  const skyT = await L.loadAsync(base + 'sky.jpg'); skyT.colorSpace = THREE.SRGBColorSpace; skyT.generateMipmaps = false; skyT.minFilter = THREE.LinearFilter; skyT.wrapS = THREE.RepeatWrapping;
  const sky = new THREE.Mesh(new THREE.SphereGeometry(600, 24, 16), new THREE.ShaderMaterial({ vertexShader: skyVS, fragmentShader: skyFS, uniforms: { map: { value: skyT }, gain: { value: 1.25 } }, side: THREE.BackSide, depthWrite: false, toneMapped: false }));
  sky.renderOrder = -20; sky.frustumCulled = false; R.group.add(sky); R.landSky = sky;
  // plants
  const cards = await fetch('assets/land/cards.json').then(r => r.json()), place = await fetch(base + 'plants.json').then(r => r.json());
  const M = new THREE.Matrix4(), Q = new THREE.Quaternion(), P = new THREE.Vector3(), S = new THREE.Vector3(), Y = new THREE.Vector3(0, 1, 0), C = new THREE.Color();
  const sunV = b2t(R.meta.windowDir).normalize();
  const wind = (mat, amp, lit) => { mat.onBeforeCompile = sh => { sh.uniforms.uTime = shared.uTime; sh.uniforms.uSunV = { value: sunV };
    sh.vertexShader = 'uniform float uTime;uniform vec3 uSunV;varying float vSh;varying float vCamD;\n' + (lit ? 'attribute vec3 normal2;\n' : '') + sh.vertexShader.replace('#include <project_vertex>', '#include <project_vertex>\n vCamD = -mvPosition.z;').replace('#include <begin_vertex>', `#include <begin_vertex>
      { float ph = instanceMatrix[3][0] * .13 + instanceMatrix[3][2] * .17; float k = position.y * ${amp}; k *= k; transformed.x += sin(uTime * .9 + ph + position.x * .4) * k; transformed.z += cos(uTime * .7 + ph + position.z * .4) * k * .7;
        vSh = ${lit ? '.5 + .62 * abs(dot(normalize(mat3(instanceMatrix) * normal2), uSunV))' : '1.'}; }`);
    sh.fragmentShader = 'varying float vSh;varying float vCamD;\n' + sh.fragmentShader.replace('#include <map_fragment>', 'if (vCamD < 1.7) discard;\n#include <map_fragment>').replace('#include <opaque_fragment>', 'outgoingLight *= vSh;\n#include <opaque_fragment>'); }; };
  const E_ = new THREE.Euler(), Q2 = new THREE.Quaternion(); const inst = (geo, mat, list, tint = true, sink = 0, tilt = 0) => {
    const im = new THREE.InstancedMesh(geo, mat, list.length); im.frustumCulled = false;
    list.forEach((p, i) => { P.set(p[0], p[2] - .06 - (sink * p[3]), -p[1]); Q.setFromAxisAngle(Y, p[4]); if (tilt) { E_.set(Math.sin(i * 1.7) * tilt, 0, Math.cos(i * 2.3) * tilt); Q.premultiply(Q2.setFromEuler(E_)); } S.setScalar(p[3]); M.compose(P, Q, S); im.setMatrixAt(i, M); if (tint) { const k = .8 + .34 * ((i * 37 % 97) / 97); im.setColorAt(i, C.setRGB(k, k, k * .95)); } });
    (world.plants ?? R.group).add(im); return im;
  };
  const crossed = c => { const a = new THREE.PlaneGeometry(c.w, c.h).translate(0, c.h / 2, 0), b = a.clone().rotateY(Math.PI / 2), g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute([...a.attributes.position.array, ...b.attributes.position.array], 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute([...a.attributes.uv.array, ...b.attributes.uv.array], 2)); g.setIndex([0, 2, 1, 2, 3, 1, 4, 6, 5, 6, 7, 5]); return g; };
  const plantGroup = world.plants = new THREE.Group(); R.group.add(plantGroup);
  for (const [fn, list0] of Object.entries(place.cards)) {
    if (!cards[fn] || /^grass/.test(fn)) continue;
    const big = /^[jip]/.test(fn), list = MOBILE && !big ? list0.filter((_, i) => i % 2 === 0) : list0; if (!list.length) continue;
    const t = await L.loadAsync(`assets/land/${fn}.webp`); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4;
    const mat = new THREE.MeshBasicMaterial({ map: t, side: THREE.DoubleSide, alphaTest: .42, alphaToCoverage: true, color: new THREE.Color(.7, .84, .62) });
    wind(mat, big ? '.05' : '.2'); inst(crossed(cards[fn]), mat, list, true, /jtree|jsmall/.test(fn) ? cards[fn].h * .07 : 0);
  }
  // palms and bananas are real meshes
  const geo = await fetch('assets/land/palms.json').then(r => r.json());
  const [frond, leaf, barkT] = await Promise.all(['frond', 'bananaleaf', 'palmbark'].map(async n => { const t = await L.loadAsync(`assets/land/${n}.webp`); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t; }));
  const buf = g => { const b = new THREE.BufferGeometry(); b.setAttribute('position', new THREE.Float32BufferAttribute(g.pos, 3)); b.setAttribute('uv', new THREE.Float32BufferAttribute(g.uv, 2)); b.setIndex(g.idx); b.computeVertexNormals(); b.setAttribute('normal2', b.attributes.normal); return b; };
  for (const [n, list0] of Object.entries(place.meshes)) {
    const isP = n.startsWith('palm'), g = geo[n], list = MOBILE ? list0.filter((_, i) => i % 2 === 0) : list0;
    inst(buf(g.t), new THREE.MeshBasicMaterial({ map: barkT, color: isP ? 0x8f826c : 0x6f8a4c }), list, false, 0, isP ? .1 : 0);
    const fm = new THREE.MeshBasicMaterial({ map: isP ? frond : leaf, side: THREE.DoubleSide, alphaTest: .45, alphaToCoverage: true, color: new THREE.Color(isP ? .56 : .6, isP ? .66 : .72, isP ? .42 : .46) });
    wind(fm, isP ? '.045' : '.14', true); inst(buf(g.f), fm, list, true, 0, isP ? .1 : 0);
  }
  await addNearField(R, L, base);
  // lotus pond
  { const p = R.meta.pond, w = new THREE.Mesh(new THREE.CircleGeometry(p.r + 1.1, 48).rotateX(-Math.PI / 2), new THREE.ShaderMaterial({ transparent: false, uniforms: { map: { value: skyEarly }, uTime: shared.uTime }, vertexShader: 'varying vec3 vWp;void main(){vec4 w=modelMatrix*vec4(position,1.);vWp=w.xyz;gl_Position=projectionMatrix*viewMatrix*w;}',
      fragmentShader: `varying vec3 vWp;uniform sampler2D map;uniform float uTime;void main(){vec3 vd=normalize(vWp-cameraPosition);vec2 w=vWp.xz*1.8+uTime*.2;vec3 n=normalize(vec3(sin(w.x+sin(w.y*1.3))*.016,1.,cos(w.y*.9+sin(w.x))*.016));vec3 r=reflect(vd,n);vec3 sk=texture2D(map,vec2(atan(r.z,r.x)/6.2831853+.5,asin(clamp(r.y,-1.,1.))/3.1415927+.5)).rgb;float f=.1+.9*pow(1.-max(dot(-vd,n),0.),4.);gl_FragColor=vec4(mix(vec3(.018,.035,.03),sk,f),1.);\n#include <colorspace_fragment>\n}` }));
    w.position.set(p.x, -.2, -p.y); w.scale.z = .8; R.group.add(w);
    const pad = new THREE.CircleGeometry(.48, 16, .3, 5.9).rotateX(-Math.PI / 2), pm = new THREE.MeshBasicMaterial({ color: 0x5a9a44, side: THREE.DoubleSide }), fl = new THREE.ConeGeometry(.09, .16, 8), fm = new THREE.MeshBasicMaterial({ color: 0xf0a6bd }), L_ = [], F_ = [];
    for (let i = 0; i < 46; i++) { const a = i * 2.4, r = Math.sqrt((i + .5) / 46) * p.r * .8, q = [p.x + Math.cos(a) * r, p.y + Math.sin(a) * r * .8, -.12, .8 + (i % 5) * .15, i]; L_.push(q); if (i % 5 === 0) F_.push([q[0], q[1], -.04, 1, i]); }
    inst(pad, pm, L_, false); inst(fl, fm, F_, false); }
  addLife(R);
  // rocks: one rough shape, many sizes
  const rg = new THREE.IcosahedronGeometry(1, 2); { const p = rg.attributes.position, v = new THREE.Vector3(); for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i); const n = 1 + .22 * Math.sin(v.x * 3.1 + v.y * 2.3) * Math.cos(v.z * 2.9) + .1 * Math.sin(v.x * 7 + v.z * 5); p.setXYZ(i, v.x * n, v.y * n * .7, v.z * n); } rg.computeVertexNormals(); }
  const rt = await tex('rock_face_03_c.jpg', THREE.SRGBColorSpace);
  rt.repeat.set(1, 1);
  const rm = new THREE.MeshStandardMaterial({ map: rt, roughness: .95, envMap: R.env, envMapIntensity: 1.1, color: 0x6e7a62 });
  const ri = new THREE.InstancedMesh(rg, rm, world.rocks.length); ri.frustumCulled = false;
  world.rocks.forEach((p, i) => { P.set(p[0], p[2] + .05, -p[1]); Q.setFromAxisAngle(Y, p[4]); S.setScalar(p[3] * .55); M.compose(P, Q, S); ri.setMatrixAt(i, M); }); R.group.add(ri);
  { const c = document.createElement('canvas'); c.width = c.height = 64; const x = c.getContext('2d'), g = x.createRadialGradient(32, 32, 2, 32, 32, 31); g.addColorStop(0, '#000000b0'); g.addColorStop(.5, '#00000050'); g.addColorStop(1, '#00000000'); x.fillStyle = g; x.fillRect(0, 0, 64, 64);
    const mt = new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, toneMapped: false, polygonOffset: true, polygonOffsetFactor: -2 });
    const all = [...Object.values(place.meshes).flat().map(p => [p[0], p[1], p[2], 1.6]), ...Object.entries(place.cards).filter(([k]) => /^[jip]/.test(k)).flatMap(([, v]) => v.map(p => [p[0], p[1], p[2], 3.2])), ...world.rocks.map(p => [p[0], p[1], p[2], p[3] * 1.3])];
    const sm = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), mt, all.length); sm.frustumCulled = false;
    all.forEach((p, i) => { P.set(p[0], p[2] + .05, -p[1]); S.set(p[3] * 2, 1, p[3] * 2); M.compose(P, Q.identity(), S); sm.setMatrixAt(i, M); }); plantGroup.add(sm); }
  scene.fog = new THREE.FogExp2(0xd6dcd8, .0028);
}

async function loadRoomGeometry(name) {
  const R = rooms[name];
  if (R.loading) return R.loading;
  return R.loading = (async () => {
    const base = `assets/rooms/${name}/`;
    const hdr = await new RGBELoader().setDataType(THREE.HalfFloatType).loadAsync(base + 'probe.hdr');
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    R.env = pmrem.fromEquirectangular(hdr).texture; hdr.dispose();
    const gl = await loader.loadAsync(base + 'room.gltf');
    const a = MOBILE ? 4 : renderer.capabilities.getMaxAnisotropy(), seen = new Set();
    gl.scene.traverse(o => {
      if (!o.isMesh) return;
      o.frustumCulled = false;
      if (seen.has(o.material)) return; seen.add(o.material);
      const m = o.material; patch(m, R);
      ['map', 'normalMap', 'roughnessMap'].forEach(k => { if (m[k]) m[k].anisotropy = Math.min(a, 8); });
      if (m.normalMap) m.normalScale.set(.9, .9);
      if (m.alphaTest > 0) { m.alphaToCoverage = true; m.side = THREE.DoubleSide; }
      else if (R.meta.name === 'cave') m.side = THREE.DoubleSide;
    });
    R.group = new THREE.Group(); R.group.add(gl.scene);
    if (R.meta.sky) {
      const [x0, y0, z0, x1, y1, z1] = R.meta.sky;
      const tex = await new THREE.TextureLoader().loadAsync(base + 'sky.jpg');
      tex.colorSpace = THREE.SRGBColorSpace; tex.generateMipmaps = false; tex.minFilter = THREE.LinearFilter; tex.wrapS = THREE.RepeatWrapping;
      const g = new THREE.BoxGeometry(x1 - x0, z1 - z0, y1 - y0);
      const m = new THREE.ShaderMaterial({ vertexShader: skyVS, fragmentShader: skyFS, uniforms: { map: { value: tex }, gain: { value: R.meta.skygain ?? 1 } }, side: THREE.BackSide, depthWrite: false, toneMapped: false });
      R.skyTex = tex;
      const sky = R.sky = new THREE.Mesh(g, m); sky.position.set((x0 + x1) / 2, (z0 + z1) / 2, -(y0 + y1) / 2); sky.renderOrder = -10; sky.frustumCulled = false;
      R.group.add(sky);
    }
    // faint window glass catches a reflection of the room
    if (R.meta.windows?.length) {
      const pos = [], idx = [];
      R.meta.windows.forEach((w, i) => { w.forEach(p => pos.push(p[0], p[2], -p[1])); idx.push(i * 4, i * 4 + 1, i * 4 + 2, i * 4, i * 4 + 2, i * 4 + 3); });
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setIndex(idx); g.computeVertexNormals();
      const m = R.meta.rainGlass ? new THREE.ShaderMaterial({ vertexShader: skyVS, fragmentShader: rainFS, side: THREE.DoubleSide, toneMapped: false, transparent: true, depthWrite: false,
          uniforms: { uTime: shared.uTime } })
        : new THREE.MeshStandardMaterial({ color: 0x000000, roughness: .05, metalness: 0, envMap: R.env, envMapIntensity: .22, transparent: true, opacity: .16, side: THREE.DoubleSide, depthWrite: false });
      const glass = new THREE.Mesh(g, m); glass.frustumCulled = false; R.group.add(glass);
    }
    (R.meta.flames || []).forEach(f => addFlame(R, f));
    if (R.meta.sun && R.meta.shaftGain) addShafts(R);
    addDust(R);
    R.gongs = {};
    gl.scene.traverse(o => { const m = /gong_([abc])/.exec(o.name); if (o.isMesh && m) R.gongs[{ a: 'g40', b: 'g32', c: 'g24' }[m[1]]] = mountGong(R, o); });
    if (R.meta.land) await addLand(R, gl);
    if (R.meta.teacher) await addTeacher(R);
    scene.add(R.group); R.ready = true;
    window.__loaded = (window.__loaded || 0) + 1;
  })();
}

// ---- the teacher
let idleData = null;
function batikTexture() {   // a woven checked cloth pattern, drawn in the browser
  const c = document.createElement('canvas'); c.width = c.height = 256; const x = c.getContext('2d'); x.fillStyle = '#3c2518'; x.fillRect(0, 0, 256, 256);
  for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { x.fillStyle = (i + j) % 2 ? '#8a5a2b' : '#231610'; x.save(); x.translate(i * 32 + 16, j * 32 + 16); x.rotate(Math.PI / 4); x.fillRect(-10, -10, 20, 20); x.fillStyle = '#c9a15a'; x.fillRect(-3, -3, 6, 6); x.restore(); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(3, 2); t.colorSpace = THREE.SRGBColorSpace; return t;
}
async function addTeacher(R) {
  const cfg = SCORES[R.meta.name].teacher ?? {}, L = new THREE.TextureLoader(), T = `assets/teacher/${cfg.who}/`, tex = {};
  await Promise.all(['body_c', 'body_n', 'body_r', 'head_c', 'head_n', 'head_r'].map(async k => {
    const t = tex[k] = await L.loadAsync(T + k + '.jpg'); t.flipY = false; t.colorSpace = k.endsWith('_c') ? THREE.SRGBColorSpace : THREE.NoColorSpace; t.anisotropy = 8;
  }));
  if (await fetch(T + 'op.png', { method: 'HEAD' }).then(r => r.ok).catch(() => false)) { const op = tex.op = await L.loadAsync(T + 'op.png'); op.flipY = false; op.colorSpace = THREE.SRGBColorSpace; }
  const gl = await loader.loadAsync(T + (R.meta.teacher.pose === 'stand' ? 'teacher_stand.glb' : 'teacher.glb'));
  idleData ??= await fetch('assets/teacher/idle.json').then(r => r.json()).catch(() => null);
  tex.batik ??= batikTexture();
  R.teacher = new Teacher(gl, R, tex, { ...cfg, idle: idleData }); if (cur === R.meta.name) R.teacher.greet();
}

// ---- candle flames
const flameMat = () => new THREE.ShaderMaterial({
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, toneMapped: false,
  uniforms: { uTime: shared.uTime, seed: { value: Math.random() * 40 } },
  vertexShader: `varying vec2 vU;uniform float uTime,seed;void main(){vU=uv;vec3 p=position;float k=uv.y*uv.y;p.x+=sin(uTime*7.+seed)*.012*k+sin(uTime*13.+seed*2.)*.006*k;
    vec4 c=modelViewMatrix*vec4(0.,0.,0.,1.);vec2 s=vec2(length(modelMatrix[0].xyz),length(modelMatrix[1].xyz));c.xy+=p.xy*s;gl_Position=projectionMatrix*c;}`,
  fragmentShader: `varying vec2 vU;uniform float uTime,seed;void main(){vec2 u=vU*2.-1.;float y=vU.y;float w=mix(.62,.02,pow(y,1.3))*(1.-.15*sin(uTime*11.+seed));
    float d=abs(u.x)/max(w,.01);float a=smoothstep(1.,.2,d)*smoothstep(0.,.1,y)*smoothstep(1.,.65,y);
    vec3 c=mix(vec3(1.,.55,.14),vec3(1.,.93,.75),smoothstep(.75,.1,d)*smoothstep(.75,.2,y));c=mix(c,vec3(.16,.26,.8),smoothstep(.16,.0,y)*.8);
    gl_FragColor=vec4(c*2.2,a);
#include <colorspace_fragment>
  }`,
});
const glowTex = (() => { const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d'); const g = x.createRadialGradient(64, 64, 0, 64, 64, 64); g.addColorStop(0, '#ffc98a'); g.addColorStop(.25, '#a8602766'); g.addColorStop(1, '#00000000'); x.fillStyle = g; x.fillRect(0, 0, 128, 128); return new THREE.CanvasTexture(c); })();
function addFlame(R, f) {
  const q = new THREE.Mesh(new THREE.PlaneGeometry(1, 1, 1, 6).translate(0, .5, 0), flameMat());
  const s = f.h * 1.15; q.scale.set(s * .55, s, 1); q.frustumCulled = false; b2t(f.pos, q.position); q.position.y -= s * .15; R.group.add(q);
  const g = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, opacity: .34, toneMapped: false }));
  g.scale.setScalar(.4); b2t(f.pos, g.position); R.group.add(g);
}

// ---- light in the air: soft beams from each window, and slow dust
function addShafts(R) {
  const sun = b2t(R.meta.sun).normalize(), L = 5.5, pos = [], fade = [];
  for (const w of R.meta.windows) {
    const q = w.map(p => b2t(p)); const c = q.reduce((a, b) => a.add(b.clone()), new THREE.Vector3()).multiplyScalar(.25);
    const nrm = q[1].clone().sub(q[0]).cross(q[3].clone().sub(q[0])).normalize();
    const off = Math.sign(nrm.dot(sun.clone().negate().sub(new THREE.Vector3()))) || 1;
    for (let i = 0; i < 4; i++) {
      const a = q[i].clone().lerp(c, .06), b = q[(i + 1) % 4].clone().lerp(c, .06), a2 = a.clone().addScaledVector(sun, -L), b2 = b.clone().addScaledVector(sun, -L);
      [a, b, b2, a, b2, a2].forEach((p, k) => { pos.push(p.x, p.y, p.z); fade.push(k === 2 || k === 4 || k === 5 ? 0 : 1); });
    }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('fade', new THREE.Float32BufferAttribute(fade, 1));
  const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, toneMapped: false, uniforms: { gain: { value: .022 * R.meta.shaftGain } },
    vertexShader: 'attribute float fade;varying float f;varying vec3 vN,vV;void main(){f=fade;vec4 w=modelMatrix*vec4(position,1.);vV=normalize(cameraPosition-w.xyz);gl_Position=projectionMatrix*viewMatrix*w;}',
    fragmentShader: 'varying float f;uniform float gain;void main(){gl_FragColor=vec4(vec3(1.,.86,.66)*gain*f*f,1.);}' });
  const o = new THREE.Mesh(g, m); o.frustumCulled = false; R.group.add(o);
}
function addDust(R) {
  const b = R.meta.box, n = 260, p = new Float32Array(n * 3);
  for (let i = 0; i < n; i++) { p[i * 3] = b[0] + Math.random() * (b[3] - b[0]); p[i * 3 + 1] = .2 + Math.random() * Math.min(2.8, b[5]); p[i * 3 + 2] = -(b[1] + Math.random() * (b[4] - b[1])); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(p, 3));
  const m = new THREE.ShaderMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false, uniforms: { uTime: shared.uTime },
    vertexShader: 'uniform float uTime;varying float a;void main(){vec3 q=position;float s=position.x*3.1+position.z*1.7;q+=vec3(sin(uTime*.07+s),sin(uTime*.05+s*2.)*.5,cos(uTime*.06+s))*.35;vec4 mv=modelViewMatrix*vec4(q,1.);float d=-mv.z;a=smoothstep(.2,.9,d)*smoothstep(4.5,1.5,d);gl_PointSize=clamp(14./max(d,.3),1.,5.);gl_Position=projectionMatrix*mv;}',
    fragmentShader: 'varying float a;void main(){float r=length(gl_PointCoord-.5);gl_FragColor=vec4(vec3(1.,.9,.76)*.05*a*smoothstep(.5,.1,r),1.);}' });
  const o = new THREE.Points(g, m); o.frustumCulled = false; R.group.add(o);
}
// Each gong hangs from its own pivot and swings a little when struck
function mountGong(R, mesh) {
  mesh.geometry.computeBoundingBox(); const bb = mesh.geometry.boundingBox, sz = bb.getSize(new THREE.Vector3()), c = bb.getCenter(new THREE.Vector3());
  const piv = new THREE.Group(); piv.position.set(c.x, bb.max.y + .25, c.z); mesh.parent.add(piv); mesh.position.sub(piv.position); piv.add(mesh);
  return { piv, axis: sz.x < sz.z ? 'z' : 'x', a: 0, v: 0, w: 2 * Math.PI * .55 };
}

// ---- walking
function inRects(x, y) {
  for (const r of world.walk) if (x >= Math.min(r[0], r[2]) && x <= Math.max(r[0], r[2]) && y >= Math.min(r[1], r[3]) && y <= Math.max(r[1], r[3])) return true;
  return false;
}
function heightAt(x, y) {
  const L = world.land; if (!L) return 0;
  const fx = x - L.x0, fy = y - L.y0, i = Math.floor(fx), j = Math.floor(fy), a = fx - i, b = fy - j;
  const h = (ii, jj) => L.h[Math.min(L.ny - 1, Math.max(0, jj)) * L.nx + Math.min(L.nx - 1, Math.max(0, ii))];
  return (h(i, j) * (1 - a) + h(i + 1, j) * a) * (1 - b) + (h(i, j + 1) * (1 - a) + h(i + 1, j + 1) * a) * b;
}
function inHut(x, y) { for (const n of world.rooms) { const m = rooms[n].meta, b = m.box, e = .42; if (x > Math.min(b[0], m.door[0]) - e && x < Math.max(b[3], m.door[0]) + e && y > Math.min(b[1], m.door[1]) - e && y < Math.max(b[4], m.door[1]) + e) return true; } return false; }
function outdoorOk(x, y) {
  const L = world.land; if (!L) return false;
  const i = Math.round(x - L.x0), j = Math.round(y - L.y0); if (i < 4 || j < 4 || i >= L.nx - 4 || j >= L.ny - 4) return false;
  if (L.steep[j * L.nx + i]) return false;
  return !inHut(x, y);
}
function free(x, y) {
  if (!inRects(x, y) && !world.walkc.some(c => Math.hypot(x - c[0], y - c[1]) < c[2]) && !outdoorOk(x, y)) return false;
  for (const o of world.obstacles) { const dx = x - o[0], dy = y - o[1]; if (dx * dx + dy * dy < o[2] * o[2]) return false; }
  return true;
}
function move(dx, dy) {
  const nx = state.x + dx, ny = state.y + dy, a = state.x, b = state.y;
  if (free(nx, ny)) { state.x = nx; state.y = ny; }
  else if (free(nx, state.y)) state.x = nx;
  else if (free(state.x, ny)) state.y = ny;
  else { const L = Math.hypot(dx, dy) || 1; for (const a of [.6, -.6, 1.1, -1.1]) { const c = Math.cos(a), n = Math.sin(a), mx = (dx * c - dy * n), my = (dx * n + dy * c); if (free(state.x + mx, state.y + my)) { state.x += mx; state.y += my; break; } } }
  const d = Math.hypot(state.x - a, state.y - b); state.stepD += d;
  if (state.stepD > .72) { state.stepD = 0; if (audio.ctx && FOOTSTEPS) audio.step(surfaceAt()); }
}
function roomAt(x, y) {
  for (const n of world.rooms) { const b = rooms[n]?.meta.box; if (b && x > b[0] - .05 && x < b[3] + .05 && y > b[1] - .05 && y < b[4] + .05) return n; }
  return null;
}
const surfaceAt = () => { const r = roomAt(state.x, state.y); return r ? rooms[r].meta.surface : world.hall?.surface ?? 'stone'; };

// ---- input
let drag = null, moved = 0, dragId = null;
renderer.domElement.addEventListener('pointerdown', e => { if (drag) return; drag = [e.clientX, e.clientY]; moved = 0; dragId = e.pointerId; renderer.domElement.setPointerCapture(e.pointerId); });
const dragEnd = e => { if (e.pointerId !== dragId) return; const tap = drag && moved < 8 && started && e.type === 'pointerup'; drag = null; dragId = null; if (tap) strikeAt(e.clientX, e.clientY); };
addEventListener('pointerdown', () => audio.wake(), true); document.addEventListener('visibilitychange', () => { if (!document.hidden) audio.wake(); });
addEventListener('pointerup', dragEnd); addEventListener('pointercancel', dragEnd);
addEventListener('pointermove', e => {
  if (!drag || e.pointerId !== dragId) return; moved += Math.abs(e.clientX - drag[0]) + Math.abs(e.clientY - drag[1]);
  state.yaw -= (e.clientX - drag[0]) * .0035; state.pitch = THREE.MathUtils.clamp(state.pitch - (e.clientY - drag[1]) * .0035, -1.25, 1.45);
  drag = [e.clientX, e.clientY];
});
addEventListener('keydown', e => { keys[e.code] = true; if (e.code === 'KeyM') rest('lie'); if (e.code === 'KeyN') rest('sit'); if (e.code === 'KeyH' && started) setHud(document.body.classList.contains('nohud')); if (e.code === 'KeyF' && started && fsCan()) fsSet(!fsEl()); });
addEventListener('keyup', e => keys[e.code] = false);
addEventListener('resize', () => { camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix(); renderer.setSize(innerWidth, innerHeight); composer?.setSize(innerWidth, innerHeight); });

const ray = new THREE.Raycaster(), v2 = new THREE.Vector2();
function strikeAt(cx, cy) {
  if (!cur) return;
  v2.set(cx / innerWidth * 2 - 1, -(cy / innerHeight) * 2 + 1); ray.setFromCamera(v2, camera);
  hitInstrument(ray.ray.origin, ray.ray.direction);
}
const tmp = new THREE.Vector3();
function hitInstrument(o, d) {
  const live = audio.rooms[cur]; if (!live) return false;
  let best = null, bd = .55;
  for (const [id, p] of Object.entries(rooms[cur].meta.instruments)) {
    const q = b2t(p, tmp).clone().sub(o); const along = q.dot(d); if (along < 0 || along > 9) continue;
    const off = q.sub(d.clone().multiplyScalar(along)).length(); if (off < bd) { bd = off; best = id; }
  }
  if (!best) return false;
  const hit = live.score.touch?.(best) ?? touchDefault(best); if (hit) audio.play(live, best, hit, .8, { delay: .005 });
  return true;
}
function touchDefault(id) {
  const m = audio.buf[cur]; if (!m) return null;
  const T = { jar: 'drip0', ocean: 'ocean0', stick: 'stick0', mono: 'mono0', tanpura: 'tan10', drum: 'd4', didge: 'didge0', earth: 'ch_earth0', water: 'ch_water0', air: 'ch_air0', fire: 'ch_fire0', g40: 'g40_h1', g32: 'g32_h1', g24: 'g24_h1' };
  if (m[T[id]]) return T[id];
  for (const k of [`${id}_s1`, `${id}_s`, `${id}_h1`, id]) if (m[k]) return k;
  return null;
}

// ---- sitting and lying
function nearestSeat() {
  const list = rooms[cur]?.meta.seats ?? [];
  let b = null, d = 1e9; for (const s of list) { const q = Math.hypot(s.pos[0] - state.x, s.pos[1] - state.y); if (q < d) { d = q; b = s; } } return b;
}
// The Sit and Lie down buttons both go to the nearest mat. Press the other one to change position, or the same one to get up.
function poseUi() {
  for (const [id, label, mode, word] of [['bSit', 'sitLabel', 'sit', L10.sit], ['bLie', 'lieLabel', 'lie', L10.lie]]) {
    const on = state.resting && state.pose === mode; $(id).classList.toggle('main', !!on); $(id).setAttribute('aria-pressed', !!on); $(label).textContent = on ? L10.up : word;
  }
}
const sitLabel = on => { if (!on) state.resting = false; poseUi(); };
function getUp() { state.sit = 0; state.aim = 2.5; state.aimPitch = 0; state.target = state.ret ? { x: state.ret[0], y: state.ret[1], sit: false } : null; sitLabel(false); document.body.classList.remove('quiet'); }
function rest(mode) {
  if (state.resting) {
    if (state.pose === mode) return getUp();
    state.pose = mode; state.aim = 3; poseUi(); return;
  }
  state.pose = mode;
  const s = nearestSeat(); if (!s) { flash(L10.walkFirst, ''); return; }
  state.ret = [state.x, state.y]; state.target = { x: s.pos[0], y: s.pos[1], sit: true, look: s.look }; state.resting = true; poseUi();
}
$('bSit').onclick = () => rest('sit'); $('bLie').onclick = () => rest('lie');
$('bSound').onclick = () => { audio.setMuted(!audio.muted); $('soundLabel').textContent = audio.muted ? L10.muted : L10.sound; $('waves').style.display = audio.muted ? 'none' : ''; $('bSound').classList.toggle('on', audio.muted); $('bSound').setAttribute('aria-pressed', audio.muted); };
$('bHome').onclick = () => { sheet(null); setEyes(false); keepAwake(false); if (fsEl()) fsSet(false); audio.stop(); renderer.setAnimationLoop(null); started = false; cur = null; lastRoom = undefined; document.body.classList.remove('playing', 'quiet'); $('home').classList.remove('hide'); $('fade').style.opacity = 1; };

// ---- on-screen controls
// Joystick: up and down walk, left and right turn. The further you push, the faster you go.
const stick = $('stick'), knob = $('knob'), joy = { x: 0, y: 0, id: null };
function joyMove(e) {
  const r = stick.getBoundingClientRect(), R = r.width / 2, dx = e.clientX - r.left - R, dy = e.clientY - r.top - R, max = R - 22, d = Math.hypot(dx, dy), k = d > max ? max / d : 1;
  knob.style.transform = `translate(${dx * k}px,${dy * k}px)`;
  const dead = v => Math.abs(v) < .12 ? 0 : (v - Math.sign(v) * .12) / .88;
  joy.x = dead(dx * k / max); joy.y = dead(-dy * k / max);
}
function joyEnd(e) { if (e.pointerId !== joy.id) return; joy.id = null; joy.x = joy.y = 0; knob.style.transform = ''; stick.classList.remove('on'); }
stick.addEventListener('pointerdown', e => { e.preventDefault(); if (joy.id !== null) return; joy.id = e.pointerId; stick.classList.add('on'); try { stick.setPointerCapture(e.pointerId); } catch { } joyMove(e); if (state.sit) { getUp(); state.target = null; } });
stick.addEventListener('pointermove', e => { if (e.pointerId === joy.id) joyMove(e); });
stick.addEventListener('pointerup', joyEnd); stick.addEventListener('pointercancel', joyEnd); stick.addEventListener('lostpointercapture', joyEnd);
stick.addEventListener('contextmenu', e => e.preventDefault());
$('vol').oninput = e => audio.setVolume(+e.target.value);
const speed = fast => { keys.ShiftLeft = fast; $('spFast').classList.toggle('on', fast); $('spSlow').classList.toggle('on', !fast); };
$('spSlow').onclick = () => speed(false); $('spFast').onclick = () => speed(true);
function setHud(on) { document.body.classList.toggle('nohud', !on); $('bHide').setAttribute('aria-checked', !on); if (!on) sheet(null); }
$('bHide').onclick = () => setHud(false);
$('show').onclick = () => setHud(true);
// panels that slide up. Only one is open at a time.
function sheet(id) {
  for (const [k, btn] of [['sheetRooms', 'bRooms'], ['sheetSet', 'bSettings'], ['sheetIos', 'bFullTab']]) { const on = k === id; $(k).classList.toggle('open', on); if (k !== 'sheetIos') { $(btn).classList.toggle('on', on); $(btn).setAttribute('aria-expanded', on); } }
  $('scrim').classList.toggle('on', !!id);
}
const showRooms = on => sheet(on ? 'sheetRooms' : null);
$('bRooms').onclick = () => sheet($('sheetRooms').classList.contains('open') ? null : 'sheetRooms');
$('bSettings').onclick = () => sheet($('sheetSet').classList.contains('open') ? null : 'sheetSet');
$('scrim').onclick = () => sheet(null);
$('iosClose').onclick = () => sheet(null);
$('lEn').onclick = () => setLang('en'); $('lZh').onclick = () => setLang('zh'); $('langHome').onclick = () => setLang(lang === 'zh' ? 'en' : 'zh');
addEventListener('keydown', e => { if (e.code === 'Escape') sheet(null); });
function buildRooms() {
  const add = (label, id, img) => { const b = document.createElement('button'); b.className = 'card'; b.dataset.room = id; b.innerHTML = `<img src="assets/thumbs/${img}.jpg" alt=""><b></b>`; b.querySelector('b').textContent = label; b.onclick = () => goTo(id); $('rooms').append(b); };
  add(roomName(''), '', 'gallery');
  world.rooms.forEach(n => add(roomName(n), n, n));
  refreshText = () => { document.querySelectorAll('#rooms .card').forEach(c => { c.querySelector('b').textContent = roomName(c.dataset.room); }); markRoom(true); poseUi(); fsLabel(); $('soundLabel').textContent = audio.muted ? L10.muted : L10.sound; };
}
let enteredAt = 0;
function markRoom(keep) {
  document.querySelectorAll('#rooms .card').forEach(b => { const on = b.dataset.room === (cur ?? ''); b.classList.toggle('here', on); b.querySelector('i')?.remove(); if (on) { const i = document.createElement('i'); i.textContent = L10.here; b.append(i); } });
  $('nowName').textContent = roomName(cur); if (!keep) enteredAt = performance.now();
}
setInterval(() => { if (!started || !cur) { $('nowTime').textContent = ''; return; } const t = Math.floor((performance.now() - enteredAt) / 1000); $('nowTime').textContent = `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`; }, 1000);
function placeIn(n) {
  const m = rooms[n].meta, d = [m.probe[0] - m.door[0], m.probe[1] - m.door[1]], l = Math.hypot(...d);
  const inn = n === 'cave' ? 3.6 : 1.9; state.x = m.door[0] + d[0] / l * inn; state.y = m.door[1] + d[1] / l * inn; state.yaw = Math.atan2(-d[0], d[1]); state.pitch = 0;
}
// Go straight to a room: fade to black, move, load it, fade back
let going = false;
async function goTo(n) {
  if (going) return; going = true; sheet(null);
  const f = $('fade'); f.style.transition = 'opacity .5s'; f.style.opacity = 1;
  await new Promise(r => setTimeout(r, 550));
  state.sit = 0; state.sitT = 0; state.target = null; state.ret = null; sitLabel(false); document.body.classList.remove('quiet');
  if (n) placeIn(n); else { state.x = world.spawn[0]; state.y = world.spawn[1]; state.yaw = 0; state.pitch = 0; }
  await nearLoad(); f.style.transition = ''; f.style.opacity = 0; going = false;
}

let titleT;
function flash(a, b) { const t = $('title'); t.querySelector('b').textContent = a; t.querySelector('small').textContent = b; t.style.opacity = 1; clearTimeout(titleT); titleT = setTimeout(() => t.style.opacity = 0, 5000); }

// ---- the world
async function init() {
  world = await (await fetch('assets/world.json')).json();
  await Promise.all([...world.rooms, 'hall'].map(async n => { const r = await fetch(`assets/rooms/${n}/room.json`); if (r.ok) rooms[n] = { meta: await r.json() }; }));
  world.rooms = world.rooms.filter(n => rooms[n]);
  world.walk = []; world.obstacles = []; world.walkc = [];
  for (const n of [...world.rooms, 'hall']) { const m = rooms[n]?.meta; if (!m) continue; world.walk.push(...m.walk); world.obstacles.push(...m.obstacles); world.walkc.push(...(m.walkc || [])); }
  (world.extraWalk || []).forEach(r => world.walk.push(r));
  world.hall = rooms.hall?.meta; world.rocks = rooms.hall?.meta.rocks ?? [];
  const start = params.get('room');
  if (start && rooms[start]) {
    placeIn(start);
  } else { state.x = world.spawn[0]; state.y = world.spawn[1]; state.yaw = (world.spawn[2] || 0) * Math.PI / 180; }
  buildRooms();
  if (rooms.hall) await loadRoomGeometry('hall');
  renderer.compile(scene, camera);
}
// ---- my figure: a plain smooth person, seen from just behind. It walks when you walk.
const me = { on: true, group: new THREE.Group(), legs: [], arms: [], d: 2.6, k: 0, phase: 0 };
try { me.on = localStorage.getItem('seeMe') !== '0'; } catch { }
{
  const mat = me.mat = new THREE.MeshStandardMaterial({ color: 0xcfc6b6, roughness: .68, metalness: 0 }), part = (r, l, y = 0) => { const m = new THREE.Mesh(new THREE.CapsuleGeometry(r, l, 6, 14), mat); m.position.y = y; m.frustumCulled = false; return m; };
  const torso = part(.17, .42, 1.12); torso.scale.set(1.05, 1, .72); const hips = part(.15, .1, .86); hips.scale.set(1.1, 1, .78);
  const neck = part(.05, .06, 1.47), head = new THREE.Mesh(new THREE.SphereGeometry(.112, 20, 16), mat); head.position.y = 1.6; head.scale.set(.92, 1.08, 1); head.frustumCulled = false;
  me.group.add(torso, hips, neck, head);
  for (const s of [-1, 1]) {
    const leg = new THREE.Group(); leg.position.set(s * .1, .84, 0); const up = part(.075, .3); up.position.y = -.2; const knee = new THREE.Group(); knee.position.y = -.42; const low = part(.06, .3); low.position.y = -.2; const foot = part(.05, .13); foot.rotation.x = Math.PI / 2; foot.position.set(0, -.41, -.05); knee.add(low, foot); leg.add(up, knee); me.group.add(leg); me.legs.push({ leg, knee, s });
    const arm = new THREE.Group(); arm.position.set(s * .23, 1.36, 0); arm.rotation.z = s * .1; const u = part(.05, .22); u.position.y = -.16; const el = new THREE.Group(); el.position.y = -.31; const f = part(.042, .22); f.position.y = -.15; const h = new THREE.Mesh(new THREE.SphereGeometry(.05, 12, 10), mat); h.position.y = -.31; h.frustumCulled = false; el.add(f, h); arm.add(u, el); me.group.add(arm); me.arms.push({ arm, el, s });
  }
  const c = document.createElement('canvas'); c.width = c.height = 128; const x = c.getContext('2d'), g = x.createRadialGradient(64, 64, 8, 64, 64, 62); g.addColorStop(0, '#000a'); g.addColorStop(.6, '#0005'); g.addColorStop(1, '#0000'); x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  me.shadow = new THREE.Mesh(new THREE.PlaneGeometry(1.1, 1.1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false, toneMapped: false })); me.shadow.frustumCulled = false;
  scene.add(me.group, me.shadow); me.group.visible = me.shadow.visible = false;
}
$('bMe').setAttribute('aria-checked', me.on);
$('bMe').onclick = () => { me.on = !me.on; $('bMe').setAttribute('aria-checked', me.on); try { localStorage.setItem('seeMe', me.on ? '1' : '0'); } catch { } };
// The camera stays behind the figure, and comes closer when a wall is in the way.
function camBehind(x, y, yaw, want) {
  const bx = Math.sin(yaw), by = -Math.cos(yaw); let d = .4;
  const box = cur ? rooms[cur].meta.box : null;
  for (; d < want; d += .15) {
    const px = x + bx * d, py = y + by * d;
    if (box && (px < box[0] + .25 || px > box[3] - .25 || py < box[1] + .25 || py > box[4] - .25)) break;   // inside a room the camera stays in the room
    if (!free(px, py) && !obstacleOnly(px, py)) break;
  }
  return Math.max(.5, d - .25);
}
function obstacleOnly(x, y) { return inRects(x, y) || world.walkc.some(c => Math.hypot(x - c[0], y - c[1]) < c[2]) || outdoorOk(x, y); }
function updateMe(dt, eyeZ, ground) {
  const show = me.on && !renderer.xr.isPresenting && !window.__shot && !state.sit && !state.target?.sit && me.d > 1.15;
  me.k += ((show ? 1 : 0) - me.k) * Math.min(1, dt * 3.5);
  const vis = me.k > .02; me.group.visible = me.shadow.visible = vis; if (!vis) return null;
  const moved = Math.hypot(state.x - (me.px ?? state.x), state.y - (me.py ?? state.y)); me.px = state.x; me.py = state.y;
  const sp = Math.min(1, moved / Math.max(dt, .001) / 1.3); me.w = (me.w ?? 0) + (sp - (me.w ?? 0)) * Math.min(1, dt * 7); me.phase += moved * 4.4;
  const w = me.w, s1 = Math.sin(me.phase);
  for (const l of me.legs) { const a = s1 * l.s; l.leg.rotation.x = a * .55 * w; l.knee.rotation.x = Math.max(0, -a * .5 + .25) * 1.25 * w; }
  for (const a of me.arms) { const q = -s1 * a.s; a.arm.rotation.x = q * .42 * w; a.el.rotation.x = -.25 - .35 * Math.max(0, q) * w; }
  const R = rooms[cur ?? 'hall']; if (R?.env && me.mat.envMap !== R.env) { me.mat.envMap = R.env; me.mat.needsUpdate = true; }
  me.mat.envMapIntensity = cur ? 1.3 : .75;
  const bob = Math.abs(Math.sin(me.phase)) * .025 * w;
  me.group.position.set(state.x, ground + bob, -state.y); me.group.rotation.y = state.yaw; me.group.scale.setScalar(1);
  me.shadow.position.set(state.x, ground + .03, -state.y); me.shadow.material.opacity = me.k;
  return me.k;
}

// ---- eyes closed: the view fades to the dark red of closed lids, the sound goes on.
// A headset cannot show page overlays, so there the same fade comes from the exposure.
let eyesShut = false, eyesT, wake = null;
async function keepAwake(on) {   // a phone that sleeps would stop the sound
  try { if (on && !wake && navigator.wakeLock) { wake = await navigator.wakeLock.request('screen'); wake.addEventListener('release', () => { wake = null; }); } else if (!on) { await wake?.release(); wake = null; } } catch { }
}
function setEyes(shut) {
  if (shut === eyesShut) return; eyesShut = shut; const e = $('eyes'); clearTimeout(eyesT); sheet(null);
  if (shut) { e.classList.add('show'); requestAnimationFrame(() => requestAnimationFrame(() => e.classList.add('on'))); e.classList.remove('hint'); eyesT = setTimeout(() => { e.classList.add('hint'); eyesT = setTimeout(() => e.classList.remove('hint'), 4500); }, 3000); }
  else { e.classList.remove('on', 'hint'); eyesT = setTimeout(() => e.classList.remove('show'), 2800); }
}
$('bEyes').onclick = () => setEyes(true);
$('eyes').onclick = () => { audio.wake(); setEyes(false); };
addEventListener('keydown', e => { if (eyesShut && !['ShiftLeft', 'MetaLeft'].includes(e.code)) setEyes(false); else if (e.code === 'KeyE' && started) setEyes(true); });
document.addEventListener('visibilitychange', () => { if (!document.hidden && started) keepAwake(true); });

// ---- full screen. iPhone Safari has no full screen for pages, so there the page is added to the Home Screen.
const fsEl = () => document.fullscreenElement ?? document.webkitFullscreenElement;
const fsCan = () => !!(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen);
const standalone = () => matchMedia('(display-mode: fullscreen), (display-mode: standalone)').matches || navigator.standalone === true;
function fsSet(on) {
  const d = document.documentElement;
  if (on) (d.requestFullscreen ?? d.webkitRequestFullscreen)?.call(d)?.catch?.(() => { });
  else (document.exitFullscreen ?? document.webkitExitFullscreen)?.call(document)?.catch?.(() => { });
}
const fsLabel = () => { const on = !!fsEl(); $('fsLabel').textContent = on ? L10.exit : L10.full; $('fsIn').style.display = on ? 'none' : ''; $('fsOut').style.display = on ? '' : 'none'; $('bFullTab').classList.toggle('on', on); $('bFullTab').setAttribute('aria-pressed', on); };
document.addEventListener('fullscreenchange', fsLabel); document.addEventListener('webkitfullscreenchange', fsLabel);
$('bFullTab').onclick = () => {
  if (fsCan()) fsSet(!fsEl());
  else sheet('sheetIos');
};
if (standalone()) $('bFullTab').style.display = 'none';

async function enter() {
  audio.unlock();
  if (fsCan() && !standalone() && !params.get('auto')) fsSet(true);
  $('enter').disabled = true; $('load').textContent = MOBILE ? L10.openingPhone : L10.opening;
  if (!world) await init();
  audio.onHit = onHit; audio.onEnd = R => { if (R.meta.name !== cur) return; flash(L10.ended, L10.ended2); if (eyesShut) { const e = $('eyes'), sp = e.querySelector('span'); sp.textContent = L10.ended; e.classList.add('hint'); setTimeout(() => { e.classList.remove('hint'); sp.textContent = L10.eyesOpen; }, 7000); } };
  await audio.start();
  await nearLoad();
  world.fieldWarm?.();
  document.body.classList.add('playing'); markRoom(); $('home').classList.add('hide'); audio.wake(); $('fade').style.opacity = 0; $('enter').disabled = false; $('load').textContent = L10.headphones;
  const touch = matchMedia('(pointer:coarse)').matches;
  $('help').textContent = touch ? L10.helpTouch : L10.helpMouse;
  setTimeout(() => $('help').style.opacity = 0, 9000);
  if (!document.querySelector('#VRButton') && navigator.xr && await navigator.xr.isSessionSupported('immersive-vr').catch(() => false)) document.body.appendChild(VRButton.createButton(renderer));
  if ((params.get('intro') || !navigator.webdriver) && !params.get('room') && state.seen !== true) { state.intro = INTRO; state.seen = true; document.body.classList.add('intro'); addEventListener('pointerdown', () => { if (state.intro > 0) endIntro(); }, { once: true, capture: true }); }
  started = true; renderer.setAnimationLoop(frame); window.__ready = true; keepAwake(true);
  setTimeout(() => { if (audio.ctx?.state !== 'running') flash(L10.tapSound, L10.tapSound2); }, 2500);
}
$('enter').onclick = enter;

function onHit(room, id, gain, delay, mv, dur) {
  const now = audio.ctx.currentTime, g = rooms[room]?.gongs?.[id]; if (g) setTimeout(() => g.v += .012 * gain, delay * 1000);
  const t = rooms[room]?.teacher; if (t && mv) t.act(mv, id, now + delay, now, dur * (mv.drive ?? 0));
}

function unloadRoom(n) {
  const R = rooms[n]; scene.remove(R.group);
  R.group.traverse(o => { o.geometry?.dispose(); const m = o.material; if (m) { for (const k of ['map', 'normalMap', 'roughnessMap', 'lightMap', 'alphaMap']) m[k]?.dispose(); m.dispose(); } });
  R.env?.dispose(); THREE.Cache.clear(); R.group = null; R.sky = null; R.teacher = null; R.gongs = null; R.ready = false; R.loading = null;
}
// Load nearby rooms; give each one a sound level that depends on where you stand.
let nearT = 0;
async function nearLoad() {
  const near = [];
  for (const n of world.rooms) {
    const m = rooms[n].meta, d = Math.hypot(m.door[0] - state.x, m.door[1] - state.y);
    if (d < 28 || roomAt(state.x, state.y) === n) near.push([d, n]);
  }
  near.sort((a, b) => a[0] - b[0]);
  await Promise.all(near.slice(0, MOBILE ? 2 : 4).map(([, n]) => loadRoomGeometry(n)));
  // Inside a room only that room and the gallery are drawn. In the gallery only the nearest rooms are drawn.
  const here = roomAt(state.x, state.y), keep = near.slice(0, renderer.xr.isPresenting || MOBILE ? 2 : 4);
  for (const n of world.rooms) if (rooms[n].group) rooms[n].group.visible = here ? n === here : keep.some(q => q[1] === n);
  if (MOBILE) for (const n of world.rooms) { const R = rooms[n]; if (R.group && !near.slice(0, 2).some(q => q[1] === n)) unloadRoom(n); }
  if (!audio.ctx) return;
  const liveWant = near.filter(q => q[0] < 27).slice(0, MOBILE ? 1 : 2).map(q => q[1]);
  Object.keys(audio.rooms).forEach(n => { if (!liveWant.includes(n)) audio.leaveRange(n); });
  liveWant.forEach(n => audio.enterRange(rooms[n].meta));
}

const shotOff = () => false;
const INTRO = 11, INTRO_PATH = [[-60, -210, 96], [-34, -150, 62], [-6, -104, 26], [3.2, -76, 6], [3.2, -58, 3.27]];
function endIntro() { state.intro = 0; document.body.classList.remove('intro'); camera.rotation.set(0, 0, 0); clock.getDelta(); }
let lastRoom = null;
function frame() {
  const dt = Math.min(clock.getDelta(), .05);
  shared.uTime.value += dt;
  const xr = renderer.xr.isPresenting;
  let mx = 0, my = 0, turn = 0;
  if (keys.KeyW || keys.ArrowUp) my += 1; if (keys.KeyS || keys.ArrowDown) my -= 1;
  if (keys.KeyA) mx -= 1; if (keys.KeyD) mx += 1;
  if (keys.ArrowLeft) state.yaw += dt * 1.2; if (keys.ArrowRight) state.yaw -= dt * 1.2;
  my += joy.y; state.yaw -= joy.x * Math.abs(joy.x) * dt * 1.5;
  if (xr) {
    for (const src of renderer.xr.getSession().inputSources) {
      const a = src.gamepad?.axes; if (!a || a.length < 4) continue;
      if (src.handedness === 'left') { mx += a[2]; my -= a[3]; }
      if (src.handedness === 'right') {
        turn = a[2];
        const y = src.gamepad.buttons[4]?.pressed; if (y && !state.yb) rest('sit'); state.yb = y;
        const z = src.gamepad.buttons[5]?.pressed; if (z && !state.zb) setEyes(!eyesShut); state.zb = z;
      }
    }
    if (Math.abs(turn) > .7 && !state.snap) { state.yaw -= Math.sign(turn) * Math.PI / 6; state.snap = true; }
    if (Math.abs(turn) < .3) state.snap = false;
    if (Math.abs(mx) < .15) mx = 0; if (Math.abs(my) < .15) my = 0;
  }
  const speed = keys.ShiftLeft ? 2.4 : 1.35;
  if (state.target) {
    const t = state.target, dx = t.x - state.x, dy = t.y - state.y, d = Math.hypot(dx, dy);
    if (d > .04) { const s = Math.min(d, dt * 1.1); state.x += dx / d * s; state.y += dy / d * s; }
    else {
      if (t.sit) { state.sit = 1; state.aim = 3; if (state.pose === 'lie') document.body.classList.add('quiet'); const L_ = audio.rooms[cur]; if (L_?.ready && !L_.settled) { L_.settled = true; L_.t0 = audio.ctx.currentTime; L_.score.begin?.(L_, audio); } }
      state.target = null;
    }
    state.sitT += ((t.sit ? 1 : 0) - state.sitT) * dt * 1.2;
    if (t.sit && t.look) { const want = Math.atan2(-(t.look[0] - state.x), t.look[1] - state.y); let dd = want - state.yaw; dd = Math.atan2(Math.sin(dd), Math.cos(dd)); state.yaw += dd * dt * 1.2; state.pitch += ((xr ? 0 : POSE[state.pose].pitch) - state.pitch) * dt * .8; }
  } else if (!state.sit) {
    state.sitT += (0 - state.sitT) * dt * 1.5;
    if (mx || my) {
      let h = state.yaw;
      if (xr) { const e = new THREE.Euler().setFromQuaternion(camera.quaternion, 'YXZ'); h += e.y; }
      const c = Math.cos(h), s = Math.sin(h);
      move((-s * my + c * mx) * speed * dt, (c * my + s * mx) * speed * dt);
    }
  } else { state.sitT += (1 - state.sitT) * dt * 1.2; if (mx || my) { getUp(); state.target = null; } }

  if (state.intro > 0 && !xr) {
    state.intro -= dt; const u = 1 - Math.max(0, state.intro) / INTRO, e = u * u * (3 - 2 * u), pts = INTRO_PATH, t = e * (pts.length - 1), i = Math.min(pts.length - 2, Math.floor(t)), f = t - i, P_ = pts[i], Q_ = pts[i + 1], g = f * f * (3 - 2 * f);
    const px = P_[0] + (Q_[0] - P_[0]) * g, py = P_[1] + (Q_[1] - P_[1]) * g, pz = P_[2] + (Q_[2] - P_[2]) * g, lx = THREE.MathUtils.lerp(-8, 3.2, e * e), ly = THREE.MathUtils.lerp(260, 0, e * e), lz = THREE.MathUtils.lerp(70, 3.4, e * e);
    if (scene.fog) scene.fog.density = .0028 * e * e;
    rig.position.set(px, pz, -py); rig.rotation.set(0, 0, 0); camera.lookAt(lx, lz, -ly); renderer.toneMappingExposure = rooms.hall.meta.exposure ?? 1;
    if (state.intro <= 0) endIntro();
    if (composer) { gradePass.uniforms.uT.value = shared.uTime.value % 10; world.life?.(dt); composer.render(dt); } else renderer.render(scene, camera);
    return;
  }
  const shot = window.__shot; let eye;
  if (shot) { state.x = shot[0]; state.y = shot[1]; state.yaw = shot[3] * Math.PI / 180; state.pitch = shot[4] * Math.PI / 180; eye = shot[2]; }
  else {
    const P = POSE[state.pose]; state.poseH += (P.h - state.poseH) * dt * 1.4;
    if (state.aim > 0 && !xr) { state.aim -= dt; const pt = state.sit || state.target?.sit ? P.pitch : 0; state.pitch += (pt - state.pitch) * Math.min(1, dt * 1.6); }
    eye = THREE.MathUtils.lerp(standH, state.poseH, state.sitT) + Math.sin(state.stepD * 4.36) * .008;
  }
  if (xr) { rig.position.set(state.x, (state.gy ?? 0) - state.sitT * .55, -state.y); rig.rotation.set(0, state.yaw, 0); camera.position.set(0, 0, 0); }
  else if (!shot && (me.d += (camBehind(state.x, state.y, state.yaw, 3.3) - me.d) * Math.min(1, dt * 5), updateMe(dt, eye, state.gy ?? 0) !== null)) {
    const k = me.k, D = me.d * k, tilt = state.pitch, bx = Math.sin(state.yaw), by = -Math.cos(state.yaw), hd = D * Math.cos(tilt * .8);
    let camY = eye + (state.gy ?? 0) + k * (.62 - Math.sin(tilt * .8) * D); camY = Math.max(camY, (state.gy ?? 0) + .35); if (cur) camY = Math.min(camY, rooms[cur].meta.box[5] - .35);
    rig.position.set(state.x + bx * hd, camY, -(state.y + by * hd)); rig.rotation.set(0, state.yaw, 0); camera.rotation.set(state.pitch, 0, 0);
  } else { rig.position.set(state.x, eye + (shot ? 0 : state.gy ?? 0), -state.y); rig.rotation.set(0, state.yaw, 0); camera.rotation.set(state.pitch, 0, 0); }

  if (world.field && !shotOff()) { const q = Math.hypot(state.x - (world.fx ?? 1e9), state.y - (world.fy ?? 1e9)); if (q > 2) { world.fx = state.x; world.fy = state.y; world.field(state.x, state.y); } }
  const r = roomAt(state.x, state.y);
  const groundY = r ? 0 : heightAt(state.x, state.y); state.gy = (state.gy ?? groundY) + (groundY - (state.gy ?? groundY)) * Math.min(1, dt * 8);
  if (r !== lastRoom) { lastRoom = r; cur = r; markRoom(); if (r) { flash(roomName(r), L10.s[r] ?? ''); rooms[r].teacher?.greet(); } nearLoad(); }
  if ((nearT += dt) > 1) { nearT = 0; nearLoad(); }
  const target = (renderer.xr.isPresenting && eyesShut) ? 0 : (r ? rooms[r].meta.exposure : world.hall?.exposure) ?? 1;
  if (scene.fog) scene.fog.density = r ? 0 : .0028;
  renderer.toneMappingExposure += (target - renderer.toneMappingExposure) * dt * .7;   // the eye adapts slowly
  for (const n of world.rooms) if (rooms[n].sky) rooms[n].sky.visible = r === n && !rooms[n].meta.rainGlass;
  const fl = cur ? rooms[cur].meta.flames?.length : 0;
  shared.uFlick.value = fl ? 1 + .012 * Math.sin(shared.uTime.value * 9.7) + .01 * Math.sin(shared.uTime.value * 23.1) : 1;

  if (audio.ctx) {
    for (const n of Object.keys(audio.rooms)) {
      const m = rooms[n].meta, d = Math.hypot(m.door[0] - state.x, m.door[1] - state.y);
      const q_ = Math.min(1, d / 27); audio.roomOpen(n, r === n ? 1 : (.55 + 3.4 * q_) * (1 - q_ ** 3));
    }
    { let dn = 99; for (const n of Object.keys(audio.rooms)) { const m = rooms[n].meta; dn = Math.min(dn, Math.hypot(m.door[0] - state.x, m.door[1] - state.y)); } audio.setHallWet(r ? 0 : 1); audio.outdoors = !r; audio.setOutdoor(r ? .12 : .35 + .65 * Math.min(1, dn / 30)); }
    const cam = renderer.xr.isPresenting ? renderer.xr.getCamera() : camera;
    cam.getWorldPosition(tmp); const p = tmp.clone(), f = new THREE.Vector3(0, 0, -1).applyQuaternion(cam.getWorldQuaternion(new THREE.Quaternion())), u = new THREE.Vector3(0, 1, 0).applyQuaternion(cam.getWorldQuaternion(new THREE.Quaternion()));
    audio.listener(p, f, u);
  }
  if (world.plants) world.plants.visible = !r || !MOBILE; if (world.fieldGroup) for (const g of world.fieldGroup) g.visible = !r;
  for (const n of world.rooms) { const R = rooms[n]; if (R.teacher && R.group?.visible) { R.teacher.viewer = rig.position; } if (R.teacher && R.group?.visible) R.teacher.update(dt, audio.ctx?.currentTime ?? 0); }
  for (const n of world.rooms) for (const g of Object.values(rooms[n].gongs || {})) {
    g.v += (-g.w * g.w * g.a - .25 * g.v) * dt; g.a += g.v * dt; g.piv.rotation[g.axis] = g.a;
  }
  world.life?.(dt);
  if (composer && !renderer.xr.isPresenting) { gradePass.uniforms.uT.value = shared.uTime.value % 10; composer.render(dt); } else renderer.render(scene, camera);
}
applyLang();
window.__state = state; window.__heightAt = heightAt; window.__audio = audio; window.__rooms = rooms; window.__free = free; Object.defineProperty(window, "__world", { get: () => world }); window.__enter = enter; window.__renderer = renderer;
if (params.get('auto')) enter();
