"""Render every sample to WAV, encode to AAC, and write the sample manifest.
Usage: python scripts/render_audio.py [room ...]"""
import json, os, subprocess, sys, time
import numpy as np
from concurrent.futures import ProcessPoolExecutor
from scipy.io import wavfile
sys.path.insert(0, os.path.dirname(__file__))
from synth_lib import *

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
WAV = f'{ROOT}/audio/wav'; WEB = f'{ROOT}/web/assets/audio'


def job(a):
    room, name, fn, args, seed = a
    x = fn(*args, np.random.default_rng(seed))
    x = np.nan_to_num(np.asarray(x, 'f4')); x = fade(hp(x, 24).astype('f4'), .0015, .25)
    x = norm(x, .92)
    os.makedirs(f'{WAV}/{room}', exist_ok=True); os.makedirs(f'{WEB}/{room}', exist_ok=True)
    p = f'{WAV}/{room}/{name}.wav'
    wavfile.write(p, SR, (x * 32767).astype('i2'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', p, '-c:a', 'aac', '-b:a', '112k', f'{WEB}/{room}/{name}.m4a'], check=True)
    return room, name, round(len(x) / SR, 1)


def bowl_s(f, t60, lvl, dur, table_seed, rng):
    t = bowl_table(f, np.random.default_rng(table_seed))
    return strike(f, t, BOWL_A, t60, dur, rng, tc=.0008, level=lvl)


def bowl_r(f, t60, dur, table_seed, rng):
    t = bowl_table(f, np.random.default_rng(table_seed))
    return rub(f, t, BOWL_A, t60, dur, rng, hold=dur * .52, attack=dur * .14, rev=rng.uniform(.8, 1.25))


def crys_s(f, t60, dur, table_seed, rng):
    t = bowl_table(f, np.random.default_rng(table_seed), CRYSTAL_R, .006)
    return strike(f, t, CRYSTAL_A, t60, dur, rng, tc=.0026, level=.7)


def crys_r(f, t60, dur, table_seed, rng):
    t = bowl_table(f, np.random.default_rng(table_seed), CRYSTAL_R, .006)
    return rub(f, t, CRYSTAL_A, t60, dur, rng, hold=dur * .58, attack=dur * .17, rev=rng.uniform(.5, .8),
               harm=(1, .22, .09, .03), noise=.006)


def gong_h(f0, seed, lvl, dur, centre, rng, t60=34):
    return Gong(f0, seed, t60=t60, centre=centre).hit(dur, lvl, rng)


def gong_w(f0, seed, peak, dur, centre, rng):
    return gong_roll(Gong(f0, seed, centre=centre), dur, rng, peak)


def chimes(notes, dur, rng): return chime_phrase(notes, dur, rng)
def tingsha_(f, rng): return tingsha(f, rng)
def fork_(f, rng): return fork(f, rng)


def rin(f, t60, lvl, dur, seed, rng):
    t = bowl_table(f, np.random.default_rng(seed), RIN_R, .01)
    return strike(f, t, RIN_A, t60, dur, rng, tc=.00045, level=lvl)


def drips(jf, rng):
    jar = jar_ir(jf, np.random.default_rng(5))
    return norm(drip(rng, jar=jar))


def bamboo(rng): return bamboo_knock(rng)
def tanpura_(f, dur, rng): return tanpura(f, dur, rng)
def sweep(f, dur, up, rng): return monochord_sweep(f, dur, rng, up=up)
def fdrum(f, lvl, rng): return frame_drum(f, lvl, rng)
def didge(f, dur, rng): return didgeridoo(f, dur, rng)
def ocean(dur, rng): return ocean_drum(dur, rng)
def stick(dur, rng): return rainstick(dur, rng)
def loop_rain(d, rng): return rain_on_glass(d, rng)
def loop_stream(d, rng): return stream(d, rng)
def loop_tone(d, rng): return room_tone(d, rng)
def loop_wind(d, rng): return wind_outside(d, rng)
def step(k, rng): return footstep(k, rng)
def loop_cicada(d, rng): return cicadas(d, rng)


J = []
def add(room, name, fn, *args, seed=None):
    J.append((room, name, fn, args, seed if seed is not None else hash((room, name)) % 2**31 if False else sum(map(ord, room + name)) * 7 + 11))


# Himalayan: seven hammered bowls, large and low to small and bright
for i, (f, t60) in enumerate([(98, 52), (131, 46), (165, 42), (196, 36), (247, 31), (311, 26), (392, 22)]):
    for v, l in enumerate((.45, .8)):
        add('himalayan', f'b{i}_s{v}', bowl_s, f, t60, l, 54, 40 + i)
    add('himalayan', f'b{i}_r', bowl_r, f, t60, 46, 40 + i)
add('himalayan', 'tingsha', tingsha_, 2250.)

# Crystal: frosted quartz bowls in a C major scale, rubbed and tapped
for i, f in enumerate([130.8, 146.8, 164.8, 174.6, 196.0, 220.0, 246.9]):
    add('crystal', f'c{i}_r', crys_r, f, 62, 58, 70 + i)
    add('crystal', f'c{i}_s', crys_s, f, 64, 58, 70 + i)
add('crystal', 'fork', fork_, 528.)

# Gong: 40 inch wind gong, 32 inch tam-tam, 24 inch tuned gong
for name, f0, seed, ct in (('g40', 44., 3, None), ('g32', 62., 8, None), ('g24', 98., 13, 196.)):
    for v, l in enumerate((.18, .42)):
        add('gong', f'{name}_h{v}', gong_h, f0, seed, l, 30, ct)
    add('gong', f'{name}_w', gong_w, f0, seed, .5 if name == 'g40' else .4, 42, ct)

# Rain: chimes in four tunings, ocean drum, rainstick
SETS = dict(earth=[196, 233.1, 261.6, 293.7, 349.2], water=[220, 261.6, 293.7, 329.6, 392],
            air=[293.7, 349.2, 392, 440, 523.3], fire=[329.6, 392, 440, 493.9, 587.3])
for k, n in SETS.items():
    for v in range(3): add('rain', f'ch_{k}{v}', chimes, n, 14.)
for v in range(3): add('rain', f'ocean{v}', ocean, 15. + v * 2)
for v in range(2): add('rain', f'stick{v}', stick, 16.)
add('rain', 'rainloop', loop_rain, 37.)

# Rin: temple bowl set, water jar, bamboo
for i, (f, t60) in enumerate([(174, 30), (262, 24), (392, 19), (587, 14), (880, 10)]):
    for v, l in enumerate((.45, .85)):
        add('rin', f'r{i}_s{v}', rin, f, t60, l, 36, 90 + i)
for v in range(6): add('rin', f'drip{v}', drips, 310.)
add('rin', 'knock', bamboo)
add('rin', 'stream', loop_stream, 29.)

# Strings: monochord in C, tanpura in C
for v, up in enumerate((True, False, True)):
    add('strings', f'mono{v}', sweep, 65.41, 24., up)
for v, f in enumerate([98.0, 130.81, 130.81, 65.41]):
    for w in range(2): add('strings', f'tan{v}{w}', tanpura_, f, 9.)

# Cave: frame drum, didgeridoo, drips
for v in range(6): add('cave', f'd{v}', fdrum, 71., .35 + v * .1)
for v in range(3): add('cave', f'didge{v}', didge, 69.3, 26.)
for v in range(4): add('cave', f'drip{v}', drips, 190.)

# Shared
for k in ('wood', 'stone', 'tatami', 'concrete', 'rug'):
    for v in range(3): add('shared', f'step_{k}{v}', step, k)
add('shared', 'tone', loop_tone, 27.)
add('shared', 'wind', loop_wind, 31.)
add('shared', 'cicada', loop_cicada, 33.)

if __name__ == '__main__':
    want = set(sys.argv[1:])
    jobs = [j for j in J if not want or j[0] in want]
    print(len(jobs), 'samples'); t0 = time.time()
    with ProcessPoolExecutor(10) as ex:
        for r in ex.map(job, jobs): print(r, round(time.time() - t0), flush=True)
    man = {}
    for r, n, *_ in J: man.setdefault(r, []).append(n)
    json.dump(man, open(f'{WEB}/manifest.json', 'w'))
