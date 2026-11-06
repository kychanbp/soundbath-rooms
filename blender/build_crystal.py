"""Crystal bowl room: a round white chamber with a dome and an open oculus."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Crystal bowls'


def build(R):
    g = R.g; Rd = 5.4; cy = 6.4; Hw = 2.9; Ho = 6.2; ro = 1.45
    # floor: a disc of pale concrete
    n = 96
    a = np.linspace(0, 2 * np.pi, n, endpoint=False) - np.pi / 2
    rings = np.array([0.01, .25, .5, .75, 1.0]) * Rd
    Pf = np.zeros((n, len(rings), 3))
    for j, r in enumerate(rings): Pf[:, j, 0] = r * np.cos(a); Pf[:, j, 1] = cy + r * np.sin(a)
    g.grid('concrete_w', Pf[:, ::-1], closed_u=True)
    g.quad('concrete_w', (-.75, 0, 0), (.75, 0, 0), (.75, 1.2, 0), (-.75, 1.2, 0))
    # wall and dome are one revolved surface with a gap for the door
    gap = math.asin(.75 / Rd)
    aa = np.linspace(-np.pi / 2 + gap, 1.5 * np.pi - gap, n)
    t = np.linspace(0, 1, 26); zz = Hw + (Ho - Hw) * np.sin(t * np.pi / 2); rr = Rd * np.cos(t * np.pi / 2) ** .8 * (1 - ro / Rd) + ro
    pr = np.r_[np.array([[Rd, 0], [Rd, 2.25], [Rd, Hw]]), np.c_[rr[1:], zz[1:]]]
    Pw = np.zeros((n, len(pr), 3))
    for j, (r, z) in enumerate(pr): Pw[:, j, 0] = r * np.cos(aa); Pw[:, j, 1] = cy + r * np.sin(aa); Pw[:, j, 2] = z
    g.grid('lime', Pw, flip=True)
    # above the door
    ad = np.linspace(-np.pi / 2 - gap, -np.pi / 2 + gap, 6); Pa = np.zeros((6, 2, 3))
    for j, z in enumerate((2.25, Hw)): Pa[:, j, 0] = Rd * np.cos(ad); Pa[:, j, 1] = cy + Rd * np.sin(ad); Pa[:, j, 2] = z
    Pa2 = np.zeros((n, len(pr) - 2, 3))
    g.grid('lime', Pa, flip=True)
    ad2 = np.linspace(-np.pi / 2 - gap, -np.pi / 2 + gap, 6)
    Pb = np.zeros((6, len(pr) - 2, 3))
    for j, (r, z) in enumerate(pr[2:]): Pb[:, j, 0] = r * np.cos(ad2); Pb[:, j, 1] = cy + r * np.sin(ad2); Pb[:, j, 2] = z
    g.grid('lime', Pb, flip=True)
    R.door(1.5, 2.25, 'lime')
    # concrete oculus collar
    Pc = np.zeros((48, 2, 3)); ac = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    for j, z in enumerate((Ho, Ho + .35)): Pc[:, j, 0] = ro * np.cos(ac); Pc[:, j, 1] = cy + ro * np.sin(ac); Pc[:, j, 2] = z
    g.grid('concrete_w', Pc[:, ::-1], closed_u=True, flip=True)
    # a low bench that follows the wall
    t = np.linspace(-np.pi / 2 + gap + .12, 1.5 * np.pi - gap - .12, 80); Pl = []
    P0 = np.stack([(Rd - .42) * np.cos(t), cy + (Rd - .42) * np.sin(t), np.full(80, .42)], -1)
    P1 = np.stack([(Rd - .42) * np.cos(t), cy + (Rd - .42) * np.sin(t), np.zeros(80)], -1)
    P2 = np.stack([(Rd - .0) * np.cos(t), cy + (Rd - .0) * np.sin(t), np.full(80, .42)], -1)
    g.grid('concrete_w', np.stack([P1, P0, P2], 1), flip=True)
    # slender timber ribs follow the dome up to the oculus, and a ring ties them together
    for k in range(16):
        A = (k + .5) / 16 * 2 * np.pi - np.pi / 2
        if abs(math.sin(A) + 1) < .02: continue
        pp = pr[pr[:, 1] > 0] - [.05, 0]
        pp = np.r_[[[Rd - .05, .42]], pp]
        path = np.stack([pp[:, 0] * math.cos(A), cy + pp[:, 0] * math.sin(A), pp[:, 1]], -1)
        g.tube('beam', path, np.full(len(path), .05), n=6, caps=False)
    rg = np.linspace(0, 2 * np.pi, 96, endpoint=False)
    g.tube('beam', np.stack([(ro + .03) * np.cos(rg), cy + (ro + .03) * np.sin(rg), np.full(96, Ho - .02)], -1), np.full(96, .05), n=6, caps=False)
    # seven bowls in a ring, largest at the back
    tx, ty = 0, cy + 2.55
    R.teacher(tx, ty, (0, -1)); P.cushion(R.p, 'linen', (tx, ty, 0), .9, .9, .045, 0, 7); P.zafu(R.p, 'linen', (tx, ty, .04)); R.obstacle(tx, ty, .55)
    notes = [(.2, .19), (.185, .18), (.17, .165), (.16, .155), (.15, .145), (.14, .135), (.13, .125)]
    for i, (rb, hb) in enumerate([notes[k] for k in (5, 3, 1, 0, 2, 4, 6)]):
        ix = (5, 3, 1, 0, 2, 4, 6)[i]
        A = math.radians(-90 + (i - 3) * 35); x = tx + .74 * math.cos(A); y = ty + .74 * math.sin(A)
        P.torus(R.p, 'terry', (x, y, 0), rb * .78, rb * .1, seed=i, squash=.7)
        P.crystal(R.p, (x, y, .03), rb, hb)
        R.instrument(f'c{ix}', (x, y, .03 + hb)); R.obstacle(x, y, rb + .1)
    P.cushion(R.p, 'linen', (.72, ty + .1, 0), .24, .24, .03, 0, 2)
    R.instrument('fork', (0, ty - .32, .92))
    # four mats like spokes, heads to the middle, facing the teacher
    for i, A in enumerate((-150, -110, -70, -30)):
        r = 1.9; x = r * math.cos(math.radians(A)); y = cy + r * math.sin(math.radians(A))
        R.mat(x, y, A + 90 + 180, 'linen', 'herring', i, look=(tx, ty, 1.5))
    R.model('calathea_orbifolia_01', TRS(-3.9, 2.9, .42, 30, 1.0), 26000); R.obstacle(-3.5, 3.1, .5)
    R.model('anthurium_botany_01', TRS(4.2, 3.6, .42, 200, 1.0), 26000); R.obstacle(3.9, 3.7, .5)
    R.glass((-ro, cy - ro, Ho + .34), (ro, cy - ro, Ho + .34), (ro, cy + ro, Ho + .34), (-ro, cy + ro, Ho + .34))
    R.sky(-Rd, cy - Rd, Rd, cy + Rd, Ho + 1.6)
    return dict(box=[-Rd, cy - Rd, 0, Rd, cy + Rd, Ho], walk=[(-.72, .9, .72, 2.0)], surface='concrete',
                pano=(0, cy, 1.5), cams=[((0, 3, 1.5), (0, 9, 1.0))],
                hdri='qwantani_noon', rot=95, strength=9, shafts=.8, exposure=1.6, window_dir=(0, 0, 1), rt=[5.2, 5.8, 6, 5.4, 4.2, 3], sky_ev=-.6,
                meta=dict(walkc=[list(map(float, R.w(0, cy)[:2])) + [Rd - .62]]))
