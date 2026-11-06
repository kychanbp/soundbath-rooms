"""The valley: ground, huts seen from outside, signposts, rocks. Named 'hall' so the app treats it as the space between rooms."""
import json, numpy as np, math
from lib import *
import props as P
from room_base import *
from layout import PLACE

TITLE = 'Forest path'
LAND = json.load(open(f'{ROOT}/data/land.json')); D = np.load(f'{ROOT}/data/land.npz')


def box_hut(R, name, W, L, H, roof, walls, windows, rise=.86, far_open=False):
    """Outer skin of a room as a Balinese bale: volcanic stone base, steep thatch hip roof, dark timber posts."""
    g = R.g; e = .36; x = W / 2 + e; y1 = L + e; sb = min(.95, H)
    t = [o for o in windows if o[0] == 'e']; f = [o for o in windows if o[0] == 'f']
    def face(a, b, ops):
        low = [(c, w, sl, min(h, sb)) for c, w, sl, h in ops if sl < sb]
        R.wall('bstone', a, b, sb, low, thick=.04)
        R.wall(walls, a, b, H, [(c, w, max(sl, sb), h) for c, w, sl, h in ops if h > sb], thick=.04, base=sb)
    face((x, 0), (-x, 0), [(0, 1.56, 0, 2.3)])
    face((x, y1), (x, 0), [o[1:] for o in t])
    face((-x, 0), (-x, y1), [])
    if not far_open: face((-x, y1), (x, y1), [o[1:] for o in f])
    for o in t: g.quad('water', (x + .01, o[1] - o[2] / 2, o[3]), (x + .01, o[1] + o[2] / 2, o[3]), (x + .01, o[1] + o[2] / 2, o[4]), (x + .01, o[1] - o[2] / 2, o[4]))
    for o in f: g.quad('water', (o[1] + o[2] / 2, y1 + .01, o[3]), (o[1] - o[2] / 2, y1 + .01, o[3]), (o[1] - o[2] / 2, y1 + .01, o[4]), (o[1] + o[2] / 2, y1 + .01, o[4]))
    ov = 1.25; ex = x + ov; yA = -1.4; yB = y1 + (1.25 if not far_open else 1.6); ze = H - .2; rh = ex * rise; y0r, y1r = yA + ex * .92, yB - ex * .92
    if y1r < y0r: y0r = y1r = (yA + yB) / 2
    top = ze + rh
    A, B, C, D_ = (-ex, yA, ze), (ex, yA, ze), (ex, yB, ze), (-ex, yB, ze); E, F_ = (0, y0r, top), (0, y1r, top)
    g.quad(roof, A, B, F_ if False else E, E) if False else None
    g.poly(roof, [A, B, E]); g.poly(roof, [C, D_, F_]); g.quad(roof, B, C, F_, E); g.quad(roof, D_, A, E, F_)
    # alang-alang thatch: overlapping courses, each a thick rough lip, with a bound ridge
    rng_ = np.random.default_rng(int(W * 100))
    def course(P0, P1, Q0, Q1, n=11):
        for i in range(n):
            t0 = i / n; t1 = t0 + 1.25 / n
            a0 = np.array(P0) * (1 - t0) + np.array(Q0) * t0; b0 = np.array(P1) * (1 - t0) + np.array(Q1) * t0
            a1 = np.array(P0) * (1 - min(t1, 1)) + np.array(Q0) * min(t1, 1); b1 = np.array(P1) * (1 - min(t1, 1)) + np.array(Q1) * min(t1, 1)
            lift = np.array([0, 0, .13]); drop = np.array([0, 0, -.05 - rng_.uniform(0, .05)])
            g.quad(roof, tuple(a0 + lift + drop), tuple(b0 + lift + drop), tuple(b1 + lift), tuple(a1 + lift))
            g.quad(roof, tuple(a0 + drop), tuple(b0 + drop), tuple(b0 + lift + drop), tuple(a0 + lift + drop))
    course(A, B, E, E); course(B, C, E, F_); course(C, D_, F_, F_); course(D_, A, F_, E)
    if y1r > y0r:
        rp = np.array([(0, y, top + .1) for y in np.linspace(y0r - .25, y1r + .25, 14)]); g.tube(roof, rp, np.full(14, .24), n=8)
        for y in np.linspace(y0r, y1r, 6): g.cyl('leather', (0, y, top + .12), (0, y + .04, top + .12), .26, n=10)
    g.lathe('brass', (0, (y0r + y1r) / 2, top + .32), [(0, .55), (.04, .3), (.1, .12), (.16, 0), (0, -.02)][::-1], n=12) if False else None
    # bamboo eave pole and carved posts at the door
    for P0, P1 in ((A, B), (B, C), (C, D_), (D_, A)):
        g.cyl('bamboog', (P0[0], P0[1], P0[2] - .1), (P1[0], P1[1], P1[2] - .1), .05, n=8)
    for s_ in (-1, 1):
        px = s_ * 1.0; py = -.95; prof = []
        for z_, r_ in ((0, .13), (.3, .13), (.34, .17), (.42, .1), (1.6, .09), (1.66, .13), (1.72, .09), (ze + .45 * rise - .3, .08), (ze + .45 * rise, .15)):
            prof.append((r_, z_))
        g.lathe('redlac', (px, py, 0), prof[::-1], n=14)
    # carved door frame in red and gold, and side walls to the steps
    for s_ in (-1, 1):
        g.beam('redlac', (s_ * .86, -.03, 0), (s_ * .86, -.03, 2.42), .16, .1); g.beam('gold', (s_ * .86, -.09, .1), (s_ * .86, -.09, 2.3), .06, .02)
    g.beam('redlac', (-1.02, -.03, 2.42), (1.02, -.03, 2.42), .1, .22); g.beam('gold', (-.9, -.09, 2.42), (.9, -.09, 2.42), .02, .07)
    for k in range(5): g.cyl('gold', (-.8 + k * .4, -.1, 2.56), (-.8 + k * .4, -.1, 2.72 - abs(k - 2) * .05), .05, .01, n=6)
    for st, (yy, hh) in enumerate(((-1.25, .1), (-.85, .2))):
        g.beam('paras', (-1.05, yy, hh / 2), (1.05, yy, hh / 2), .42, hh)
    g.quad('bamboo', D_, C, B, A)                                                   # the ceiling of the deep eave
    for P0, P1 in ((A, B), (B, C), (C, D_), (D_, A)):                               # thick thatch edge
        g.quad(roof, (P0[0], P0[1], P0[2] - .22), (P1[0], P1[1], P1[2] - .22), P1, P0)
    g.beam('beam', E, F_, .2, .2) if y1r > y0r else None
    for px, py in ((-ex + .55, yA + .55), (ex - .55, yA + .55), (ex - .55, yB - .55), (-ex + .55, yB - .55)):
        g.beam('beam', (px, py, 0), (px, py, ze + .1), .2, .2); g.beam('bstone', (px, py, 0), (px, py, .32), .4, .4)
    g.beam('bstone', (-1.5, -.6, .06), (1.5, -.6, .06), .9, .12)


def shrine(g, x, y, z, s=1.0):
    """A small stone shrine: stacked plinth with a little thatch cap."""
    H = 0
    for w, h in ((1.0, .18), (.78, .16), (.56, .62), (.74, .12), (.62, .1)):
        g.beam('bstone', (x, y, z + H), (x, y, z + H + h * s), w * s, w * s); H += h * s
    g.beam('beam', (x, y, z + H), (x, y, z + H + .45 * s), .08 * s, .08 * s); H += .45 * s
    W = .9 * s; A, B, C, D_, E = (x - W, y - W, z + H), (x + W, y - W, z + H), (x + W, y + W, z + H), (x - W, y + W, z + H), (x, y, z + H + .85 * s)
    for a, b in ((A, B), (B, C), (C, D_), (D_, A)): g.poly('thatch', [a, b, E])
    g.quad('thatch', D_, C, B, A)


def candi(g, x, y, z):
    """Candi bentar: a split temple gate of red brick with grey carved paras bands. Each half is a mirror of the other."""
    for s_ in (-1, 1):
        H = 0; cx = x + s_ * 2.35
        tiers = ((3.3, .55, 'paras'), (2.9, 1.0, 'brick'), (3.2, .22, 'paras'), (2.5, .9, 'brick'), (2.85, .2, 'paras'), (2.1, .78, 'brick'), (2.4, .18, 'paras'), (1.7, .66, 'brick'), (1.95, .16, 'paras'), (1.25, .55, 'brick'), (1.45, .14, 'paras'), (.8, .42, 'brick'), (.5, .36, 'paras'))
        for w, h, m in tiers:
            # the inner face is cut straight, as if a tower had been split in two
            x0, x1 = (cx - w / 2, x + 1.15) if s_ < 0 else (x - 1.15 + 0 * w, cx + w / 2)
            x0, x1 = (min(x0, x1), max(x0, x1))
            if s_ < 0: x1 = min(x1, x - .95)
            else: x0 = max(x0, x + .95)
            g.beam(m, ((x0 + x1) / 2 - (x1 - x0) / 2, y, z + H + h / 2), ((x0 + x1) / 2 + (x1 - x0) / 2, y, z + H + h / 2), w * .86, h)
            if m == 'paras':                                                     # small carved finials on each corner
                for c_, (px, py) in enumerate(((x0, y - w * .43), (x0, y + w * .43), (x1, y - w * .43), (x1, y + w * .43))):
                    g.lathe('paras', (px, py, z + H + h), [(.09, 0), (.06, .1), (.09, .16), (.02, .3), (0, .36)][::-1], n=8)
            H += h
        # flanking walls
        g.beam('brick', (x + s_ * 4.1, y, z + .55), (x + s_ * 9, y, z + .55), .42, 1.1); g.beam('paras', (x + s_ * 4.1, y, z + 1.14), (x + s_ * 9, y, z + 1.14), .56, .12)
    for s_ in (-1, 1): g.beam('paras', (x + s_ * 1.5, y - 2.4, z + .35), (x + s_ * 1.5, y - 2.4, z + .35), .01, .01) if False else None


def penjor(g, x, y, z, a=0, H=7.5):
    """A tall curved bamboo pole with a hanging palm-leaf ornament, as Balinese families raise along paths."""
    k = 26; t = np.linspace(0, 1, k); c, s_ = math.cos(a), math.sin(a)
    p = np.stack([x + c * (t ** 2.4) * 2.4, y + s_ * (t ** 2.4) * 2.4, z + t * H * (1 - .13 * t ** 2)], -1)
    g.tube('bamboog', p, .045 * (1 - .75 * t) + .012, n=7, caps=False)
    q = p[-1]; d = np.array([0, 0, -1.])
    g.cyl('yellowc', tuple(q), tuple(q + d * 1.0), .05, .16, n=8, caps=False); g.cyl('yellowc', tuple(q + d * 1.0), tuple(q + d * 1.25), .16, .02, n=8, caps=False)
    for f in range(7):
        b = f / 7 * 6.28; o = np.array([math.cos(b) * .16, math.sin(b) * .16, 0]); g.cyl('yellowc', tuple(q + d * .95 + o), tuple(q + d * 2.1 + o * 2.2), .012, .004, n=4, caps=False)


def tedung(g, x, y, z, H=2.6):
    """A ceremonial umbrella."""
    g.cyl('bamboog', (x, y, z), (x, y, z + H), .025, n=7); r = .85
    g.lathe('yellowc', (x, y, z + H - .25), [(r, 0), (r * .86, .13), (r * .4, .3), (0, .4)], n=20)
    g.cyl('gold', (x, y, z + H - .25), (x, y, z + H - .4), r, r, n=20, caps=False)


def poleng(g, x, y, z, r=.95, h=1.25, n=24):
    """Black and white checked cloth wrapped around a sacred tree."""
    rows = 8; cols = 16
    for i in range(cols):
        for j in range(rows):
            a0, a1 = i / cols * 6.283, (i + 1) / cols * 6.283; z0, z1 = z + .5 + j / rows * h, z + .5 + (j + 1) / rows * h
            m = 'polw' if (i + j) % 2 else 'polb'
            g.quad(m, (x + r * math.cos(a0), y + r * math.sin(a0), z0), (x + r * math.cos(a1), y + r * math.sin(a1), z0), (x + r * math.cos(a1), y + r * math.sin(a1), z1), (x + r * math.cos(a0), y + r * math.sin(a0), z1))


def build(R):
    Z = D['Z']; xs = D['xs']; ys = D['ys']
    n, m = Z.shape
    V = np.stack([np.tile(xs, n), np.repeat(ys, m), Z.ravel()], -1)
    idx = np.arange(n * m).reshape(n, m); q = np.stack([idx[:-1, :-1], idx[:-1, 1:], idx[1:, 1:], idx[1:, :-1]], -1).reshape(-1, 4)
    R.g.add('ground', V, V[:, :2] / 4, Q=q)
    # huts: each stands around its own room
    T0 = R.T.copy()
    def inroom(name, fn):
        R.T = np.array(PLACE[name]); R.g.T = R.T; R.p.T = R.T; fn(); R.T = T0; R.g.T = T0; R.p.T = T0
    inroom('himalayan', lambda: box_hut(R, 'himalayan', 9.4, 11.6, 3.7, 'thatch', 'clay', [('f', -2.9, 1.7, .7, 2.9), ('f', 0, 1.7, .7, 2.9), ('f', 2.9, 1.7, .7, 2.9), ('e', 4.2, 1.3, .9, 2.8), ('e', 7.6, 1.3, .9, 2.8)]))
    inroom('gong', lambda: box_hut(R, 'gong', 10.2, 11.4, 4.4, 'thatch', 'black_wood', [('f', -3.3, 2.3, 3.72, 4.1), ('f', 0, 2.3, 3.72, 4.1), ('f', 3.3, 2.3, 3.72, 4.1)]))
    inroom('rin', lambda: box_hut(R, 'rin', 7.2, 8.2, 2.85, 'thatch', 'siding', [], far_open=True))
    inroom('strings', lambda: box_hut(R, 'strings', 7.2, 9.2, 3.6, 'thatch', 'cedar', [('f', 0, 1.8, .9, 2.1), ('e', 5.0, 2.8, .4, 2.2)]))
    # crystal: drum and dome from outside
    def crystal():
        cy = 6.4; rd = 5.42; a = np.linspace(0, 2 * np.pi, 72, endpoint=False) - np.pi / 2; t = np.linspace(0, 1, 14)
        pr = [(rd + .3, 0), (rd + .3, 2.95)] + [(1.55 + (rd + .32 - 1.55) * math.cos(u * math.pi / 2) ** .8, 2.95 + 3.3 * math.sin(u * math.pi / 2)) for u in t[1:]]
        Pw = np.zeros((72, len(pr), 3))
        for j, (r, z) in enumerate(pr): Pw[:, j, 0] = r * np.cos(a); Pw[:, j, 1] = cy + r * np.sin(a); Pw[:, j, 2] = z
        # leave a gap at the door (first columns)
        R.g.grid('clay', Pw[3:-2, :2], flip=False)
        # a round thatched roof over the dome, with a smoke-hole collar at the skylight
        ring = np.array([(rd + 1.3, 2.75), (1.9, 6.5), (1.5, 6.7)]); Pr = np.zeros((72, 3, 3)); ao = np.linspace(0, 2 * np.pi, 72, endpoint=False)
        for j, (r_, z_) in enumerate(ring): Pr[:, j, 0] = r_ * np.cos(ao); Pr[:, j, 1] = cy + r_ * np.sin(ao); Pr[:, j, 2] = z_
        R.g.grid('thatch', Pr, closed_u=True, along='v')
        for z0, sc in ((3.4, .84), (4.2, .62), (5.0, .42), (5.8, .22)):
            r0 = (rd + 1.3) * sc + 1.4 * (1 - sc); Pq = np.zeros((72, 2, 3))
            for j, (r_, z_) in enumerate(((r0 + .2, z0 - .22), (r0 - .05, z0 + .1))): Pq[:, j, 0] = r_ * np.cos(ao); Pq[:, j, 1] = cy + r_ * np.sin(ao); Pq[:, j, 2] = z_
            R.g.grid('thatch', Pq, closed_u=True, along='v')
        Pd = np.zeros((6, 5, 3)); ad = np.linspace(a[-3], a[3] + 2 * np.pi, 6)
        for j, (r, z) in enumerate(pr[1:6]): Pd[:, j, 0] = r * np.cos(ad); Pd[:, j, 1] = cy + r * np.sin(ad); Pd[:, j, 2] = z
        R.g.grid('clay', Pd)
        for s in (-1, 1):
            R.g.quad('clay', *([(s * .78, 1.0, 0), (s * .78, -.05, 0), (s * .78, -.05, 2.95), (s * .78, 1.0, 2.95)] if s > 0 else [(s * .78, -.05, 0), (s * .78, 1.0, 0), (s * .78, 1.0, 2.95), (s * .78, -.05, 2.95)]))
        R.g.beam('beam', (-1, -.05, 2.45), (1, -.05, 2.45), .3, .3); R.g.quad('clay', (-.8, -.05, 2.3), (.8, -.05, 2.3), (.8, -.05, 2.95), (-.8, -.05, 2.95))
    inroom('crystal', crystal)
    # rain: outer face of the low wall and the door wall
    def rain():
        W = 9.2; D_ = 9.4; y1 = 1 + D_
        R.wall('clay', (W / 2 + .13, 1), (-W / 2 - .13, 1), 3.1, [(0, 1.56, 0, 2.3)], thick=.04)
        R.wall('bstone', (-W / 2 - .13, y1 + .13), (W / 2 + .13, y1 + .13), .55, [])
        R.wall('bstone', (W / 2 + .13, y1 + .13), (W / 2 + .13, 1), .55, []); R.wall('bstone', (-W / 2 - .13, 1), (-W / 2 - .13, y1 + .13), .55, [])
        for y in (0,):
            for s in (-1, 1):
                R.g.quad('concrete_w', *([(s * .78, 1, 0), (s * .78, 0, 0), (s * .78, 0, 2.3), (s * .78, 1, 2.3)] if s > 0 else [(s * .78, 0, 0), (s * .78, 1, 0), (s * .78, 1, 2.3), (s * .78, 0, 2.3)]))
            R.g.quad('concrete_w', (-1, 0, 2.3), (1, 0, 2.3), (1, 0, 3.1), (-1, 0, 3.1)); R.g.quad('concrete_w', (.78, 1, 2.3), (.78, 0, 2.3), (-.78, 0, 2.3), (-.78, 1, 2.3), flip=True)
    inroom('rain', rain)
    R.windows.clear()
    # cave mouth: a rough rock face with the door in it, backed by the hill
    cx, cy = PLACE['cave'][0, 3], PLACE['cave'][1, 3]
    nx_, nz_ = 86, 46; X_ = np.linspace(-11, 11, nx_); Zf = np.linspace(0, 11.5, nz_); r_ = np.random.default_rng(5); W_ = np.zeros((nx_, nz_))
    for f_, a_ in ((.25, .55), (.6, .28), (1.4, .12), (3.1, .05)):
        for _ in range(6):
            d_ = r_.normal(0, 1, 2); W_ += a_ / 2 * np.sin(np.outer(X_, np.ones(nz_)) * d_[0] * f_ + np.outer(np.ones(nx_), Zf) * d_[1] * f_ + r_.uniform(0, 6))
    arc = (X_ / 11) ** 2 * 2.4
    Pts_ = np.zeros((nx_, nz_, 3)); Pts_[..., 0] = cx + X_[:, None]; Pts_[..., 2] = Zf[None]
    Pts_[..., 1] = cy + .2 + arc[:, None] + W_ * np.clip(np.hypot(X_[:, None] / 1.6, Zf[None] / 3.0) - 1, 0, 1) + Zf[None] * .34
    idx = np.arange(nx_ * nz_).reshape(nx_, nz_); q_ = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    mid = Pts_.reshape(-1, 3)[q_].mean(1); keep = ~((np.abs(mid[:, 0] - cx) < .95) & (mid[:, 2] < 2.42))
    R.p.add('rock', Pts_.reshape(-1, 3), np.c_[Pts_.reshape(-1, 3)[:, 0], Pts_.reshape(-1, 3)[:, 2]] / 5, Q=q_[keep])
    for x, y, z, rz, s in ((-2.7, -1.0, 0, 40, 1.3), (2.9, -.8, 0, 150, 1.5), (-6.5, -.3, 0, 200, 2.2), (6.8, .2, 0, 300, 2.4)):
        R.model('boulder_01', TRS(cx + x, cy + y, z, rz, s), 9000); R.obstacle(cx + x, cy + y, s * .6)
    for x in np.arange(-10.5, 10.6, 1.0):
        if abs(x) > .9: R.obstacle(cx + x, cy + .35 + (x / 11) ** 2 * 2.4, .5)
    for x, y in ((-5.5, -24), (5.5, -24), (-8, 14), (8, 14), (-11, 38), (11, 38), (-6, 76), (6, 76)):
        i = int(x - xs[0]); j = int(y - ys[0]); shrine(R.g, x, y, float(Z[j, i]) - .05, 1.0); R.obstacle(x, y, .85)
    i = int(0 - xs[0]); j = int(-46 - ys[0]); candi(R.g, 3.2, -46, float(Z[j, i]) - .1)
    for s_ in (-1, 1):
        for dx, w_ in ((2.35, 3.5),): R.g.beam('paras', (3.2 + s_ * dx - w_ / 2, -46, float(Z[j, i]) - .85), (3.2 + s_ * dx + w_ / 2, -46, float(Z[j, i]) - .85), 3.1, .75)
    for s_ in (-1, 1): R.obstacle(3.2 + s_ * 2.6, -46, 1.6); R.obstacle(3.2 + s_ * 6, -46, 1.1); R.obstacle(3.2 + s_ * 8, -46, 1.1)
    # small thatched shelters among the paddies, as in the photographs of Jatiluwih
    for x, y in ((-92, 40), (88, -30), (96, 64), (-78, -52), (-30, 126), (58, 132)):
        i = int(x - xs[0]); j = int(y - ys[0]); z = float(Z[j, i]); W = 1.5
        for sx in (-1, 1):
            for sy in (-1, 1): R.g.beam('beam', (x + sx * W, y + sy * W, z - .3), (x + sx * W, y + sy * W, z + 2.1), .12, .12)
        R.g.quad('plank', (x - W, y - W, z + .55), (x + W, y - W, z + .55), (x + W, y + W, z + .55), (x - W, y + W, z + .55))
        e = 2.5; A, B_, C_, D2, E_ = (x - e, y - e, z + 2.0), (x + e, y - e, z + 2.0), (x + e, y + e, z + 2.0), (x - e, y + e, z + 2.0), (x, y, z + 3.9)
        for a_, b_ in ((A, B_), (B_, C_), (C_, D2), (D2, A)): R.g.poly('thatch', [a_, b_, E_])
    zAt = lambda x, y: float(Z[int(y - ys[0]), int(x - xs[0])])
    for x, y, a in ((-3, -41, .5), (3, -41, 2.6), (-3.2, -28, .4), (3.2, -6, 2.8), (-5, 8, .3), (-4, 30, .6), (5, 34, 2.4), (-3, 66, .5), (4, 70, 2.7)):
        penjor(R.g, x, y, zAt(x, y) - .1, a); R.obstacle(x, y, .2)
    for x, y in ((-1.6, -44), (1.6, -44), (-1.6, 88), (1.6, 88)):
        tedung(R.g, x, y, zAt(x, y)); R.obstacle(x, y, .2)
    # the great banyans by the trail wear checked cloth, as sacred trees do in Bali
    for fn, pts in LAND['place']['cards'].items():
        if fn != 'jtree0': continue
        near = sorted(pts, key=lambda p: min(abs(p[0]) + abs(p[1] - y_) for y_ in (0, 40)))[:4]
        for p in near: poleng(R.g, p[0], p[1], p[2], r=.075 * p[3] * 5.0 * .36)
    # signposts at each fork
    for name, x, y, a in (('himalayan', -5.5, -19.5, 200), ('crystal', 5.5, -19.5, -20), ('gong', -6, 16.5, 200), ('rain', 6, 16.5, -20), ('rin', -8.5, 41, 200), ('strings', 8.5, 42, -20), ('cave', 4.5, 72, 90)):
        c = math.cos(math.radians(a)); s = math.sin(math.radians(a))
        i = int(x - xs[0]); j = int(y - ys[0]); z = float(Z[j, i])
        R.g.beam('beam', (x, y, z - .2), (x, y, z + 1.85), .1, .1)
        # the board hangs to one side of the post, and reads from both directions
        for side in (-1, 1):
            nx, ny = -s * side, c * side; bx, by = x + nx * .06, y + ny * .06; dx, dy = c * side, s * side; o = .64 * side
            cx_, cy_ = bx + c * o, by + s * o
            R.g.add(f'sign_{name}', [(cx_ - dx * .6, cy_ - dy * .6, z + 1.3), (cx_ + dx * .6, cy_ + dy * .6, z + 1.3), (cx_ + dx * .6, cy_ + dy * .6, z + 1.7), (cx_ - dx * .6, cy_ - dy * .6, z + 1.7)], [(0, 0), (1, 0), (1, 1), (0, 1)], Q=[[0, 1, 2, 3]])
        R.obstacle(x, y, .3)
    # rocks: a few placed, the rest appear from the placement file in the app
    R.huts = {k: dict(door=v['door'], dir=v['dir'], w=v['w'], l=v['l']) for k, v in LAND['sites'].items()}
    return dict(box=[-130, -100, 0, 130, 160, 60], walk=[], surface='rug', pano=(0, 2, 2.0), cams=[((0, -54, 1.65), (0, -40, 4)), ((-16, -9, 1.65), (-32, -12, 3)), ((-3, 80, 1.65), (0, 92, 3.5)), ((24, 4, 1.65), (60, 20, 3))],
                hdri='overcast_soil_puresky', far=True, haze=.95, rot=0, strength=1.0, exposure=1.2, window_dir=(.45, -.55, .7), rt=[.6, .5, .4, .3, .3, .2], sky_ev=-.7, shafts=0, meta=dict(land=True, amb=(.05, .06, .06)), lm_ground=4096)
