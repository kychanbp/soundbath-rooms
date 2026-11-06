"""Gong room: dark timber, concrete floor, a slit of dusk along the top of the far wall, many candles."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Gong bath'


def build(R):
    g = R.g; W, D, H = 10.2, 10.4, 4.3
    R.floor('concrete_f', -W / 2, 1, W / 2, 1 + D)
    R.ceiling_planks('black_wood', -W / 2, 1, W / 2, 1 + D, H)
    R.wall('concrete_w', (W / 2, 1 + D), (-W / 2, 1 + D), H, [(x, 2.3, 3.72, 4.1) for x in (-3.3, 0, 3.3)], reveal='concrete_w', thick=.5)
    R.wall('black_wood', (W / 2, 1), (W / 2, 1 + D), H)
    R.wall('black_wood', (-W / 2, 1 + D), (-W / 2, 1), H)
    R.wall('black_wood', (-W / 2, 1), (W / 2, 1), H, [(0, 1.5, 0, 2.3)], reveal='beam')
    R.door(1.5, 2.3, 'beam')
    for y in np.arange(1, 1 + D + .1, 2.6):
        g.beam('beam', (-W / 2, y, H - .14), (W / 2, y, H - .14), .22, .28)
    R.skirting('beam', -W / 2, 1, W / 2, 1 + D, .14)
    # felt baffles on side walls soften the wash
    for s in (-1, 1):
        for y in np.arange(3, 10, 2.2):
            P.cushion(g, 'herring', (0, 0, 0), .001, .001, .001) if False else None
            g.quad('felt', (s * (W / 2 - .04), y + s * .9, .5), (s * (W / 2 - .04), y - s * .9, .5), (s * (W / 2 - .04), y - s * .9, 3.4), (s * (W / 2 - .04), y + s * .9, 3.4))
    # three gongs stand in a horseshoe, so that one player can reach them all with a long mallet
    tx, ty = 0, 7.75
    R.teacher(tx, ty, (0, 1), 'stand'); R.obstacle(tx, ty, .4)
    for name, Rr, tex, ang, lift in (('g40', .66, 'gong_a', 0, .5), ('g32', .5, 'gong_b', 62, .72), ('g24', .39, 'gong_c', -62, .9)):
        dist = 1.22
        cx_, cy_ = tx - dist * math.sin(math.radians(ang)), ty + dist * math.cos(math.radians(ang))
        T_ = TRS(cx_, cy_, 0, ang)
        with g.with_T(T_):
            cz = P.gong_stand(g, (0, 0, 0), Rr, lift=lift)
        with R.p.with_T(T_):
            P.gong(R.p, (0, 0, cz), Rr, tex=tex, lip=Rr * .09)
        R.instrument(name, (cx_, cy_, cz))
        R.obstacle(cx_, cy_, Rr + .22); R.obstacle(cx_ + .6 * math.cos(math.radians(ang)), cy_ + .6 * math.sin(math.radians(ang)), .35); R.obstacle(cx_ - .6 * math.cos(math.radians(ang)), cy_ - .6 * math.sin(math.radians(ang)), .35)
    P.rug(g, 'rugblue', (0, 4.3, 0), 6.6, 3.3, 0, 5)
    for i, (x, y, rz) in enumerate([(-2.1, 3.9, -12), (-.7, 3.6, -4), (.7, 3.6, 4), (2.1, 3.9, 12)]):
        R.mat(x, y, rz + 180, 'herring', 'wool', i, look=(0, 8.8, 2.4))
    rng = np.random.default_rng(3)
    pts = []
    for x in np.linspace(-4.6, 4.6, 15):
        y = 6.1 - .25 * math.cos(x); 
        if abs(x) < 4.7: pts.append((x + rng.normal(0, .05), y + rng.normal(0, .1), rng.uniform(.09, .24), .03))
    R.candles(pts)
    R.model('brass_candleholders', TRS(-4.3, 2.3, 0, 40, 1.2), 12000); R.obstacle(-4.3, 2.3, .3)
    R.model('brass_vase_03', TRS(4.3, 2.4, 0, 0, 1.6), 12000); R.obstacle(4.3, 2.4, .3)
    R.sky(-W / 2, 1, W / 2, 1 + D + 1.4, H + 1)
    return dict(box=[-W / 2, 1, 0, W / 2, 1 + D, H], walk=[(-W / 2 + .3, 1.0, W / 2 - .3, 1 + D - .4)], surface='concrete',
                pano=(0, 5.8, 1.5), cams=[((-.2, 1.6, 1.6), (0, 9, 1.8)), ((-3.4, 5.6, 1.1), (1.4, 9.2, 1.5)), ((-1.3, 7.8, .8), (.3, 9.3, 1.3))],
                sky_hdri='green_sanctuary', hdri='qwantani_dusk_2', rot=175, strength=8, shafts=.0, exposure=1.9, window_dir=(0, -.8, .5), rt=[2.8, 2.5, 2.2, 1.9, 1.5, 1.1], sky_ev=-.4)
