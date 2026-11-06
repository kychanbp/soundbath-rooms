"""Room helper: shell pieces, props, instruments, seats, and collision data, all in one world frame."""
import numpy as np, math
from lib import *
import props as P


class Room:
    def __init__(s, name, T):
        s.name = name; s.T = np.array(T, float)
        s.g = Geo(); s.p = Geo(); s.g.T = s.T; s.p.T = s.T
        s.instruments = {}; s.obstacles = []; s.seats = []; s.windows = []; s.models = []; s.stubs = []
        s.lights = []; s.flames = []; s.anim = []; s.skybox = None; s.glows = []; s.teacher_at = None

    def w(s, x, y, z=0):
        return (s.T @ np.array([x, y, z, 1.]))[:3]

    def floor(s, m, x0, y0, x1, y1, z=0):
        s.g.quad(m, (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z))
        s.g.quad(m, (-.75, 0, z), (.75, 0, z), (.75, 1.02, z), (-.75, 1.02, z))

    def ceiling_planks(s, m, x0, y0, x1, y1, z):
        s.g.quad(m, (x0, y1, z), (x1, y1, z), (x1, y0, z), (x0, y0, z))

    def wall(s, m, a, b, H, openings=(), reveal=None, thick=.34, base=0):
        """Wall from a to b, room on the left of a->b. openings: (centre coordinate along the wall axis, width, sill, head)."""
        a = np.array(a, float); b = np.array(b, float); L = np.linalg.norm(b - a); u = (b - a) / L
        n = np.array([-u[1], u[0]]); ax = 0 if abs(u[0]) > .5 else 1
        ops = sorted([((c - a[ax]) / u[ax], w, sl, h) for c, w, sl, h in openings])
        xs = sorted({0., L, *[t - w / 2 for t, w, _, _ in ops], *[t + w / 2 for t, w, _, _ in ops]})
        zs = sorted({base, H, *[v for _, _, sl, h in ops for v in (sl, h)]})
        xs = np.array(xs); zs = np.array(zs); nx, nz = len(xs), len(zs)
        V = []; UV = []
        for z in zs:
            for x in xs:
                p = a + u * x; V.append((p[0], p[1], z)); UV.append((x, z))
        V = np.array(V); UV = np.array(UV) * s.g.uvs(m) + s.g.rng.random(2)
        Q = []
        for j in range(nz - 1):
            for i in range(nx - 1):
                cx = (xs[i] + xs[i + 1]) / 2; cz = (zs[j] + zs[j + 1]) / 2
                if any(abs(cx - t) < w / 2 and sl < cz < h for t, w, sl, h in ops): continue
                k = j * nx + i
                Q.append((k + nx, k + nx + 1, k + 1, k))
        s.g.add(m, V, UV, Q=Q)
        rm = reveal or m
        for t, w, sl, h in ops:
            p0 = a + u * (t - w / 2); p1 = a + u * (t + w / 2); out = -n * thick
            q = lambda A, B, C, D: s.g.quad(rm, A, B, C, D)
            P3 = lambda p, z, o=0: (p[0] + out[0] * o, p[1] + out[1] * o, z)
            q(P3(p0, h), P3(p0, h, 1), P3(p0, sl, 1), P3(p0, sl))       # jambs, facing into the opening
            q(P3(p1, sl), P3(p1, sl, 1), P3(p1, h, 1), P3(p1, h))
            q(P3(p0, h), P3(p1, h), P3(p1, h, 1), P3(p0, h, 1))         # head
            if sl > 0: q(P3(p1, sl), P3(p0, sl), P3(p0, sl, 1), P3(p1, sl, 1))
            if sl > 0:
                c0 = np.r_[P3(p0, sl, .5)]; c1 = np.r_[P3(p1, sl, .5)]; c2 = np.r_[P3(p1, h, .5)]; c3 = np.r_[P3(p0, h, .5)]
                s.windows.append([s.w(*c0).tolist(), s.w(*c1).tolist(), s.w(*c2).tolist(), s.w(*c3).tolist()])

    def door(s, w, h, m, H=None):
        """Short passage from the gallery (y=0) into the room (y=1)."""
        s.g.quad(m, (w / 2, 1, h), (w / 2, 0, h), (w / 2, 0, 0), (w / 2, 1, 0))
        s.g.quad(m, (-w / 2, 0, h), (-w / 2, 1, h), (-w / 2, 1, 0), (-w / 2, 0, 0))
        s.g.quad(m, (-w / 2, 1, h), (w / 2, 1, h), (w / 2, 0, h), (-w / 2, 0, h))
        s.stubs.append((-w / 2 - .1, -.25, w / 2 + .1, h))

    def skirting(s, m, x0, y0, x1, y1, h, gaps=()):
        for a, b, c, d in ((x0, y0, x0, y1), (x1, y0, x1, y1), (x0, y1, x1, y1)):
            s.g.beam(m, (a, b, h / 2), (c, d, h / 2), .03, h)
        for a, b in (((x0, y0), (-.75, y0)), ((.75, y0), (x1, y0))):
            s.g.beam(m, (*a, h / 2), (*b, h / 2), .03, h)

    def lattice(s, m, lo, hi, nx=6, nz=9, bar=.03, depth=.05):
        lo = np.array(lo, float); hi = np.array(hi, float)
        d = hi[:2] - lo[:2]
        for t in np.linspace(0, 1, nx + 1):
            q = lo[:2] + d * t
            s.g.beam(m, (q[0], q[1], lo[2]), (q[0], q[1], hi[2]), bar if t not in (0, 1) else bar * 2.2, depth, up=(abs(d[0]) < 1e-6, abs(d[1]) < 1e-6, 0))
        for t in np.linspace(0, 1, nz + 1):
            z = lo[2] + (hi[2] - lo[2]) * t
            s.g.beam(m, (lo[0], lo[1], z), (hi[0], hi[1], z), depth, bar if t not in (0, 1) else bar * 2.2)

    def glow(s, a, b, c, d, strength=.6, col=(1, .8, .6)):
        s.glows.append(([s.w(*a), s.w(*b), s.w(*c), s.w(*d)], strength, col))

    def glass(s, a, b, c, d):
        s.windows.append([s.w(*q).tolist() for q in (a, b, c, d)])

    def candles(s, pts, mat='wax'):
        for x, y, h, r in pts:
            P.candle(s.p, (x, y, 0), r, h, m=mat)
            s.flame((x, y, h + .012), .045)

    def teacher(s, x, y, facing, pose='seat'):
        """facing: local direction she looks along, as (dx, dy). She is posed in a separate file and baked here as a shadow."""
        p = s.w(x, y); d = s.T[:3, :3] @ np.array([facing[0], facing[1], 0.])
        s.teacher_at = dict(pos=[float(p[0]), float(p[1])], yaw=float(math.atan2(-d[0], d[1])), z=0.0, pose=pose)

    def instrument(s, id, p):
        s.instruments[id] = [float(v) for v in s.w(*p)]

    def obstacle(s, x, y, r):
        q = s.w(x, y); s.obstacles.append([float(q[0]), float(q[1]), r])

    def obstacle_box(s, x0, y0, x1, y1):
        for x in np.arange(x0, x1 + .01, .4):
            for y in np.arange(y0, y1 + .01, .4):
                s.obstacle(x, y, .32)

    def seat(s, x, y, z, look):
        q = s.w(x, y, z); l = s.w(*look)
        s.seats.append(dict(pos=[float(v) for v in q], look=[float(v) for v in l]))

    def mat(s, x, y, rz, top, bl, seed=0, look=None, lie=True):
        """Floor mat with a bolster and a folded blanket. rz=0 means the head end points to -Y."""
        p = s.p
        P.cushion(p, top, (x, y, .0), .78, 1.95, .055, rz, seed + 10, sag=.1)
        c, n = math.cos(math.radians(rz)), math.sin(math.radians(rz))
        P.bolster(p, 'velvet' if seed % 2 else 'herring', (x + n * .82, y - c * .82, .05), .62, .11, rz, seed)
        P.blanket(p, bl, (x - n * .75, y + c * .75, .055), .54, .34, rz + 2, seed + 3)
        s.seat(x, y, .05, look or (x - n * 3, y + c * 3, .9))

    def model(s, name, T, max_tris=20000):
        s.models.append((name, s.T @ np.array(T), max_tris))

    def sky(s, x0, y0, x1, y1, h):
        a = s.w(x0, y0); b = s.w(x1, y1)
        lo = np.minimum(a, b); hi = np.maximum(a, b)
        s.skybox = [float(lo[0]), float(lo[1]), -.5, float(hi[0]), float(hi[1]), float(h)]

    def lamp(s, p, col, power, radius=.02):
        s.lights.append((s.w(*p), col, power, radius))

    def flame(s, p, h=.05):
        s.flames.append(dict(pos=[float(v) for v in s.w(*p)], h=h))
        s.lamp(p, (1, .55, .22), 9 * (h / .05) ** 2, .012)

    def blender_objects(s, coll):
        sh = s.g.build(coll, 'shell_'); pr = s.p.build(coll, 'prop_')
        return sh, pr
