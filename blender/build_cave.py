"""Stone chamber: a natural cave with a crack of daylight, candles, a shallow pool."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Cave drum'


def vnoise(p, seed):
    """Sum of random plane waves. Fast smooth noise for a vertex grid."""
    rng = np.random.default_rng(seed); o = np.zeros(p.shape[:-1])
    for f, a, k in ((.35, 1, 6), (.9, .42, 9), (2.1, .16, 12), (5.0, .05, 14)):
        for _ in range(k):
            d = rng.normal(0, 1, 3); d /= np.linalg.norm(d)
            o += a / math.sqrt(k) * np.sin((p @ d) * f * 2 + rng.uniform(0, 6.3))
    return o


def build(R):
    g = R.g; p = R.p; cx, cy = 0, 8.2; Rx, Ry, Hz = 6.2, 7.0, 5.4
    n, k = 260, 110
    A = np.linspace(0, 2 * np.pi, n, endpoint=False); T = np.linspace(0, np.pi / 2, k)
    aa, tt = np.meshgrid(A, T, indexing='ij')
    u = np.stack([np.cos(aa) * np.cos(tt), np.sin(aa) * np.cos(tt), np.sin(tt)], -1)
    Pts = u * [Rx, Ry, Hz]
    d = vnoise(Pts, 3)
    Pts = Pts + u * d[..., None] * .55 * (1 - .75 * (tt / (np.pi / 2)) ** 4)[..., None]
    # the opening at the top is a long crack, not a circle
    q = np.clip((tt / (np.pi / 2) - .78) / .22, 0, 1)[..., None] ** 2
    Pts = Pts * np.concatenate([1 - .55 * q, 1 + 1.5 * q, 1 + 0 * q], -1)
    # bottom edge stays at the floor; keep a door tunnel at -Y
    Pts[..., 2] = np.maximum(Pts[..., 2], 0)
    Pts[..., 0] += cx; Pts[..., 1] += cy
    W = (np.abs(Pts[..., 0]) < 1.15) & (Pts[..., 1] < 3.2) & (Pts[..., 2] < 2.5)
    Pts[..., 1][W] = Pts[..., 1][W] - 1.9   # push the wall back around the door
    # crack at the top: leave out faces near the apex
    keep = np.ones((n, k - 1), bool); keep[:, -2:] = False
    # texture coordinates spread outward from the top, so the rock does not pinch at the crack
    Q_ = Pts[:, :-5]; nu, nv = Q_.shape[:2]
    Q2 = np.concatenate([Q_, Q_[:1]], 0)
    A2 = np.r_[A, 2 * np.pi][:, None]
    du = Q2[..., 0] - cx + Q2[..., 2] * np.cos(A2); dv = Q2[..., 1] - cy + Q2[..., 2] * np.sin(A2)
    UV_ = np.stack([du, dv], -1).reshape(-1, 2) / 5.0
    idx = np.arange((nu + 1) * nv).reshape(nu + 1, nv)
    qq = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], -1).reshape(-1, 4)[:, ::-1]
    p.add('rock', Q2.reshape(-1, 3), UV_, Q=qq)
    # floor: packed sand with small rises, kept near z=0 so walking stays level
    m = 180; X, Y = np.meshgrid(np.linspace(-Rx - 1, Rx + 1, m), np.linspace(cy - Ry - 1, cy + Ry + 1, m), indexing='ij')
    Fp = np.stack([X, Y, np.zeros_like(X)], -1)
    h = vnoise(Fp * [1, 1, 0], 9) * .018
    r = np.hypot((X - cx) / Rx, (Y - cy) / Ry)
    h = h + np.clip(r - .78, 0, 1) ** 2 * 3.0
    h = h * (1 - np.exp(-(X / 1.5) ** 4) * (Y < 4.5))
    Fp[..., 2] = h
    p.grid('sand2', Fp)
    # door tunnel with rock jambs
    R.door(1.5, 2.3, 'rock')
    g.quad('rock2', (-.75, 0, .002), (.75, 0, .002), (.75, 1.3, .002), (-.75, 1.3, .002))
    # the shallow pool
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False); ring = [(0, 0)]
    pool = np.stack([3.1 + 1.25 * np.cos(a) * (1 + .1 * np.sin(a * 3)), 10.4 + .85 * np.sin(a) * (1 + .14 * np.cos(a * 2)), np.full(48, .012)], -1)
    pp = np.stack([np.full(48, 3.1), np.full(48, 10.4), np.full(48, .012)], -1)
    g.grid('water', np.stack([pool, pp], 1)[::-1], closed_u=True)
    # drum on a stand in the middle, skin toward the door
    tx, ty = 0, 8.4
    R.teacher(tx, ty, (0, -1)); P.sheepskin(R.p, (tx, ty, .015), 1.0, 1.0, 0, 3); P.zafu(R.p, 'velvet', (tx, ty, .03)); R.obstacle(tx, ty, .55)
    y = 7.72; x0 = -.24
    P.frame_drum(R.p, (x0, y, .58), R=.3, depth=.085, face=1)
    g.beam('beam', (x0 - .38, y, 0), (x0 - .3, y, .6), .05, .05); g.beam('beam', (x0 + .38, y, 0), (x0 + .3, y, .6), .05, .05)
    g.beam('beam', (x0 - .42, y - .28, .03), (x0 - .4, y + .28, .03), .05, .05); g.beam('beam', (x0 + .42, y - .28, .03), (x0 + .4, y + .28, .03), .05, .05)
    R.instrument('drum', (x0, y + .05, .6)); R.obstacle(x0, y, .55)
    # didgeridoo: the bell rests on a stone and the mouthpiece comes to her
    R.model('rock_moss_set_01', TRS(.95, 6.6, 0, 80, .28), 6000)
    P.didge(R.p, (.92, 6.62, .2), (.04, 8.1, .97)); R.instrument('didge', (.1, 7.98, .9)); R.obstacle(.6, 7.1, .4); R.obstacle(.95, 6.6, .4)
    R.instrument('drip1', (3.1, 10.4, 1.5)); R.instrument('drip2', (-4.2, 6.5, 1.2)); R.instrument('drip3', (2.8, 4.6, 1.2))
    P.sheepskin(R.p, (-1.2, 4.4, .015), 1.0, 1.8, 170, 1); P.sheepskin(R.p, (1.1, 4.3, .015), 1.0, 1.8, 192, 2)
    R.seat(-1.2, 4.4, .06, (0, 8.4, 2.2)); R.seat(1.1, 4.3, .06, (0, 8.4, 2.2))
    # candles on ledges of rock
    rng = np.random.default_rng(1); pts = []
    for i in range(16):
        q = rng.uniform(.25, 2.9) if i % 2 else rng.uniform(3.4, 6.0); rr = rng.uniform(.70, .76)
        pts.append((cx + Rx * rr * math.cos(q), cy + Ry * rr * math.sin(q), rng.uniform(.1, .22), .032))
    R.candles(pts)
    R.model('rock_moss_set_01', TRS(4.1, 11.4, 0, 30, 1.0), 26000); R.obstacle(4.1, 11.4, .9)
    R.model('brass_pot_01', TRS(-2.9, 11.2, 0, 70, 1.6), 8000); R.obstacle(-2.9, 11.2, .4)
    R.glass((-.25, cy - 1, Hz - .1), (.25, cy - 1, Hz - .1), (.25, cy + 1, Hz - .1), (-.25, cy + 1, Hz - .1))
    R.sky(cx - 3, cy - 4, cx + 3, cy + 4, Hz + 2)
    return dict(box=[-Rx, cy - Ry - .4, 0, Rx, cy + Ry, Hz], walk=[(-.72, -.02, .72, 3.4)], surface='stone',
                pano=(0, 7.0, 1.6), cams=[((0, 1.8, 1.6), (0, 9, 1.2)), ((-2.6, 6.0, 1.0), (2.8, 11, 1.0)), ((.5, 5.8, 1.1), (0, 7.6, 1.0))],
                hdri='misty_pines', rot=10, strength=9, shafts=.7, exposure=1.35, window_dir=(0, 0, 1), rt=[5.4, 5, 4.6, 3.8, 2.8, 1.9], sky_ev=-.3,
                meta=dict(walkc=[[float(v) for v in R.w(0, 7.6)[:2]] + [5.0]]))
