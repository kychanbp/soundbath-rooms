"""Rain room: a glasshouse with plants. Chimes hang from timber arms. Rain runs down the panes."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Rain and chimes'


def build(R):
    g = R.g; W, D, He, Hr = 9.2, 9.4, 3.1, 4.6
    R.floor('concrete_r', -W / 2, 1, W / 2, 1 + D)
    y1 = 1 + D
    xs = np.linspace(-W / 2, W / 2, 5); ys = np.linspace(1, y1, 5)
    far = [((a + b) / 2, b - a - .12, .55, He - .08) for a, b in zip(xs[:-1], xs[1:])]
    east = [((a + b) / 2, b - a - .12, .55, He - .08) for a, b in zip(ys[:-1], ys[1:])]
    R.wall('concrete_w', (W / 2, y1), (-W / 2, y1), He, far, reveal='steel', thick=.12)
    R.wall('concrete_w', (W / 2, 1), (W / 2, y1), He, east, reveal='steel', thick=.12)
    R.wall('concrete_w', (-W / 2, y1), (-W / 2, 1), He, east, reveal='steel', thick=.12)
    R.wall('clay', (-W / 2, 1), (W / 2, 1), He, [(0, 1.5, 0, 2.3)], reveal='beam')
    R.door(1.5, 2.3, 'beam')
    # gable glass roof with a ridge along Y, and frames
    for s in (-1, 1):
        for i in range(4):
            a, b = ys[i], ys[i + 1]
            A = (s * W / 2, a + .04, He); B = (0, a + .04, Hr); C = (0, b - .04, Hr); D_ = (s * W / 2, b - .04, He)
            R.glass(A, B, C, D_)
        for y in ys:
            g.beam('steel', (s * W / 2, y, He), (0, y, Hr), .05, .08, up=(0, 0, 1))
    # back gable and front gable closing triangles
    g.poly('clay', [(-W / 2, 1, He), (W / 2, 1, He), (0, 1, Hr)])
    R.glass((-W / 2, y1, He), (W / 2, y1, He), (0, y1, Hr), (0, y1, Hr))
    g.beam('steel', (0, 1, Hr), (0, y1, Hr), .08, .08)
    for x in xs: g.beam('steel', (x, y1, 0.5), (x, y1, He), .06, .06)
    for y in ys:
        for s in (-1, 1): g.beam('steel', (s * W / 2, y, .5), (s * W / 2, y, He), .06, .06)
    for s in (-1, 1):
        g.beam('steel', (s * W / 2, 1, He), (s * W / 2, y1, He), .08, .08)
    g.beam('steel', (-W / 2, y1, He), (W / 2, y1, He), .08, .08)
    # the teacher sits under one timber rail with all four chimes in reach, the ocean drum and rainstick at her side
    tx, ty = 0, 8.35
    R.teacher(tx, ty, (0, -1)); P.cushion(R.p, 'herring', (tx, ty, 0), .9, .9, .045, 0, 7); P.zafu(R.p, 'velvet', (tx, ty, .04)); R.obstacle(tx, ty, .55)
    y = 7.92
    for x in (-.95, .95):
        g.beam('beam', (x, y, 0), (x, y, 1.86), .08, .08); g.beam('beam', (x, y - .3, .03), (x, y + .3, .03), .08, .06)
    g.beam('beam', (-1.05, y, 1.86), (1.05, y, 1.86), .08, .09)
    for name, x in (('earth', -.5), ('water', -.17), ('air', .17), ('fire', .5)):
        P.koshi(R.p, (x, y, 0), H=1.83)
        R.instrument(name, (x, y + .06, 1.17))
    R.obstacle_box(-1.05, y - .25, 1.05, y + .05)
    P.ocean_drum(R.p, (0, 8.0, .33)); R.instrument('ocean', (0, 8.0, .39))
    R.model('wooden_stool_01', TRS(-2.4, 7.0, 0, 15, 1.0), 6000); R.obstacle(-2.4, 7.0, .3)
    P.rainstick(R.p, (.62, 8.02, .03), (.38, 8.12, .86)); R.instrument('stick', (.48, 8.08, .5))
    R.instrument('glassE', (4.6, 5.5, 2.2)); R.instrument('glassW', (-4.6, 5.5, 2.2))
    # stone path and a mat
    P.rug(g, 'herring', (.8, 4.8, 0), 3.2, 3.0, 0, 8, fringe=False)
    R.mat(.1, 4.8, 180, 'linen', 'wool', 0, look=(0, 8.4, 2.2)); R.mat(1.5, 4.8, 180, 'linen', 'wool', 1, look=(0, 8.4, 2.2))
    # plants fill the glasshouse edges
    rng = np.random.default_rng(2)
    pl = [('potted_plant_01', -4.0, 2.0), ('potted_plant_02', -4.0, 4.0), ('potted_plant_04', -4.0, 6.2), ('fern_02', -3.1, 2.7), ('calathea_orbifolia_01', -3.1, 5.2), ('anthurium_botany_01', -3.2, 7.2),
          ('potted_plant_02', 4.0, 2.1), ('potted_plant_04', 4.0, 4.3), ('fern_02', 3.1, 3.2), ('calathea_orbifolia_01', 3.2, 6.2), ('potted_plant_01', 4.0, 6.6), ('fern_02', -4.0, 8.9), ('anthurium_botany_01', 4.0, 8.8), ('potted_plant_02', 2.2, 9.6)]
    for n, x, y in pl:
        R.model(n, TRS(x, y, 0, rng.uniform(0, 360), rng.uniform(1.5, 2.0)), 18000); R.obstacle(x, y, .5)
    R.sky(-W / 2 - .7, 1, W / 2 + .7, y1 + .7, Hr + .8)
    return dict(box=[-W / 2, 1, 0, W / 2, y1, He], walk=[(-W / 2 + .35, 1.0, W / 2 - .35, y1 - .35)], surface='concrete',
                pano=(0, 5.6, 1.6), cams=[((-1.6, 2, 1.6), (.8, 9, 1.4)), ((1.2, 6.2, 1.2), (-3.4, 7, 1.2))],
                sky_hdri='green_sanctuary', hdri='rainforest_trail', rot=30, strength=1.1, exposure=.85, window_dir=(0, 0, 1), rt=[1.9, 1.8, 1.7, 1.7, 1.5, 1.2], sky_ev=-.4,
                meta=dict(rainGlass=True))
