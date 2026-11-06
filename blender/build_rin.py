"""Rin room: tatami, cedar posts, plaster, one side open to a stroll garden. A water jar sings below the eaves."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Rin bells'


def build(R):
    g = R.g; W, D, H = 7.2, 7.2, 2.75
    y1 = 1 + D
    # tatami laid in the auspicious pattern
    M = 1.8; S = .9; x0 = -W / 2
    def t(x, y, w, d):
        V = [(x, y, 0), (x + w, y, 0), (x + w, y + d, 0), (x, y + d, 0)]
        UV = [(0, 0), (1, 0), (1, .5), (0, .5)] if w >= d else [(0, .5), (0, 0), (1, 0), (1, .5)]
        g.add('tatami', V, UV, Q=[[0, 1, 2, 3]])
    for j in range(4):
        y = 1 + j * M
        for i in range(4):
            xx = x0 + i * M
            if (i + j) % 2 == 0: t(xx, y, M, S); t(xx, y + S, M, S)
            else: t(xx, y, S, M); t(xx + S, y, S, M)
    g.quad('floor_pale', (-.75, 0, 0), (.75, 0, 0), (.75, 1.0, 0), (-.75, 1.0, 0))
    # engawa veranda
    g.quad('hinoki', (-W / 2 - 1, y1, -.01), (W / 2 + 1, y1, -.01), (W / 2 + 1, y1 + 1.2, -.01), (-W / 2 - 1, y1 + 1.2, -.01))
    g.quad('hinoki', (-W / 2 - 1, y1 + 1.2, H + .05), (W / 2 + 1, y1 + 1.2, H + .05), (W / 2 + 1, 1, H + .05), (-W / 2 - 1, 1, H + .05)) if False else None
    R.wall('white_plaster', (W / 2, 1), (W / 2, y1), H)
    R.wall('white_plaster', (-W / 2, y1), (-W / 2, 1), H, [(5.0, 1.8, .85, 1.95)], reveal='hinoki')
    R.wall('white_plaster', (-W / 2, 1), (W / 2, 1), H, [(0, 1.5, 0, 2.15)], reveal='hinoki')
    R.door(1.5, 2.15, 'hinoki')
    g.quad('white_plaster', (-W / 2, y1, 2.15), (W / 2, y1, 2.15), (W / 2, y1, H), (-W / 2, y1, H))
    g.quad('hinoki', (-W / 2, y1, H), (W / 2, y1, H), (W / 2, 1, H), (-W / 2, 1, H))
    # eaves over the veranda
    g.quad('hinoki', (-W / 2 - 1, y1 + 1.2, 2.3), (W / 2 + 1, y1 + 1.2, 2.3), (W / 2 + 1, y1, 2.2), (-W / 2 - 1, y1, 2.2))
    # posts and rails
    for x in (-W / 2, -1.8, 1.8, W / 2):
        g.beam('hinoki', (x, y1, 0), (x, y1, 2.2), .12, .12)
        g.beam('hinoki', (x, y1 + 1.1, -.01), (x, y1 + 1.1, 2.28), .1, .1)
    for y in (1, y1):
        g.beam('hinoki', (-W / 2, y, 2.15), (W / 2, y, 2.15), .12, .08)
    for s in (-1, 1):
        for y in (2.8, 4.6, 6.4):
            g.beam('hinoki', (s * (W / 2 - .03), y, 0), (s * (W / 2 - .03), y, H), .1, .08)
    for x in np.arange(-W / 2 + .9, W / 2, .9):
        g.beam('hinoki', (x, 1, H - .03), (x, y1, H - .03), .04, .05)
    # shoji pushed to the sides: paper in a thin cedar grid
    for x0_, x1_ in ((-W / 2, -2.6), (-2.6, -1.8), (1.8, 2.6), (2.6, W / 2)):
        if x1_ - x0_ < 1: continue
        y = y1 - .02
        g.quad('shoji', (x1_, y, .05), (x0_, y, .05), (x0_, y, 2.13), (x1_, y, 2.13))
        for x in np.linspace(x0_, x1_, 5): g.beam('hinoki', (x, y - .012, .05), (x, y - .012, 2.13), .014, .028)
        for z in np.linspace(.05, 2.13, 9): g.beam('hinoki', (x0_, y - .012, z), (x1_, y - .012, z), .028, .014)
    # tokonoma alcove on the east wall
    P.cushion(R.p, 'plank', (0, 0, 0), .001, .001, .001) if False else None
    g.beam('hinoki', (W / 2 - .45, 4.3, .08), (W / 2 - .45, 6.3, .08), .9, .16)
    R.model('ceramic_vase_03', TRS(W / 2 - .45, 5.3, .16, 0, 1.4), 12000)
    # five bells on lacquer stands
    tx, ty = 0, 7.0
    R.teacher(tx, ty, (0, -1)); P.cushion(R.p, 'velvet', (tx, ty, 0), .72, .72, .06, 0, 7); R.obstacle(tx, ty, .5)
    P.zafu(R.p, 'herring', (tx, ty, .055), R=.2, h=.14)
    bells = [(.1, .09), (.13, .115), (.17, .15), (.14, .125), (.11, .1)]
    order = (4, 3, 0, 1, 2)
    for i, (rb, hb) in enumerate(bells):
        A = math.radians(-90 + (i - 2) * 40); x = tx + .6 * math.cos(A); y = ty + .6 * math.sin(A)
        P.bowl(R.p, (x, y, .07), rb, hb, m='brass', t=.006, seed=i + 3)
        P.cushion(R.p, 'velvet', (x, y, .0), rb * 2.2, rb * 2.2, .07, 0, i)
        R.instrument(f'r{order[i]}', (x, y, .07 + hb)); R.obstacle(x, y, rb + .12)
    # futons and floor cushions
    R.mat(-1.2, 4.6, 180, 'linen', 'herring', 0, look=(0, 7, 1.0)); R.mat(1.2, 4.6, 180, 'linen', 'herring', 1, look=(0, 7, 1.0))
    # water jar in the garden, sounds only
    R.instrument('jar', (1.8, y1 + 2.0, -.2))
    R.sky(-W / 2 - 2, 1, W / 2 + 2, y1 + 4, H + 3)
    return dict(box=[-W / 2, 1, 0, W / 2, y1 + 1.15, H], walk=[(-W / 2 + .3, 1.0, W / 2 - .3, y1 + 1.0)], surface='tatami',
                pano=(0, 4.8, 1.2), cams=[((-.3, 1.6, 1.4), (0, 8, 1.2)), ((-2.7, 6.3, .9), (2.2, 8.6, 1.0))],
                sky_hdri='green_sanctuary', hdri='ninomaru_teien', rot=40, strength=1.4, exposure=1.05, window_dir=(0, -.9, .4), rt=[.75, .62, .55, .5, .45, .38], sky_ev=-.8)
