"""Compute a stereo impulse response per room.
Early part: image sources in a box of the room's size. Late part: band noise that decays at the
room's measured-style reverberation times per octave band (125 Hz to 4 kHz)."""
import os, subprocess, json, sys
import numpy as np
from scipy import signal
from scipy.io import wavfile
SR = 48000
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = f'{ROOT}/web/assets/audio/rir'; os.makedirs(OUT, exist_ok=True)
BANDS = [125, 250, 500, 1000, 2000, 4000]
# name: size (x,y,z) m, RT60 by octave band s, early wall reflection gain, wet gain
ROOMS = dict(
    himalayan=((9.4, 10.6, 3.5), [1.9, 1.7, 1.5, 1.3, 1.1, .9], .70, .34),
    crystal=((10.8, 10.8, 6.2), [5.2, 5.8, 6.0, 5.4, 4.2, 3.0], .90, .62),
    gong=((10, 10, 4.2), [2.8, 2.5, 2.2, 1.9, 1.5, 1.1], .76, .42),
    rain=((9, 9, 4.4), [1.9, 1.8, 1.7, 1.7, 1.5, 1.2], .82, .38),
    rin=((8, 8, 2.8), [.75, .62, .55, .5, .45, .38], .50, .22),
    strings=((7.2, 8.2, 3.2), [1.3, 1.2, 1.1, .95, .8, .65], .66, .30),
    cave=((12, 13, 6), [5.4, 5.0, 4.6, 3.8, 2.8, 1.9], .86, .60),
    hall=((60, 60, 30), [.9, .8, .7, .6, .5, .4], .2, .05),
)


def early(size, g, rng, ch):
    L = int(.16 * SR); h = np.zeros(L)
    lx, ly, lz = size
    # source and listener roughly 2.5 m apart, the ears 18 cm apart
    s = np.array([lx * .55, ly * .7, 1.0]); r = np.array([lx * .5 + (.09 if ch else -.09), ly * .45, 1.2])
    for nx in range(-5, 6):
        for ny in range(-5, 6):
            for nz in range(-3, 4):
                for sx in (0, 1):
                    for sy in (0, 1):
                        for sz in (0, 1):
                            ix = (1 - 2 * sx) * s[0] + 2 * nx * lx; iy = (1 - 2 * sy) * s[1] + 2 * ny * ly; iz = (1 - 2 * sz) * s[2] + 2 * nz * lz
                            d = np.linalg.norm(np.array([ix, iy, iz]) - r)
                            i = int(d / 343 * SR)
                            if i >= L: continue
                            o = abs(2 * nx - sx) + abs(2 * ny - sy) + abs(2 * nz - sz)
                            if o == 0: continue  # direct sound comes from the panner
                            h[i] += g ** o / max(d, 1) * (1 if o % 2 == 0 else -1) * rng.uniform(.8, 1.1)
    return signal.fftconvolve(h, signal.windows.hann(9) / 2.5)[:L]


def late(rt, dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for i, (fc, r) in enumerate(zip(BANDS, rt)):
        lo = fc / 1.41 if i else 20; hi = min(fc * 1.41, 23000) if i < 5 else 23000
        sos = signal.butter(2, [lo, hi], 'bandpass', fs=SR, output='sos')
        out += signal.sosfilt(sos, rng.normal(0, 1, n)) * np.exp(-t * 6.91 / r)
    return out


for name, (size, rt, g, wet) in ROOMS.items():
    rng = np.random.default_rng(sum(map(ord, name)))
    dur = min(7.5, max(rt) * 1.25)
    n = int(dur * SR); ch = []
    v = size[0] * size[1] * size[2]
    onset = .012 + 2 * (v ** (1 / 3)) / 343 * .4   # time until the field becomes diffuse
    for c in (0, 1):
        e = early(size, g, rng, c); l = late(rt, dur, rng)
        env = np.clip((np.arange(n) / SR - onset * .4) / onset, 0, 1) ** 1.5
        l = l * env
        h = np.zeros(n); h[:len(e)] += e / (np.abs(e).max() + 1e-9) * .9
        h += l / (np.abs(l).max() + 1e-9) * .75
        ch.append(h)
    x = np.stack(ch, 1)
    x[-2400:] *= np.linspace(1, 0, 2400)[:, None]
    # equal energy: the app applies wet gain itself
    x /= np.sqrt((x ** 2).sum(0).mean())
    x *= .9 / np.abs(x).max()
    p = f'{ROOT}/audio/wav/rir_{name}.wav'
    wavfile.write(p, SR, (x * 32767).astype('i2'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', p, '-c:a', 'aac', '-b:a', '160k', f'{OUT}/{name}.m4a'], check=True)
    print(name, round(dur, 1), 's')
json.dump({k: dict(wet=v[3]) for k, v in ROOMS.items()}, open(f'{OUT}/rooms.json', 'w'))
