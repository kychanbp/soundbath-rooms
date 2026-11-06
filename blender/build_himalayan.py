"""Himalayan singing bowl room: timber and clay, deep windows on a mountain view."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Himalayan bowls'


def build(R):
    g = R.g; W, D, H = 9.4, 10.6, 3.5
    R.floor('floor_oak', -W / 2, 1, W / 2, 1 + D)
    R.ceiling_planks('plank', -W / 2, 1, W / 2, 1 + D, H)
    # window openings per wall: (centre along wall, width, sill, head)
    far = [(-2.9, 1.7, .7, 2.9), (0, 1.7, .7, 2.9), (2.9, 1.7, .7, 2.9)]
    east = [(4.2, 1.3, .9, 2.8), (7.6, 1.3, .9, 2.8)]
    west = []
    R.wall('clay', (W / 2, 1 + D), (-W / 2, 1 + D), H, far, reveal='beam')     # far wall, seen from inside
    R.wall('clay', (W / 2, 1), (W / 2, 1 + D), H, [(c, w, s, h) for c, w, s, h in east], reveal='beam')
    R.wall('clay', (-W / 2, 1 + D), (-W / 2, 1), H, west)
    R.wall('clay', (-W / 2, 1), (W / 2, 1), H, [(0, 1.5, 0, 2.3)], reveal='beam')
    R.door(1.5, 2.3, 'beam')
    # timber frame
    for y in np.arange(1.0, 1 + D + .1, 2.65):
        for s in (-1, 1):
            g.beam('beam', (s * (W / 2 - .13), y, 0), (s * (W / 2 - .13), y, H), .26, .26)
        g.beam('beam', (-W / 2, y, H - .16), (W / 2, y, H - .16), .24, .32)
    for x in (-W / 2 + .1, W / 2 - .1):
        g.beam('beam', (x, 1, H - .16), (x, 1 + D, H - .16), .22, .3)
    for x in np.arange(-W / 2 + .9, W / 2, .9):
        g.beam('beam', (x, 1, H - .38), (x, 1 + D, H - .38), .09, .13)
    g.beam('beam', (-W / 2 + .05, 1 + D - .05, .0), (W / 2 - .05, 1 + D - .05, .0), .1, .32) if False else None
    R.skirting('beam', -W / 2, 1, W / 2, 1 + D, .16)
    # window grilles
    for c, w, s, h in far:
        R.lattice('beam', (c - w / 2, 1 + D + .06, s), (c + w / 2, 1 + D + .06, h))
    for c, w, s, h in east:
        R.lattice('beam', (W / 2 + .06, c - w / 2, s), (W / 2 + .06, c + w / 2, h))
    # rug and the circle of bowls, with the listener's mats inside
    cx, cy = 0, 6.9
    P.rug(g, 'rugblue', (cx, cy, 0), 6.0, 4.6, 0, 3)
    P.rug(g, 'rugred', (cx, cy, .012), 5.3, 3.9, 0, 4, fringe=False)
    # the teacher sits at the far end of the rug, facing the mats, with the bowls in an arc within reach
    tx, ty = 0, 8.15
    R.teacher(tx, ty, (0, -1))
    P.cushion(R.p, 'herring', (tx, ty, .012), .9, .9, .045, 0, 7)
    P.zafu(R.p, 'velvet', (tx, ty, .05))
    R.obstacle(tx, ty, .55)
    fs = [(.15, .085), (.17, .095), (.19, .105), (.215, .12), (.19, .105), (.165, .09), (.14, .08)]
    for i, (rb, hb) in enumerate(fs):
        a = math.radians(-90 + (i - 3) * 35); x = tx + .72 * math.cos(a); y = ty + .72 * math.sin(a)
        P.torus(R.p, 'velvet', (x, y, .012), rb * .56, rb * .17, seed=i)
        P.bowl(R.p, (x, y, .05), rb, hb, seed=i)
        R.instrument(f'b{i}', (x, y, .05 + hb)); s_ = R.obstacle(x, y, rb + .12)
        P.mallet(R.p, (.62, 8.72, .055), 150, L=.2, head=.024)
    # tingsha on a small cushion
    P.cushion(R.p, 'velvet', (-.72, 8.68, .012), .24, .24, .05, 15, 2)
    R.instrument('tingsha', (0, 8.0, .78))
    for i, (x, y, rz) in enumerate([(-1.25, 5.0, 8), (0, 4.85, -3), (1.25, 5.0, -8)]):
        R.mat(x, y, rz, 'linen', 'wool', i)
    # butter lamps on a long low bench under the far windows
    g.beam('beam', (-3.9, 1 + D - .42, .28), (3.9, 1 + D - .42, .28), .46, .07)
    for x in (-3.8, 3.8, -1.3, 1.3):
        g.beam('beam', (x, 1 + D - .42, 0), (x, 1 + D - .42, .25), .09, .34)
    for x in np.linspace(-3.5, 3.5, 11):
        y = 1 + D - .42
        R.p.lathe('brass', (x, y, .315), [(0, 0), (.022, 0), (.012, .012), (.012, .03), (.036, .045), (.042, .075), (.03, .07), (0, .062)][::-1], n=16)
        R.flame((x, y, .405), .04)
    R.obstacle_box(-3.9, 1 + D - .62, 3.9, 1 + D - .25)
    # woven hangings on the west wall
    for y, tint in ((3.3, 'rugblue'), (5.95, 'rugred'), (8.6, 'rugblue')):
        g.quad(tint, (-W / 2 + .03, y + .55, .55), (-W / 2 + .03, y - .55, .55), (-W / 2 + .03, y - .55, 2.75), (-W / 2 + .03, y + .55, 2.75))
        g.cyl('beam', (-W / 2 + .05, y - .68, 2.77), (-W / 2 + .05, y + .68, 2.77), .018, n=8)
    # low table with a butter lamp
    R.model('chinese_tea_table', TRS(-3.6, 8.9, 0, 90, 1.0), 300000)
    R.model('brass_vase_03', TRS(-3.6, 8.9, .42, 0, 1.0), 12000)
    R.model('brass_pot_01', TRS(3.75, 2.2, 0, 40, 1.5), 8000)
    R.model('potted_plant_02', TRS(-3.75, 2.0, 0, 20, 1.0), 26000)
    R.model('wicker_basket_01', TRS(3.65, 9.9, 0, 10, 1.0), 12000)
    R.obstacle(-3.6, 8.9, .9); R.obstacle(3.75, 2.2, .5); R.obstacle(-3.75, 2, .6); R.obstacle(3.65, 9.9, .5)
    R.sky(-W / 2 - 1, 0.6, W / 2 + 1, 1 + D + 1, H + 1)
    return dict(
        box=[-W / 2, 1, 0, W / 2, 1 + D, H], walk=[(-W / 2 + .3, 1.0, W / 2 - .3, 1 + D - .3)], surface='wood',
        pano=(0, 5.6, 1.35), cams=[((-3.8, 2.0, 1.55), (1.5, 9, 1.0)), ((.2, 3.0, 1.1), (0, 9, 1.0)), ((2.6, 7.2, .7), (-1, 9.0, .25))],
        sky_hdri='green_sanctuary', hdri='fouriesburg_mountain_lookout', rot=165, strength=6, shafts=1.0, exposure=1.0, window_dir=(0, -.7, .7), rt=[1.9, 1.7, 1.5, 1.3, 1.1, .9])
