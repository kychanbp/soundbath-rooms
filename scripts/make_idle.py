"""Turn the pose tracks of generated clips into one slow looped body movement for the teachers.
Depth from one camera is noisy, so depth signals get a stronger filter and a smaller weight."""
import json, numpy as np
from scipy import signal
OUT = 'web/assets/teacher/idle.json'; RATE = 12; SLOW = 2.4
def track(path):
    d = json.load(open(path)); f = d['fps']; P = np.array([x['pose'] for x in d['frames']])
    nose, le, re, ls, rs, lh, rh = (P[:, i] for i in (0, 7, 8, 11, 12, 23, 24))
    sh = (ls + rs) / 2; hip = (lh + rh) / 2; em = (le + re) / 2; ew = np.linalg.norm(le[:, :2] - re[:, :2], axis=1).mean()
    S = dict(lean=np.arctan2(sh[:, 0] - hip[:, 0], hip[:, 1] - sh[:, 1]), roll=np.arctan2(ls[:, 1] - rs[:, 1], ls[:, 0] - rs[:, 0]), twist=(ls[:, 2] - rs[:, 2]) * .5, pitch=(sh[:, 2] - hip[:, 2]) * .4,
             hyaw=(nose[:, 0] - em[:, 0]) / ew * .9, hpitch=(nose[:, 1] - em[:, 1]) / ew * .7, hroll=np.arctan2(le[:, 1] - re[:, 1], le[:, 0] - re[:, 0]))
    b, a = signal.butter(2, 1.1 / (f / 2)); o = {}
    for k, v in S.items():
        v = np.unwrap(v) if k in ('roll', 'hroll') else v
        v = signal.filtfilt(b, a, v - v.mean()); n = int(len(v) / f * SLOW * RATE)
        o[k] = np.interp(np.linspace(0, len(v) - 1, n), np.arange(len(v)), v)
    return o
A, B = track('data/motion/next0.json'), track('data/motion/next1.json')
xf = int(1.8 * RATE); out = {}
for k in A:
    w = .5 - .5 * np.cos(np.linspace(0, np.pi, xf))
    a, b = A[k], B[k]
    m = np.r_[a[:-xf], a[-xf:] * (1 - w) + b[:xf] * w, b[xf:-xf]]
    m[:xf] = m[:xf] * w + b[-xf:] * (1 - w)                # the end flows into the start
    out[k] = [round(float(v), 4) for v in np.clip(m, -.5, .5)]
    print(k, 'range deg', round(float(np.degrees(np.ptp(m))), 1))
json.dump(dict(rate=RATE, **out), open(OUT, 'w'), separators=(',', ':')); print(len(out['lean']) / RATE, 's loop')
