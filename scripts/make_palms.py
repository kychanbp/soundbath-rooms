"""Build coconut palm and banana meshes and leaf textures. No CC0 library has them, so they are made here."""
import json, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
r = np.random.default_rng(3); O = 'web/assets/land'
def frond():
    W, H = 2048, 512; S = 2; im = Image.new('RGBA', (W * S, H * S), (58, 84, 30, 0)); d = ImageDraw.Draw(im); cy = H * S / 2
    for i in range(170):
        t = i / 169; x = (40 + t * (W - 80)) * S
        L = (H * .47 * S) * math.sin(min(1, t * 1.15 + .06) * math.pi) ** .55 * r.uniform(.9, 1.05)
        for s in (-1, 1):
            a = math.radians(r.uniform(50, 64) * (1 - .55 * t)); dx = math.cos(a) * L; dy = math.sin(a) * L * s
            g = r.uniform(.8, 1.15); base = (int(66 * g), int(104 * g), int(30 * g), 255); tip = (int(120 * g), int(132 * g), int(46 * g), 255)
            w = r.uniform(7, 11) * S * (1 - .5 * t); n = 10
            for k in range(n):
                u0, u1 = k / n, (k + 1) / n; ww = w * (1 - u0) ** .5
                c = tuple(int(base[j] * (1 - u0) + tip[j] * u0) for j in range(4))
                d.line([(x + dx * u0 * (1 + .1 * u0), cy + dy * u0), (x + dx * u1 * (1 + .1 * u1), cy + dy * u1)], fill=c, width=max(2, int(ww)))
    d.line([(30 * S, cy), ((W - 30) * S, cy)], fill=(148, 138, 72, 255), width=7 * S)
    im = im.resize((W, H), Image.LANCZOS); bleed = Image.new('RGBA', im.size, (70, 100, 34, 0)); bleed.alpha_composite(im); return bleed
def banana():
    W, H = 1024, 512; im = Image.new('RGBA', (W, H), (60, 110, 40, 0)); a = np.zeros((H, W)); y, x = np.mgrid[0:H, 0:W]; u = x / W; v = (y - H / 2) / (H / 2)
    edge = np.sin(np.clip(u * 1.02, 0, 1) * math.pi) ** .55 * .94
    tears = np.zeros(W); 
    mask = np.abs(v) < edge
    for i in range(46):
        px = int(r.uniform(.06, .98) * W); w = int(r.uniform(1, 3)); depth = r.uniform(.3, .95); s = r.choice([-1, 1])
        mask[(x >= px) & (x < px + w) & (v * s > edge * (1 - depth))] = False
    ve = .5 + .5 * np.sin(u * 150 + v * 1.5); sh = .72 + .28 * np.exp(-(np.abs(v) / np.maximum(edge, .05)) ** 2 * 1.2); base = np.dstack([.08 + .05 * ve, .19 + .09 * ve + .05 * u, .05 + .02 * ve]) * sh[..., None]
    rib = np.exp(-(v / .025) ** 2)[..., None]; base = base * (1 - rib) + np.array([.30, .38, .12]) * rib
    arr = (np.dstack([np.clip(base, 0, 1) ** (1 / 2.2), mask.astype(float)]) * 255).astype('u1'); return Image.fromarray(arr, 'RGBA')
def bark():
    W, H = 256, 1024; a = np.zeros((H, W, 3)); y = np.arange(H)[:, None]; n = r.normal(0, 1, (H, W))
    ring = .5 + .5 * np.sin(y * .22 + 2 * np.sin(y * .03)); from scipy import ndimage as ni
    n = ni.gaussian_filter(n, (1, 6)); n /= n.std()
    v = .28 + .1 * ring + .04 * n; return Image.fromarray((np.clip(np.dstack([v * 1.05, v * .92, v * .75]), 0, 1) ** (1 / 2.2) * 255).astype('u1'), 'RGB')
frond().save(f'{O}/frond.webp', quality=86, method=5, exact=True); banana().save(f'{O}/bananaleaf.webp', quality=86, method=5, exact=True); bark().save(f'{O}/palmbark.webp', quality=80)
frond().save('data/imp/frond.png'); banana().save('data/imp/bananaleaf.png'); bark().save('data/imp/palmbark.png')
def strip(V, UV, I, path, side, u0=0, u1=1):
    b = len(V); n = len(path)
    for k, (p, s) in enumerate(zip(path, side)):
        t = k / (n - 1); u = u0 + (u1 - u0) * t
        V += [(p + s).tolist(), (p).tolist(), (p - s).tolist()]; UV += [(u, 0), (u, .5), (u, 1)]
    for k in range(n - 1):
        a = b + k * 3; c = a + 3
        I += [a, a + 1, c, a + 1, c + 1, c, a + 1, a + 2, c + 1, a + 2, c + 2, c + 1]
def palm(seed, H):
    q = np.random.default_rng(seed); T, TU, TI = [], [], []; n = 7; k = 12; lean = q.uniform(.5, 1.6); dir_ = q.uniform(0, 6.28)
    pts = []
    for i in range(k):
        t = i / (k - 1); off = lean * t ** 1.8; p = np.array([math.cos(dir_) * off, t * H, math.sin(dir_) * off]); rr = .115 + .07 * (1 - t) ** 3 + .05 * math.exp(-t * 18); pts.append(p)
        for j in range(n + 1):
            a = j / n * 6.283; T.append((p + np.array([math.cos(a) * rr, 0, math.sin(a) * rr])).tolist()); TU.append((j / n * 1, t * H / 4.5))
    for i in range(k - 1):
        for j in range(n):
            a = i * (n + 1) + j; b = a + n + 1; TI += [a, a + 1, b, a + 1, b + 1, b]
    F, FU, FI = [], [], []; top = pts[-1]
    for f in range(22):
        az = f * 2.4 + q.uniform(-.2, .2); up = q.uniform(.25, 1.15) if f < 15 else q.uniform(-.5, .1); L = q.uniform(3.6, 4.8) * (1 - .1 * (up < 0)); w = q.uniform(.85, 1.1); dirx = np.array([math.cos(az), 0, math.sin(az)]); side = np.array([-math.sin(az), 0, math.cos(az)])
        path = []; sides = []
        for m in range(9):
            t = m / 8; a = up - 1.9 * t ** 1.4; p = top + dirx * L * t * math.cos(a * .55) + np.array([0, L * (math.sin(up) * t - .5 * t * t * (1.0 + .5 * (1 - up))), 0]); path.append(p)
            s = side * w * .5 * (1 - t ** 3 * .75) + np.array([0, -.16 * w * (1 - t), 0]); sides.append(s)
        strip(F, FU, FI, np.array(path), np.array(sides))
    return dict(t=dict(pos=np.array(T).round(3).ravel().tolist(), uv=np.array(TU).round(3).ravel().tolist(), idx=TI), f=dict(pos=np.array(F).round(3).ravel().tolist(), uv=np.array(FU).round(3).ravel().tolist(), idx=FI))
def banana_plant(seed):
    q = np.random.default_rng(seed); F, FU, FI = [], [], []; h = q.uniform(1.6, 2.4)
    T, TU, TI = [], [], []; n = 7
    for i in range(5):
        t = i / 4
        for j in range(n + 1): a = j / n * 6.283; rr = .15 - .08 * t; T.append((math.cos(a) * rr, t * h, math.sin(a) * rr)); TU.append((j / n, t * 2))
    for i in range(4):
        for j in range(n): a = i * (n + 1) + j; b = a + n + 1; TI += [a, a + 1, b, a + 1, b + 1, b]
    for f in range(9):
        az = f * 2.2; up = q.uniform(.5, 1.25); L = q.uniform(1.8, 2.9); w = q.uniform(.5, .72); d = np.array([math.cos(az), 0, math.sin(az)]); sd = np.array([-math.sin(az), 0, math.cos(az)]); P = np.array([0, h * .96, 0]); path = []; sides = []
        for m in range(7):
            t = m / 6; path.append(P + d * L * t * .85 + np.array([0, L * (math.sin(up) * t * .85 - .55 * t * t), 0])); sides.append(sd * w * .5 + np.array([0, -.08 * (1 - t), 0]))
        strip(F, FU, FI, np.array(path), np.array(sides))
    return dict(t=dict(pos=np.array(T).round(3).ravel().tolist(), uv=np.array(TU).round(3).ravel().tolist(), idx=TI), f=dict(pos=np.array(F).round(3).ravel().tolist(), uv=np.array(FU).round(3).ravel().tolist(), idx=FI))
def rice():
    W, H = 512, 512; S = 2; im = Image.new('RGBA', (W * S, H * S), (120, 170, 40, 0)); d = ImageDraw.Draw(im)
    for i in range(70):
        x0 = r.uniform(.2, .8) * W * S; lean = r.uniform(-.34, .34) * W * S; h = r.uniform(.6, 1) * H * S; g = r.uniform(.78, 1.12); c = (int(112 * g), int(168 * g), int(38 * g), 255); w = int(r.uniform(5, 10))
        pts = [(x0 + lean * t * t, H * S - h * t) for t in np.linspace(0, 1, 14)]; d.line(pts, fill=c, width=w, joint='curve')
    return im.resize((W, H), Image.LANCZOS)
c_ = rice(); c_.save(f'{O}/ricecard.webp', quality=84, method=5, exact=True)
json.dump(dict(palm0=palm(1, 9.5), palm1=palm(2, 12), palm2=palm(3, 7.5), banana0=banana_plant(4), banana1=banana_plant(5)), open(f'{O}/palms.json', 'w'), separators=(',', ':'))
print('ok')
