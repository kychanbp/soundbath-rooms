"""Plan the valley: height field, paths, ground paint, tree and rock places. Writes data/land.npz and a map picture."""
import json, numpy as np, sys
from scipy import ndimage as ni
sys.path.insert(0, 'blender')
from PIL import Image
X0, Y0, X1, Y1 = -130, -100, 130, 160; S = 1.0
xs = np.arange(X0, X1 + S, S); ys = np.arange(Y0, Y1 + S, S); XX, YY = np.meshgrid(xs, ys)
r = np.random.default_rng(12)
def noise(s, seed):
    g = np.random.default_rng(seed).normal(0, 1, XX.shape); n = ni.gaussian_filter(g, s, mode='reflect'); return n / n.std()
# door point on the land, and which way the room body runs from it
SITES = dict(himalayan=((-30, -12), (-1, 0), 9.4, 11.9), crystal=((30, -12), (1, 0), 10.8, 11.8), gong=((-34, 26), (-1, 0), 10.2, 11.6), rain=((34, 26), (1, 0), 9.2, 10.6),
             rin=((-14, 58), (0, 1), 9.2, 10.4), strings=((16, 58), (0, 1), 7.2, 9.4), cave=((0, 92), (0, 1), 12.4, 15.4))
def spline(pts, n=40):
    P = np.array(pts, float); P = np.r_[[2 * P[0] - P[1]], P, [2 * P[-1] - P[-2]]]; o = []
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, n, endpoint=False):
            a, b, c, d = P[i - 1], P[i], P[i + 1], P[i + 2]
            o.append(.5 * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t ** 2 + (-a + 3 * b - 3 * c + d) * t ** 3))
    return np.array(o + [P[-2]])
trunk = spline([(0, -62), (4, -40), (-3, -22), (2, 2), (-4, 22), (3, 42), (-2, 62), (2, 78), (0, 91)])
B = [spline([(-2.4, -18), (-14, -13), (-29.5, -12)]), spline([(-1, -16), (14, -14), (29.5, -12)]), spline([(-1, 18), (-16, 24), (-33.5, 26)]), spline([(-1, 20), (16, 22), (33.5, 26)]),
     spline([(0, 42), (-10, 46), (-14, 57.5)]), spline([(2, 46), (12, 50), (16, 57.5)])]
paths = [trunk] + B
def dist_to(pts):
    m = np.ones(XX.shape, bool)
    i = np.clip(((pts[:, 0] - X0) / S).round().astype(int), 0, XX.shape[1] - 1); j = np.clip(((pts[:, 1] - Y0) / S).round().astype(int), 0, XX.shape[0] - 1); m[j, i] = False
    return ni.distance_transform_edt(m) * S
dp = np.min([dist_to(p) for p in paths], 0)
# ---- real land: Copernicus elevation around Jatiluwih, resampled to this grid. North is +Y.
D = np.load('data/bali/dem.npz'); DZ = D['Z']; ds = float(D['s'])
ci = DZ.shape[1] / 2; cj = DZ.shape[0] / 2     # row 0 is north
rows = cj - YY / ds; cols = ci + XX / ds
Zreal = ni.map_coordinates(DZ, [rows, cols], order=3, mode='nearest'); base = float(Zreal[np.argmin(np.abs(ys - 0)), np.argmin(np.abs(xs - 0))]); Zreal = (Zreal - base).astype('f8'); print('real relief in area', Zreal.min().round(1), Zreal.max().round(1))
# real ground cover from Sentinel-2: bright lime is rice, dark green is forest
T = np.load('data/bali/tci_S2A_2026.npy').astype('f4') / 255; hs = T.shape[1] / 2
tr, tc = hs - YY / 10, hs + XX / 10
TCI = np.dstack([ni.map_coordinates(T[i], [tr, tc], order=1) for i in range(3)])
green = ni.gaussian_filter((TCI[..., 1] - .5 * TCI[..., 0] - .5 * TCI[..., 2]) * 1.0 + TCI[..., 1] * .4, 2); green = (green - np.percentile(green, 15)) / (np.percentile(green, 92) - np.percentile(green, 15) + 1e-6)
satRice = np.clip(green * 1.4 - .1, 0, 1); print('rice share from satellite', round(float((satRice > .5).mean()), 2))
Z = 1.2 * noise(18, 1) + .5 * noise(7, 2) + .12 * noise(2.5, 3)
# the sound bath bench: a wide level shelf cut into the real slope, as farmers do. Real land starts at its edge.
d0 = np.min([dist_to(p) for p in paths], 0)
hutd = np.full(XX.shape, 1e3)
for n_, ((x_, y_), d_, w_, l_) in SITES.items():
    c_x, c_y = x_ + d_[0] * l_ / 2, y_ + d_[1] * l_ / 2; hw_, hl_ = (l_ / 2, w_ / 2) if d_[0] else (w_ / 2, l_ / 2)
    hutd = np.minimum(hutd, np.hypot(np.maximum(np.abs(XX - c_x) - hw_, 0), np.maximum(np.abs(YY - c_y) - hl_, 0)))
B = np.clip(1 - np.maximum(np.minimum(d0 - 2.6, hutd - 5), 0) / 7, 0, 1); B = B * B * (3 - 2 * B)
wig = 1.1 * noise(9, 22) + .22 * noise(3, 23)
Zter = np.round((Zreal + wig) / .9) * .9
Z = Z * B + Zter * (1 - B)
# northern hill above the cave
hill = np.exp(-(((XX) / 34) ** 2 + ((YY - 112) / 28) ** 2)) * 15
Z += hill
tw = 1 - B
pad = np.zeros(XX.shape)
for n, ((x, y), d, w, l) in SITES.items():
    cx, cy = x + d[0] * l / 2, y + d[1] * l / 2
    hw, hl = (l / 2 + 3, w / 2 + 3) if d[0] else (w / 2 + 3, l / 2 + 3)
    if n == 'cave': continue
    q = np.maximum(np.abs(XX - cx) - hw, 0), np.maximum(np.abs(YY - cy) - hl, 0)
    pad = np.maximum(pad, np.clip(1 - np.hypot(*q) / 7, 0, 1))
wpath = np.clip(1 - dp / 3.2, 0, 1)
k = 1 - (1 - pad) * (1 - .92 * wpath)
k = ni.gaussian_filter(k, 1.2); Z = Z * (1 - np.clip(k, 0, 1)) + np.clip(ni.gaussian_filter(Z, 8), -1.1, 1.1) * (np.clip(k, 0, 1) - pad.clip(0, 1) * np.clip(k, 0, 1))
for n, ((x, y), d, w, l) in SITES.items():
    if n == 'cave': continue
    cx, cy = x + d[0] * l / 2, y + d[1] * l / 2; hw, hl = (l / 2 + 1.6, w / 2 + 1.6) if d[0] else (w / 2 + 1.6, l / 2 + 1.6)
    f = np.clip(1 - np.hypot(np.maximum(np.abs(XX - cx) - hw, 0), np.maximum(np.abs(YY - cy) - hl, 0)) / 3.5, 0, 1); Z = Z * (1 - f)
# the cave: a floor notch runs into a steep rock face
(cx, cy) = SITES['cave'][0]
face = np.clip((YY - cy + 1.5) / 3.5, 0, 1) * np.exp(-((XX - cx) / 26) ** 2); Z = Z + face * 13 * (1 - np.exp(-((YY - cy) / 2 + .1).clip(0) * 0))
f = np.clip(1 - np.maximum(np.maximum(np.abs(XX - cx) - 10, 0), np.maximum(YY - cy + 1, 0) + np.maximum(cy - 14 - YY, 0)) / 4, 0, 1); Z = Z * (1 - f)
Z = np.where((YY >= cy - .5) & (YY <= cy + 1.5) & (np.abs(XX - cx) < 11), np.maximum(Z, 0) * 0, Z)
# lotus pond beside the trail
PD = (-15.0, 6.0, 8.5); pd = np.hypot(XX - PD[0], (YY - PD[1]) * 1.25) + 1.2 * noise(4, 31)
Z = np.where(pd < PD[2] + 3, Z * np.clip((pd - PD[2]) / 3, 0, 1) - .75 * np.clip(1 - pd / PD[2], 0, 1) ** .5 - .05, Z)
# ground paint: 0 grass, 1 forest floor, 2 path, 3 rock
gx, gy = np.gradient(Z, S); slope = np.hypot(gx, gy)
pn = noise(1.2, 8); forest = np.clip(.5 + .28 * noise(9, 5) + .12 * pn, 0, 1)
pth = np.clip(1 - (dp + .18 * pn) / 1.05, 0, 1) ** .6 * np.clip(1.4 - slope, 0, 1); rock = np.clip((slope - .75) / .35, 0, 1) * (1 - pth)
sp = np.dstack([1 - forest, forest, pth, rock]); sp[..., :2] *= (1 - pth - rock).clip(0)[..., None]
# plants stay off paths, huts, pond, terraces edges
rice = np.clip(tw * 1.6 - .3, 0, 1) * (slope < .7) * np.clip(satRice * 1.6, 0, 1)
bund = np.clip((slope - .28) / .25, 0, 1) * tw
pond = pd < PD[2] + .4
ok = np.ones(XX.shape, bool); ok[dp < 3.2] = False; ok[hutd < 1.5] = False; ok[pad > .3] = False; ok[pond] = False; ok[(YY > 84) & (np.abs(XX) < 15) & (YY < 104)] = False; ok[(np.abs(XX) > 125) | (YY < -96) | (YY > 156)] = False
hill = ok & (tw < .15)
edge = ok & (slope < 1.2) & ((rice < .4) | (bund > .3))
P = {}
def add(name, x, y, s_):
    i, j = int(x - X0), int(y - Y0); P.setdefault(name, []).append([round(x, 2), round(y, 2), round(float(Z[j, i]), 2), round(float(s_), 2), round(float(r.uniform(0, 6.28)), 2)])
def scatter(n, mask, gap, pick, weight=None):
    pts = []
    for _ in range(n):
        x, y = r.uniform(X0 + 3, X1 - 3), r.uniform(Y0 + 3, Y1 - 3); i, j = int(x - X0), int(y - Y0)
        if not mask[j, i] or (weight is not None and r.random() > weight[j, i]): continue
        if gap and pts and np.min(np.hypot(np.array(pts)[:, 0] - x, np.array(pts)[:, 1] - y)) < gap: continue
        pts.append((x, y)); pick(x, y)
near = np.clip(1 - dp / 22, 0, 1)
scatter(60000, edge, 6.5, lambda x, y: add('palm' + str(r.integers(3)), x, y, r.uniform(.9, 1.35)), np.clip(near * .7 + .16 * (noise(10, 41) > .4) + .05, 0, 1))
scatter(30000, ok & (dp > 7) & (slope < 1.0) & (satRice < .45), 5.0, lambda x, y: add(['jtree0', 'jtree0', 'itree0', 'jsmall0', 'pachira0'][r.integers(5)], x, y, r.uniform(2.3, 3.6)), np.clip(1 - satRice * 1.5, 0, 1))
scatter(16000, hill & (dp > 3.2), 3.0, lambda x, y: add('banana' + str(r.integers(2)), x, y, r.uniform(.8, 1.3)), near)
scatter(16000, hill, 1.4, lambda x, y: add(['fern0', 'fern1', 'cal0', 'cal1', 'anth0', 'anth1'][r.integers(6)], x, y, r.uniform(1.2, 2.3)), near * .9 + .1 * forest)
scatter(9000, hill, 0, lambda x, y: add(['shrubA0', 'shrubB0', 'shrubB1', 'shrubA1'][r.integers(4)], x, y, r.uniform(3.2, 5.5)), forest * .6)
scatter(26000, hill & (slope < .7), 0, lambda x, y: add('grass' + str(r.integers(2)), x, y, r.uniform(.8, 1.5)), near * .7)
scatter(120000, (rice > .45) & (dp > 1.5), 0, lambda x, y: add('rice', x, y, r.uniform(.8, 1.1)), np.clip(1.1 - dp / 50, .1, 1))
rocks = []
scatter(1800, hill, 3, lambda x, y: rocks.append([round(x, 2), round(y, 2), round(float(Z[int(y - Y0), int(x - X0)]), 2), round(float(r.uniform(.4, 1.4)), 2), round(float(r.uniform(0, 6.28)), 2)]), near)
place = dict(cards={k: v for k, v in P.items() if not k.startswith(('palm', 'banana', 'rice'))}, meshes={k: v for k, v in P.items() if k.startswith(('palm', 'banana'))}, rice=P.get('rice', []), rock=rocks)
pond_ = dict(x=PD[0], y=PD[1], r=PD[2])
np.savez('data/land.npz', Z=Z.astype('f4'), xs=xs, ys=ys, dp=dp.astype('f4'), slope=np.where(B < .25, 9., slope).astype('f4'))
Image.fromarray((np.clip(sp[..., 1:], 0, 1) * 255).astype('u1')[::-1], 'RGB').resize((1024, 1024), Image.BICUBIC).save('data/land_splat.png')
# terrace pattern at fine scale: thin grass bunds along real contours, and each paddy with its own stage of growth
N_ = 2048; zf = N_ / Z.shape[1], N_ / Z.shape[0]
Zt = ni.zoom((Zreal + wig).astype('f4'), (N_ / Z.shape[0], N_ / Z.shape[1]), order=1); ric = ni.zoom(rice.astype('f4'), (N_ / Z.shape[0], N_ / Z.shape[1]), order=1)
gy_, gx_ = np.gradient(Zt, (Y1 - Y0) / N_, (X1 - X0) / N_); gm = np.hypot(gx_, gy_) + .004
h_ = .9; fr = Zt / h_ + .5; dist = np.abs(fr - np.round(fr)) * h_ / gm
line = np.clip(1 - dist / .34, 0, 1)
band = np.floor(fr); cell = np.floor(np.arctan2(gy_, gx_) * 0 + (np.cumsum(np.ones_like(Zt), 1) * (X1 - X0) / N_) / 26)
hash_ = (np.sin(band * 12.9898 + cell * 78.233) * 43758.5453) % 1
Image.fromarray((np.dstack([np.clip(ric, 0, 1), line, hash_]) * 255).astype('u1')[::-1], 'RGB').save('data/land_splat2.png')
json.dump(dict(pond=pond_, place=place, sites={k: dict(door=v[0], dir=v[1], w=v[2], l=v[3]) for k, v in SITES.items()}, bounds=[X0, Y0, X1, Y1], step=S, paths=[np.round(p[::6], 2).tolist() for p in paths]), open('data/land.json', 'w'))
print({k: len(v) for k, v in P.items()}, 'rocks', len(rocks), 'Z', Z.min().round(1), Z.max().round(1))
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
ls = matplotlib.colors.LightSource(315, 40).hillshade(Z, dx=1, dy=1)
fig, ax = plt.subplots(figsize=(8, 8)); ax.imshow(ls * .5 + .5 * sp[..., 2] + .3 * rice, cmap='gray', origin='lower', extent=(X0, X1, Y0, Y1))
for k, c in (('palm0', 'lime'), ('jtree0', 'g'), ('banana0', 'y')):
    q = np.array(P[k]); ax.plot(q[:, 0], q[:, 1], '.', ms=3, color=c)
for k, v in SITES.items():
    x, y = v[0]; ax.plot([x, x + v[1][0] * v[3]], [y, y + v[1][1] * v[3]], 'r', lw=4); ax.text(x, y, k, color='y')
plt.tight_layout(); plt.savefig('renders/landmap.png', dpi=70)
