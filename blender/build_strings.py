"""String room: a barrel vault of cedar boards, one tall window on an autumn wood."""
import numpy as np, math
from lib import *
import props as P
from room_base import *

TITLE = 'Strings'


def build(R):
    g = R.g; W, D, Hw = 7.2, 8.2, 2.3
    y1 = 1 + D; Hr = 3.5
    R.floor('floor_pale', -W / 2, 1, W / 2, y1)
    a = np.linspace(0, np.pi, 28)
    Pv = np.zeros((28, 2, 3))
    for j, y in enumerate((1, y1)):
        Pv[:, j, 0] = W / 2 * np.cos(a); Pv[:, j, 1] = y; Pv[:, j, 2] = Hw + (Hr - Hw) * np.sin(a)
    g.grid('cedar', Pv, along='v')
    for y in np.linspace(1.2, y1 - .2, 7):
        path = np.stack([(W / 2 - .02) * np.cos(a), np.full(28, y), Hw + (Hr - Hw - .02) * np.sin(a)], -1)
        g.tube('beam', path, np.full(28, .05), n=8, caps=False)
    R.wall('cedar', (W / 2, 1), (W / 2, y1), Hw + .01, [(5.0, 2.8, .4, 2.2)], reveal='beam')
    R.wall('cedar', (-W / 2, y1), (-W / 2, 1), Hw + .01)
    # gable ends
    for y, flip in ((1, 0), (y1, 1)):
        n = 28; P0 = np.stack([W / 2 * np.cos(a), np.full(n, y), np.full(n, Hw)], -1); P1 = np.stack([W / 2 * np.cos(a), np.full(n, y), Hw + (Hr - Hw) * np.sin(a)], -1)
        g.grid('cedar', np.stack([P0, P1], 1) if flip == 0 else np.stack([P1, P0], 1))
    R.wall('cedar', (W / 2, y1), (-W / 2, y1), Hw + .01, [(0, 1.8, .9, 2.1)], reveal='beam')
    R.wall('cedar', (-W / 2, 1), (W / 2, 1), Hw + .01, [(0, 1.5, 0, 2.2)], reveal='beam')
    R.door(1.5, 2.2, 'beam')
    R.skirting('beam', -W / 2, 1, W / 2, y1, .12)
    # the sound bed stands on trestles, so that her knees fit below it
    P.monochord(g, (0, 7.0, .3), W=.6, H=.16, rz=0)
    for x in (-.85, .85):
        g.beam('beam', (x, 6.76, 0), (x, 6.76, .3), .06, .06); g.beam('beam', (x, 7.24, 0), (x, 7.24, .3), .06, .06); g.beam('beam', (x, 6.72, .29), (x, 7.28, .29), .06, .05)
    R.instrument('mono', (0, 7.0, .47)); R.obstacle_box(-1.2, 6.65, 1.2, 7.3)
    tx, ty = 0, 7.55
    R.teacher(tx, ty, (0, -1)); P.cushion(R.p, 'herring', (tx, ty, 0), .86, .8, .045, 0, 7); P.zafu(R.p, 'velvet', (tx, ty, .04)); R.obstacle(tx, ty, .5)
    # tanpura rests on low blocks at her left hand
    P.tanpura(R.p, (.78, 7.72, .2), lean=.1); g.beam('beam', (.62, 7.58, 0), (.62, 7.86, 0.08), .1, .1); g.beam('beam', (1.9, 7.72, 0), (1.9, 7.72, .24), .07, .07)
    R.instrument('tanpura', (.62, 7.62, .42)); R.obstacle(.85, 7.72, .36); R.obstacle(1.5, 7.72, .3)
    P.rug(g, 'jacquard', (0, 4.6, 0), 3.4, 2.5, 0, 9)
    R.mat(-.75, 4.6, 180, 'linen', 'wool', 0, look=(0, 7.7, 2.2)); R.mat(.75, 4.6, 180, 'linen', 'wool', 1, look=(0, 7.7, 2.2))
    R.model('wooden_lantern_01', TRS(-3.1, 8.5, 0, 20, 1.0), 12000); R.lamp((-3.1, 8.5, .35), (1, .62, .3), 22, .05); R.obstacle(-3.1, 8.5, .3)
    R.model('wooden_lantern_01', TRS(-3.1, 2.0, 0, 70, 1.0), 12000); R.lamp((-3.1, 2.0, .35), (1, .62, .3), 22, .05); R.obstacle(-3.1, 2.0, .3)
    R.model('potted_plant_02', TRS(3.1, 2.1, 0, 30, 1.0), 26000); R.obstacle(3.1, 2.1, .5)
    R.sky(-W / 2 - 1.2, .9, W / 2 + 1.4, y1 + 1.4, Hr + .6)
    return dict(box=[-W / 2, 1, 0, W / 2, y1, Hr], walk=[(-W / 2 + .3, 1.0, W / 2 - .3, y1 - .3)], surface='wood',
                pano=(0, 5, 1.3), cams=[((-.2, 1.7, 1.6), (.3, 8, 1.1)), ((2.2, 5.2, 1.0), (-.5, 7.2, .4))],
                sky_hdri='green_sanctuary', hdri='autumn_forest_01', rot=250, strength=7, exposure=1.25, window_dir=(-.9, 0, .4), rt=[1.3, 1.2, 1.1, .95, .8, .65], sky_ev=-.6)
