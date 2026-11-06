"""Instruments, mats and cushions as parametric meshes."""
import math
import numpy as np
from lib import norm as vnorm


def bowl(g, c, R, H, m='bronze_bowl', t=.0055, seed=0, n=72):
    """Hand-beaten bowl. Profile goes up the outside, over the rim, and down the inside.
    V texture coordinate follows the profile, so the texture can polish the rim."""
    rng = np.random.default_rng(seed)
    s = np.linspace(0, 1, 26)
    # outer: flat base blends into a curved wall that leans in at the top
    def outer(u):
        r = R * (.38 + .62 * np.sin(u * np.pi / 2) ** .62) * (1 - .05 * u ** 6)
        z = H * (u ** 1.55)
        return r, z
    ro, zo = outer(s)
    ri, zi = ro[::-1] - t * 1.1, zo[::-1] - t * .4
    ri = np.maximum(ri, 0); zi = np.maximum(zi, t * 1.4)
    rim = np.array([ro[-1] + t * .05, ro[-1] - t * .55, ri[0] - t * .05])
    rz = np.array([H + t * .45, H + t * .75, H + t * .4])
    r = np.r_[0, ro, rim, ri, 0]; z = np.r_[0, zo, rz, zi, zi[-1]]
    v = np.linspace(0, 1, len(r))
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    # low frequency hand-made shape error
    wob = sum(rng.normal(0, .0028) * np.cos(k * a + rng.uniform(0, 6)) for k in (2, 3, 5))
    P = np.zeros((n + 1, len(r), 3)); UV = np.zeros((n + 1, len(r), 2))
    for i in range(n + 1):
        A = a[i % n]; w = 1 + wob[i % n] * (z / H) ** .5
        P[i, :, 0] = c[0] + r * w * math.cos(A); P[i, :, 1] = c[1] + r * w * math.sin(A); P[i, :, 2] = c[2] + z
        UV[i, :, 0] = i / n * 2 * round(R * 12 + 1) / 2; UV[i, :, 1] = v
    idx = np.arange((n + 1) * len(r)).reshape(n + 1, len(r))
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    g.add(m, P.reshape(-1, 3), UV.reshape(-1, 2), Q=q)


def torus(g, m, c, R, r, n=44, k=14, squash=.8, seed=0):
    rng = np.random.default_rng(seed)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False); b = np.linspace(0, 2 * np.pi, k, endpoint=False)
    P = np.zeros((n, k, 3))
    lump = 1 + .05 * np.sin(a * 5 + rng.uniform(0, 6)) + .03 * np.sin(a * 11 + rng.uniform(0, 6))
    for i in range(n):
        rr = r * lump[i]
        P[i, :, 0] = c[0] + (R + rr * np.cos(b)) * math.cos(a[i])
        P[i, :, 1] = c[1] + (R + rr * np.cos(b)) * math.sin(a[i])
        P[i, :, 2] = c[2] + rr * squash * (1 + np.sin(b))
    g.grid(m, P, closed_u=True, closed_v=True)


def cushion(g, m, c, w, d, h, rz=0, seed=0, nx=26, ny=26, sag=.32, tufts=0):
    """Rounded box with a puffed top and bottom. Soft creases near the edges."""
    rng = np.random.default_rng(seed)
    u = np.linspace(-1, 1, nx); v = np.linspace(-1, 1, ny)
    U, V = np.meshgrid(u, v, indexing='ij')
    su = np.sign(U) * np.abs(U) ** .55; sv = np.sign(V) * np.abs(V) ** .55
    e = 1 - np.maximum(np.abs(U), np.abs(V)) ** 6
    bump = sum(rng.normal(0, .0035) * np.sin(U * rng.uniform(2, 7) + rng.uniform(0, 6)) * np.cos(V * rng.uniform(2, 7) + rng.uniform(0, 6)) for _ in range(7))
    def surf(top):
        Z = (h / 2) * (.42 + .58 * e ** .55) + (bump * h * 1.4 if top else 0)
        if tufts:
            for tx in np.linspace(-.6, .6, tufts):
                for ty in np.linspace(-.6, .6, tufts):
                    Z = Z - h * .22 * np.exp(-(((U - tx) / .12) ** 2 + ((V - ty) / .12) ** 2))
        X = su * w / 2 * (1 - .04 * (1 - e)); Y = sv * d / 2 * (1 - .04 * (1 - e))
        return np.stack([X, Y, (Z + h / 2) if top else (-Z + h / 2)], -1)
    T = surf(True); B = surf(False)[::-1]
    co, si = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    def place(P):
        Q = P.copy(); Q[..., 0] = c[0] + P[..., 0] * co - P[..., 1] * si; Q[..., 1] = c[1] + P[..., 0] * si + P[..., 1] * co; Q[..., 2] = P[..., 2] + c[2]
        return Q
    g.grid(m, place(T)); g.grid(m, place(B))
    # side skirt to close the shape
    edge = np.r_[T[:, 0], T[-1, 1:], T[-2::-1, -1], T[0, -2::-1]]
    ee = edge.copy(); ee[:, 2] = c[2] * 0 + h / 2 - (edge[:, 2] - h / 2)
    Pp = np.stack([ee, edge], 1)
    g.grid(m, place(Pp), closed_u=True)


def bolster(g, m, c, L, r, rz=0, seed=0, n=28, k=24):
    rng = np.random.default_rng(seed)
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    s = np.linspace(-1, 1, k)
    prof = (1 - np.abs(s) ** 8) ** .5
    P = np.zeros((n, k, 3)); co, si = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    for i in range(k):
        rr = r * prof[i] * (1 + .018 * np.sin(s[i] * 6 + seed))
        x = s[i] * L / 2 * .98
        y = rr * np.cos(a); z = rr * np.sin(a) * .93 + r * .93
        P[:, i, 0] = c[0] + x * co - y * si; P[:, i, 1] = c[1] + x * si + y * co; P[:, i, 2] = c[2] + z
    g.grid(m, P, closed_u=True)


def blanket(g, m, c, w, d, rz=0, seed=0, layers=3, h=.022):
    """Folded blanket. Layers with a little slip between them."""
    rng = np.random.default_rng(seed)
    for i in range(layers):
        o = rng.normal(0, .006, 2)
        cushion(g, m, (c[0] + o[0], c[1] + o[1], c[2] + i * h * 1.15), w, d, h * 1.2, rz + rng.normal(0, .5), seed + i, nx=14, ny=14)


def mallet(g, c, ang, L=.26, head=.03, m_h='plank', m_w='leather', tilt=4):
    a = math.radians(ang); d = np.array([math.cos(a), math.sin(a), math.sin(math.radians(tilt))])
    p0 = np.array(c, float); p1 = p0 + d * L
    g.cyl(m_h, p0, p1, .0105, .013, n=10)
    prof = [(0, -head), (head * .62, -head * .8), (head * .96, -head * .3), (head, 0), (head * .96, head * .3), (head * .62, head * .8), (0, head)]
    q = p1 + d * head * .3
    pts = np.array([q + d * z for _, z in prof]); rs = np.array([max(r, .0005) for r, _ in prof])
    g.tube(m_w, pts, rs, n=14, caps=False)


def rug(g, m, c, w, d, rz=0, seed=0, fringe=True):
    rng = np.random.default_rng(seed)
    nx, ny = 40, 30
    U, V = np.meshgrid(np.linspace(-w / 2, w / 2, nx), np.linspace(-d / 2, d / 2, ny), indexing='ij')
    Z = .010 + sum(rng.normal(0, .0016) * np.sin(U * rng.uniform(1, 4) + rng.uniform(0, 6)) * np.cos(V * rng.uniform(1, 4)) for _ in range(5))
    Z[0] = Z[-1] = 0; Z[:, 0] = Z[:, -1] = 0
    co, si = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    P = np.stack([c[0] + U * co - V * si, c[1] + U * si + V * co, c[2] + Z], -1)
    g.grid(m, P)
    if fringe:
        for s in (-1, 1):
            for y in np.linspace(-d / 2, d / 2, int(d / .018)):
                x = s * (w / 2 + rng.uniform(.055, .085)); yy = y + rng.normal(0, .004)
                a = (c[0] + s * w / 2 * co - y * si, c[1] + s * w / 2 * si + y * co, c[2] + .002)
                b = (c[0] + x * co - yy * si, c[1] + x * si + yy * co, c[2] + .002)
                g.cyl('linen', a, b, .0028, .0015, n=3, caps=False)


def candle(g, c, r=.035, h=.14, m='wax', seed=0):
    g.cyl(m, c, (c[0], c[1], c[2] + h), r, n=18)


def gong(g, c, R, normal_y=True, tex='gong_a', lip=.05, t=.004, face=-1, n=96, rim=True, boss=0):
    """Flat disc with a turned-back lip. Lies in the XZ plane, faces -Y when face is -1."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    s = np.r_[np.linspace(0, .93, 20), np.linspace(.94, 1, 6)]
    rr = s * R
    dep = np.where(s < .93, .0, 0) + (np.clip((s - .93) / .07, 0, 1) ** 2) * lip + boss * np.exp(-(s / .12) ** 2) * -1
    nr = len(s)
    P = np.zeros((n, nr, 3)); UV = np.zeros((n, nr, 2))
    for j in range(nr):
        P[:, j, 0] = c[0] + rr[j] * np.cos(a); P[:, j, 2] = c[2] + rr[j] * np.sin(a); P[:, j, 1] = c[1] + (-face) * dep[j]
        UV[:, j, 0] = .5 + .5 * s[j] * np.cos(a); UV[:, j, 1] = .5 + .5 * s[j] * np.sin(a)
    P = np.concatenate([P, P[:1]], 0); UV = np.concatenate([UV, UV[:1]], 0)
    idx = np.arange((n + 1) * nr).reshape(n + 1, nr)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    if face > 0: q = q[:, ::-1]
    g.add(tex, P.reshape(-1, 3), UV.reshape(-1, 2), Q=q)
    # the back
    Pb = P.copy(); Pb[..., 1] = Pb[..., 1] + (-face) * t * 0 + (-face) * .001
    q2 = q[:, ::-1] + 0
    g.add(tex, Pb.reshape(-1, 3), UV.reshape(-1, 2), Q=q2)


def gong_stand(g, c, R, m='beam', rz=0, cord='leather', lift=0):
    """Timber frame: two posts, top rail, feet. The gong hangs on two cords. c is the floor centre."""
    w = R + .22; H = 2 * R + .55 + lift; T = .10
    x0, x1 = c[0] - w, c[0] + w
    y = c[1]
    for x in (x0, x1):
        g.beam(m, (x, y, c[2]), (x, y, c[2] + H), T, T, up=(0, 1, 0))
        g.beam(m, (x, y - .48, c[2] + .05), (x, y + .48, c[2] + .05), T * 1.1, T)
        g.beam(m, (x, y - .34, c[2] + .05), (x, y, c[2] + .55), T * .6, T * .6)
        g.beam(m, (x, y + .34, c[2] + .05), (x, y, c[2] + .55), T * .6, T * .6)
    g.beam(m, (x0 - .12, y, c[2] + H + T / 2), (x1 + .12, y, c[2] + H + T / 2), T * 1.05, T * 1.15)
    g.beam(m, (x0, y, c[2] + H - .28), (x1, y, c[2] + H - .28), T * .7, T * .55)
    cz = c[2] + H - .28 - .22 - R
    for s in (-1, 1):
        g.cyl(cord, (c[0] + s * R * .34, y, c[2] + H - .24), (c[0] + s * R * .2, y, cz + R * .94), .008, n=6, caps=False)
    return cz


def crystal(g, c, R, H, m='quartz', t=.006, n=64):
    """Frosted quartz bowl: near straight wall, thin rounded rim, seated on a rubber ring."""
    s = np.linspace(0, 1, 14)
    ro = R * (.62 + .38 * np.sin(s * np.pi / 2) ** .5); zo = H * s ** 1.15
    ri = ro[::-1] - t; zi = np.maximum(zo[::-1], t)
    rim = np.array([ro[-1], ro[-1] - t * .5, ri[0]]); rz = np.array([H + t * .3, H + t * .6, H + t * .3])
    r = np.r_[0, ro, rim, ri, 0]; z = np.r_[0, zo, rz, zi, t]
    P = np.zeros((n + 1, len(r), 3)); UV = np.zeros((n + 1, len(r), 2)); a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    v = np.linspace(0, 1, len(r))
    for i in range(n + 1):
        A = a[i % n]; P[i, :, 0] = c[0] + r * math.cos(A); P[i, :, 1] = c[1] + r * math.sin(A); P[i, :, 2] = c[2] + z; UV[i, :, 0] = i / n * 4; UV[i, :, 1] = v
    idx = np.arange((n + 1) * len(r)).reshape(n + 1, len(r))
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    g.add(m, P.reshape(-1, 3), UV.reshape(-1, 2), Q=q)


def koshi(g, c, H=2.1, tube='bamboo'):
    """Hand chime on a cord from a low timber arm. Bamboo body, small clapper, a sail."""
    x, y, z = c
    g.cyl('leather', (x, y, H), (x, y, H - .28), .002, n=5, caps=False)
    prof = [(.0, 0), (.042, 0), (.043, -.002), (.043, -.15), (.042, -.152), (.0, -.152)]
    g.lathe(tube, (x, y, H - .28), [(r, d) for r, d in prof[::-1]], n=20)
    g.cyl('leather', (x, y, H - .43), (x, y, H - .6), .0015, n=4, caps=False)
    g.lathe('leather', (x, y, H - .6), [(0, -.03), (.022, -.028), (.03, 0), (.022, .028), (0, .03)], n=10)


def ocean_drum(g, c, R=.23, tilt=8):
    g.lathe('beam', c, [(R, .0), (R + .008, .0), (R + .008, .055), (R, .055)], n=56)
    prof = [(0, .056), (R, .056)]
    g.lathe('skin', c, prof[::-1], n=56)


def rainstick(g, a, b, r=.028):
    g.cyl('bamboo', a, b, r, r * .9, n=14)


def frame_drum(g, c, R=.28, depth=.07, m_skin='skin', face=-1):
    """Disc in the XZ plane. c is its centre."""
    a = np.linspace(0, 2 * np.pi, 56, endpoint=False)
    P = np.zeros((56, 2, 3))
    for j, d in enumerate((-depth / 2, depth / 2)):
        P[:, j, 0] = c[0] + R * np.cos(a); P[:, j, 2] = c[2] + R * np.sin(a); P[:, j, 1] = c[1] + d
    g.grid('plank', P, closed_u=True)
    k = 10; s = np.linspace(0, 1, k)[::-1]
    P = np.zeros((56, k, 3)); UV = np.zeros((56, k, 2))
    for j in range(k):
        P[:, j, 0] = c[0] + R * s[j] * np.cos(a); P[:, j, 2] = c[2] + R * s[j] * np.sin(a); P[:, j, 1] = c[1] + face * (depth / 2 - .001)
        UV[:, j, 0] = .5 + .5 * s[j] * np.cos(a); UV[:, j, 1] = .5 + .5 * s[j] * np.sin(a)
    P = np.concatenate([P, P[:1]]); UV = np.concatenate([UV, UV[:1]])
    idx = np.arange(57 * k).reshape(57, k)
    q = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)
    if face > 0: q = q[:, ::-1]
    g.add(m_skin, P.reshape(-1, 3), UV.reshape(-1, 2), Q=q)
    # rawhide cords across the back
    for t in np.arange(0, np.pi, np.pi / 6):
        g.cyl('leather', (c[0] + R * .96 * math.cos(t), c[1] - face * (depth / 2 + .002), c[2] + R * .96 * math.sin(t)), (c[0] - R * .96 * math.cos(t), c[1] - face * (depth / 2 + .002), c[2] - R * .96 * math.sin(t)), .0025, n=5, caps=False)


def monochord(g, c, L=2.2, W=.72, H=.38, rz=0, n=30):
    x, y, z = c; 
    co, si = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    def p(a, b, h): return (x + a * co - b * si, y + a * si + b * co, z + h)
    # box
    for a0, a1, b0, b1 in (( -L/2, L/2, -W/2, W/2),):
        g.beam('cedar', p(-L/2, 0, H), p(L/2, 0, H), W, .022)
        g.beam('cedar', p(-L/2, -W/2 + .012, 0), p(L/2, -W/2 + .012, 0), .024, H * 2 - .02, up=(0, 0, 1)) if False else None
    for b in (-W / 2 + .015, W / 2 - .015):
        g.beam('beam', p(-L / 2, b, H / 2), p(L / 2, b, H / 2), .03, H)
    for a in (-L / 2 + .015, L / 2 - .015):
        g.beam('beam', p(a, -W / 2, H / 2), p(a, W / 2, H / 2), .03, H)
    for a in (-L / 2 + .1, L / 2 - .1):
        g.beam('plank', p(a, -W / 2 + .05, H + .03), p(a, W / 2 - .05, H + .03), .03, .035)
    for i in range(n):
        b = -W / 2 + .07 + (W - .14) * i / (n - 1)
        g.cyl('steel', p(-L / 2 + .09, b, H + .05), p(L / 2 - .09, b, H + .05), .0014, n=4, caps=False)
    # sound hole
    g.lathe('black_wood', p(0, 0, H + .012), [(.09, 0), (.1, 0)], n=30)


def tanpura(g, c, h=1.25, lean=.2):
    """Lying on a low stand. Gourd body, long neck, four strings."""
    x, y, z = c
    d = np.array([1, 0, lean]); d = d / np.linalg.norm(d)
    bz = np.array((x, y, z)); k = 14
    rs = [.0, .1, .17, .21, .22, .21, .18, .13, .08, .06]
    pts = [bz + d * (i * .055 - .25) for i in range(10)]
    g.tube('beam', np.array(pts), np.array(rs), n=24, caps=False)
    top = bz + d * (.25 + h)
    g.cyl('beam', bz + d * .24, top, .045, .036, n=12)
    for s in (-.018, -.006, .006, .018):
        o = np.array((0, s, .044))
        g.cyl('steel', bz + d * .02 + o, top + o * .6, .0008, n=4, caps=False)
    for t, sg in ((.72, 1), (.86, -1), (.98, 1), (1.1, -1)):
        q = bz + d * (.25 + t * h * .92)
        g.cyl('plank', q + np.array((0, -.07 * sg, 0)), q + np.array((0, .07 * sg, 0)), .009, n=6)


def didge(g, a, b, r0=.022, r1=.05):
    a = np.array(a, float); b = np.array(b, float); k = 24
    path = np.array([a + (b - a) * t for t in np.linspace(0, 1, k)])
    path[:, 0] += np.sin(np.linspace(0, 6, k)) * .012; path[:, 1] += np.sin(np.linspace(0, 4, k)) * .012
    g.tube('beam', path, np.linspace(r0, r1, k) ** 1.0 * (1 + .1 * np.sin(np.linspace(0, 11, k))), n=14)


def zafu(g, m, c, R=.21, h=.17):
    prof = [(0, 0), (R * .86, 0), (R, h * .22), (R * 1.02, h * .5), (R, h * .8), (R * .8, h), (0, h * 1.02)]
    g.lathe(m, c, prof[::-1], n=36)


def sheepskin(g, c, w=1.1, d=1.6, rz=0, seed=0, n=60):
    rng = np.random.default_rng(seed)
    U, V = np.meshgrid(np.linspace(-1, 1, n), np.linspace(-1, 1, n), indexing='ij')
    Rr = np.hypot(U, V * (1 + .1 * np.sin(np.arctan2(V, U) * 7)))
    z = np.clip(1 - Rr ** 5, 0, 1) ** .5 * .04 + sum(rng.normal(0, .004) * np.sin(U * rng.uniform(5, 15) + rng.uniform(0, 6)) * np.cos(V * rng.uniform(5, 15)) for _ in range(9))
    co, si = math.cos(math.radians(rz)), math.sin(math.radians(rz))
    P = np.stack([c[0] + U * w / 2 * co - V * d / 2 * si, c[1] + U * w / 2 * si + V * d / 2 * co, c[2] + np.maximum(z, 0)], -1)
    g.grid('wool', P)
