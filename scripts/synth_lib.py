"""Physical-model synthesis of sound bath instruments. All output is mono float at 48 kHz.
Every instrument is a sum of decaying resonant modes, with data from published measurements
where they exist (bowl mode ratios, membrane ratios, free bar ratios)."""
import numpy as np
from scipy import signal

SR = 48000
T60 = 6.91  # ln(1000): decay time constant = t60 / 6.91


def mallet(f, tc):
    """Spectrum of a soft strike with contact time tc (seconds). Flat below 1/(2 tc)."""
    return 1 / np.sqrt(1 + (2 * f * tc) ** 4)


def modal(f, a, t60, dur, ph=None, onset=None, rng=None, block=4096, rise=.0007):
    """Sum of decaying sines. onset is a rise time per mode, or None."""
    f = np.asarray(f, 'f8'); a = np.asarray(a, 'f8'); t60 = np.asarray(t60, 'f8')
    keep = (f > 18) & (f < SR * .46) & (a > 0)
    f, a, t60 = f[keep], a[keep], t60[keep]
    rng = rng or np.random.default_rng(0)
    ph = rng.uniform(0, 2 * np.pi, len(f)) if ph is None else np.asarray(ph)[keep]
    on = None if onset is None else np.asarray(onset, 'f8')[keep]
    tau = t60 / T60
    n = int(dur * SR); out = np.zeros(n, 'f4')
    for s in range(0, n, block):
        e = min(n, s + block)
        tt = np.arange(s, e, dtype='f8') / SR
        live = a * np.exp(-tt[0] / tau) > 3e-6
        if not live.any(): break
        env = np.exp(-tt[:, None] / tau[live])
        if on is not None:
            env = env * (1 - np.exp(-tt[:, None] / on[live]))
        if tt[0] < rise * 12:
            env = env * (1 - np.exp(-tt[:, None] / rise))
        w = np.sin(2 * np.pi * tt[:, None] * f[live] + ph[live])
        out[s:e] = (w * env * a[live]).sum(1)
    return out


def fade(x, t_in=.002, t_out=.05):
    n0 = int(t_in * SR); n1 = int(t_out * SR)
    x = x.copy()
    if n0: x[:n0] *= np.sin(np.linspace(0, np.pi / 2, n0)) ** 2
    if n1: x[-n1:] *= np.cos(np.linspace(0, np.pi / 2, n1)) ** 2
    return x


def norm(x, peak=.9):
    return x * (peak / (np.abs(x).max() + 1e-9))


def bp(x, f0, f1, order=2):
    sos = signal.butter(order, [f0, f1], 'bandpass', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def lp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, order=2):
    return signal.sosfilt(signal.butter(order, f, 'high', fs=SR, output='sos'), x)


def smooth_noise(n, rate, rng):
    """Slow random curve in the range -1..1, about `rate` changes per second."""
    k = max(4, int(n / SR * rate) + 3)
    return np.interp(np.arange(n), np.linspace(0, n, k), rng.uniform(-1, 1, k))


# ---- bowls -----------------------------------------------------------------
# Mode ratios of hand-hammered bowls: Inacio, Henrique, Antunes (2004, 2006), about 1 : 2.7 : 5.1 : 8 : 11.5 : 15.5.
BOWL_R = np.array([1, 2.71, 5.13, 8.05, 11.5, 15.4, 19.8, 24.7])
BOWL_A = np.array([1, .85, .62, .42, .28, .18, .11, .07])
CRYSTAL_R = np.array([1, 2.76, 5.33, 8.6])
CRYSTAL_A = np.array([1, .10, .035, .012])


def bowl_table(f1, rng, r=BOWL_R, spread=.012):
    k = len(r)
    rr = r * (1 + rng.normal(0, spread, k)); rr[0] = 1
    split = np.array([rng.uniform(.0015, .0065) * max(1, (i + 1) ** .3) for i in range(k)])
    return rr, split


def strike(f1, table, a, t60, dur, rng, tc=.004, level=1., phi=None):
    """One soft mallet strike. Each mode is a doublet. Strike angle sets the balance."""
    rr, split = table
    f = f1 * rr
    phi = rng.uniform(0, np.pi) if phi is None else phi
    F, A, D = [], [], []
    for i in range(len(f)):
        m = i + 2
        c, s = np.cos(m * phi), np.sin(m * phi)
        g = a[i] * mallet(f[i], tc) * level ** (1 + .12 * i)
        d = t60 * (f[i] / f1) ** -.82 * rng.uniform(.9, 1.1)
        F += [f[i] * (1 - split[i] / 2), f[i] * (1 + split[i] / 2)]
        A += [g * (.25 + .75 * abs(c)), g * (.25 + .75 * abs(s))]
        D += [d, d * rng.uniform(.8, 1.0)]
    x = modal(F, A, D, dur, ph=np.zeros(len(F)), rng=rng)
    # felt touch: a very short low thump plus a little noise
    n = int(.018 * SR); tk = rng.normal(0, 1, n) * np.exp(-np.arange(n) / (.0035 * SR))
    tk = bp(tk, 180, 1400) * .07 * level
    x[:n] += tk.astype('f4')
    return x


def rub(f1, table, a, t60, dur, rng, hold=None, rev=1.1, harm=(1, .30, .16, .08, .04), noise=.012, attack=4.5):
    """Rim friction drive. The stick-slip motion locks to the first mode and adds harmonics.
    The moving contact point makes a slow amplitude beat. After release the modes ring out."""
    n = int(dur * SR); t = np.arange(n) / SR
    hold = hold or dur * .5
    # pressure curve: slow rise, small human change, release
    pr = (1 - np.exp(-t / attack)) * (1 + .10 * smooth_noise(n, .5, rng))
    rel = np.where(t < hold, 1., np.exp(-(t - hold) / (t60 / T60)))
    env = pr * rel
    wob = 1 + 1.2e-4 * smooth_noise(n, .3, rng)
    phi = 2 * np.pi * np.cumsum(f1 * wob) / SR
    beat = 2 * rev * (1 + .05 * smooth_noise(n, .25, rng))
    bph = 2 * np.pi * np.cumsum(beat) / SR
    x = np.zeros(n, 'f4')
    drv = np.where(t < hold, 1., np.exp(-(t - hold) / .35))   # harmonics die fast after release
    for h, g in enumerate(harm, 1):
        depth = .34 + .08 * h
        am = 1 - depth * (.5 + .5 * np.cos(bph * (1 if h < 3 else 2) + rng.uniform(0, 6.28)))
        e = env * (1 if h == 1 else drv ** .8) * (env ** (.5 * (h - 1)))
        x += (g * np.cos(h * phi + rng.uniform(0, 6.28)) * am * e).astype('f4')
    # higher modes get a little energy from the friction harmonics
    rr, split = table
    for i in range(1, len(rr)):
        g = a[i] * .10 * (.6 + .4 * np.cos(bph * .5 + i))
        d = t60 * rr[i] ** -.82 / T60
        e = env ** 1.4 * np.where(t < hold, 1., np.exp(-(t - hold) / d))
        x += (g * np.sin(2 * np.pi * f1 * rr[i] * t + i) * e).astype('f4')
    # free doublet beat grows after release
    d1 = np.where(t < hold, 0., 1 - np.exp(-(t - hold) / 1.2))
    x += (.45 * env * d1 * np.sin(2 * np.pi * f1 * (1 + split[0]) * t)).astype('f4')
    # friction: resonant hiss near partials, then a thin broadband part, both pulsed by rotation
    wn = rng.normal(0, 1, n)
    ns = bp(wn, f1 * .985, f1 * 1.015) * 3.0 + bp(wn, f1 * rr[1] * .99, f1 * rr[1] * 1.01) * .9 + hp(lp(wn, 6000), 700) * .10
    pulse = .55 + .45 * np.cos(bph * .5)
    x += (ns * noise * pulse * np.where(t < hold, pr, 0)).astype('f4')
    return x


# ---- gongs -----------------------------------------------------------------
class Gong:
    """Dense mode set. High modes rise late because of the nonlinear energy cascade in a thin plate
    (Legge and Fletcher 1989). A soft strike stays low. A hard strike blooms upward."""
    def __init__(s, f0, seed, n=1100, t60=34, centre=None):
        rng = np.random.default_rng(seed)
        # plate modes have near constant density in frequency
        s.f = np.sort(np.r_[f0 * np.array([1, 1.52, 2.03, 2.71, 3.3, 4.1]) * (1 + rng.normal(0, .01, 6)),
                            np.cumsum(rng.exponential(8200 / n, n)) + f0 * 1.3])
        s.f0 = f0; s.t60 = t60 * (s.f / f0) ** -.42 * rng.uniform(.75, 1.25, len(s.f))
        s.ph = rng.uniform(0, 6.28, len(s.f)); s.w = rng.lognormal(0, .6, len(s.f)); s.seed = seed
        s.centre = centre  # tuned gongs have a clear pitch

    def hit(s, dur, level=.5, rng=None):
        rng = rng or np.random.default_rng(s.seed + 1)
        f = s.f
        bright = 420 + 6500 * level ** 1.25
        a = s.w * (f / s.f0) ** -.12 / np.sqrt(1 + (f / bright) ** 4)
        a[:6] *= 5 * (1.2 - .6 * level)
        if s.centre: a *= 1 + 7 * np.exp(-((f - s.centre) / (s.centre * .012)) ** 2)
        onset = .012 + (.28 + .75 * level) * (f / 1100) ** 1.15
        return modal(f, a, s.t60, dur, ph=s.ph + rng.uniform(0, .6, len(f)), onset=onset, rng=rng)


def fft_conv(x, h):
    return signal.fftconvolve(x, h)[:len(x)]


def gong_roll(g, dur, rng, peak=.5):
    """Continuous soft mallet tremolo that swells and falls. Two strike responses are mixed by force."""
    n = int(dur * SR); t = np.arange(n) / SR
    roll = dur * .55
    force = np.sin(np.clip(t / roll, 0, 1) * np.pi) ** 1.6 * peak
    ex0 = np.zeros(n); ex1 = np.zeros(n)
    ti = .2
    while ti < roll:
        i = int(ti * SR); fo = force[i] * rng.uniform(.75, 1.15)
        k = min(1, fo / max(peak, 1e-6))
        ex0[i] += fo * (1 - k * .75); ex1[i] += fo * k
        ti += rng.uniform(.13, .22)
    h0 = g.hit(min(dur, 34), .22, rng); h1 = g.hit(min(dur, 34), .62, rng)
    return (fft_conv(ex0, h0) + fft_conv(ex1, h1)).astype('f4')


# ---- bars and chimes ------------------------------------------------------
BAR_R = np.array([1, 2.756, 5.404, 8.933])  # free-free bar


def chime_tone(f, level, rng, dur=6., t60=6., tc=.0007):
    r = BAR_R * (1 + rng.normal(0, .004, 4)); r[0] = 1
    a = np.array([1, .55, .32, .14]) * mallet(f * r, tc)
    d = t60 * r ** -.9
    x = modal(f * r, a * level, d, dur, rng=rng)
    return x


def chime_phrase(notes, dur, rng, hits=16, tick=.03):
    """A hollow body tilted by hand. A clapper meets the rods at irregular times."""
    n = int(dur * SR); x = np.zeros(n, 'f4')
    t = rng.uniform(.0, .15); lvl = rng.uniform(.5, .9)
    span = dur * .55; k = 0
    while t < span and k < hits:
        pr = np.sin(t / span * np.pi) ** .7
        f = notes[rng.integers(len(notes))]
        l = lvl * (.25 + .75 * pr) * rng.uniform(.5, 1)
        tone = chime_tone(f, l, rng, dur=min(7., dur - t))
        i = int(t * SR); tone = tone[:n - i]; x[i:i + len(tone)] += tone
        c = rng.normal(0, 1, 200) * np.exp(-np.arange(200) / 25.)
        x[i:i + 200] += (bp(c, 2200, 7000) * tick * l).astype('f4')
        t += rng.exponential(.28) + .05; k += 1
    return x


def tingsha(f, rng, dur=14.):
    """Two small cymbals on one cord. Thick bronze, very strong doublets."""
    x = np.zeros(int(dur * SR), 'f4')
    for de in (1, 1.009):
        r = np.array([1, 2.13, 3.4, 4.9, 6.7]) * (1 + rng.normal(0, .01, 5))
        a = np.array([1, .8, .55, .3, .15])
        ff = np.r_[f * de * r, f * de * r * 1.0035]
        x += modal(ff, np.r_[a, a * .7], np.r_[12 * r ** -.6, 11 * r ** -.6], dur, rng=rng)
    n = 240; c = rng.normal(0, 1, n) * np.exp(-np.arange(n) / 30.)
    x[:n] += (hp(c, 3000) * .5).astype('f4')
    return x


def fork(f, rng, dur=16.):
    a = [1, .06, .012]
    return modal([f, f * 2, f * 6.2], a, [14, 7, 2.2], dur, rng=rng)


# ---- rin and water ---------------------------------------------------------
RIN_R = np.array([1, 2.68, 5.05, 7.9, 11.2])
RIN_A = np.array([1, .62, .34, .15, .06])


def drip(rng, f=None, jar=None):
    """A drop falls in water: rising bubble tone (Minnaert), then a ring from the vessel."""
    f = f or rng.uniform(700, 1700)
    n = int(.14 * SR); t = np.arange(n) / SR
    cf = f * (1 + 2.2 * t)
    x = np.sin(2 * np.pi * np.cumsum(cf) / SR) * np.exp(-t / .022) * (1 - np.exp(-t / .0008))
    out = np.zeros(int(3.5 * SR), 'f4'); out[:n] = x.astype('f4')
    if jar is not None: out = fft_conv(out, jar).astype('f4') + out * .35
    return out


def jar_ir(f0, rng):
    """Buried inverted jar of a suikinkutsu: narrow resonances with long ring."""
    r = np.array([1, 2.02, 3.1, 4.2, 5.45, 6.8, 8.1]) * (1 + rng.normal(0, .01, 7))
    return modal(f0 * r, [1, .9, .8, .6, .45, .3, .2], 2.2 * r ** -.45, 3.2, rng=rng)


def bamboo_knock(rng):
    r = np.array([1, 1.46, 2.4, 3.3])
    x = modal(720 * r, [1, .7, .4, .2], [.16, .1, .06, .035], .4, rng=rng)
    n = 300; c = rng.normal(0, 1, n) * np.exp(-np.arange(n) / 40.)
    x[:n] += (bp(c, 600, 4000) * .5).astype('f4')
    return x


# ---- strings ---------------------------------------------------------------
def plucked(f, dur, rng, pos=.17, t60=14., B=2e-5, n=26, soft=2200, body=None):
    """Stiff string (Fletcher). Each partial loses energy to air and to the bridge."""
    h = np.arange(1, n + 1)
    fn = f * h * np.sqrt(1 + B * h ** 2)
    a = np.abs(np.sin(h * np.pi * pos)) / h ** .85 / np.sqrt(1 + (fn / soft) ** 2)
    d = t60 / (1 + .018 * h ** 1.5)
    if body is not None: a = a * body(fn)
    return modal(fn, a, d, dur, rng=rng)


def monochord_sweep(f0, dur, rng, strings=26, up=True):
    """Finger strokes across unison strings. Each string has its own small tuning error."""
    n = int(dur * SR); x = np.zeros(n, 'f4')
    body = lambda ff: 1 + 1.2 * np.exp(-((ff - 196) / 60) ** 2) + .7 * np.exp(-((ff - 420) / 120) ** 2)
    span = dur * .32
    for i in range(strings):
        t = (i / strings if up else 1 - i / strings) * span + rng.uniform(-.03, .03)
        cents = rng.normal(0, 1.1)
        mult = 2 if i % 7 == 3 else 1
        l = np.sin((i + .5) / strings * np.pi) ** .5 * rng.uniform(.6, 1)
        y = plucked(f0 * mult * 2 ** (cents / 1200), dur - max(t, 0) - .01, rng, pos=rng.uniform(.14, .23), t60=dur * 1.1, n=18, soft=1300, body=body)
        i0 = int(max(t, 0) * SR); y = y[:n - i0]; x[i0:i0 + len(y)] += y * l
    return x


def tanpura(f, dur, rng, t60=13.):
    """Curved bridge (jawari). The string grazes the bridge, so upper partials bloom one after another."""
    h = np.arange(1, 37); fn = f * h
    n = int(dur * SR); t = (np.arange(0, n, 64) / SR)[:, None]
    tau = (t60 / T60) / (1 + .012 * h)
    base = 1 / h ** .75
    t0 = .12 + .23 * h ** .75
    w = .22 + .09 * h ** .5
    gain = (.35 + 1.8 * np.exp(-((t - t0) / w) ** 2) * (1 - np.exp(-h / 3.))) * np.exp(-t / tau) * base
    gain = gain * (1 + .1 * np.sin(2 * np.pi * rng.uniform(.8, 2.2, 36) * t + rng.uniform(0, 6, 36)))
    tt = np.arange(n) / SR
    x = np.zeros(n, 'f4')
    det = rng.normal(0, .6, 36)
    for i in range(36):
        g = np.interp(tt, t[:, 0], gain[:, i])
        x += (g * np.sin(2 * np.pi * (fn[i] + det[i] * .05) * tt + i * 2.1)).astype('f4')
    # pluck
    k = 400; x[:k] += (lp(rng.normal(0, 1, k), 2400) * np.exp(-np.arange(k) / 60.) * .2).astype('f4')
    return x


# ---- drum and didgeridoo --------------------------------------------------
DRUM_R = np.array([1, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50])  # ideal circular membrane


def frame_drum(f0, level, rng, dur=2.4):
    r = DRUM_R * (1 + rng.normal(0, .006, 8)); r[0] = 1
    pos = rng.uniform(.2, .6)  # beater nearer the rim wakes more upper modes
    a = np.array([1, .6 * pos * 2, .6, .45 * pos * 2, .4, .3, .22, .16]) * level ** np.linspace(.9, 1.5, 8)
    t60 = np.array([1.0, .75, .55, .5, .4, .35, .3, .26]) * rng.uniform(.9, 1.1)
    n = int(dur * SR); t = np.arange(n) / SR
    x = np.zeros(n, 'f4')
    glide = 1 + .035 * level * np.exp(-t / .045)  # tension falls after impact
    for i in range(8):
        ph = 2 * np.pi * np.cumsum(f0 * r[i] * glide) / SR
        x += (a[i] * np.exp(-t * T60 / t60[i]) * np.sin(ph)).astype('f4')
    k = 480; x[:k] += (lp(rng.normal(0, 1, k), 2600) * np.exp(-np.arange(k) / 70.) * .9 * level).astype('f4')
    hoop = modal([612, 1040], [.012, .007], [.09, .06], dur, rng=rng) * level
    return x + hoop


def didgeridoo(f0, dur, rng):
    """Lip buzz into a long bore (odd modes), shaped by the player's vocal tract (Tarnopolsky et al. 2005)."""
    n = int(dur * SR); t = np.arange(n) / SR
    # breath: a pulse every few seconds, with quick nose sniffs
    beat = 1 + .25 * np.sin(2 * np.pi * t * 1.45) ** 8
    press = (1 - np.exp(-t / .5)) * (.75 + .25 * smooth_noise(n, 1.2, rng)) * beat
    f = f0 * (1 + .006 * smooth_noise(n, 2, rng) + .004 * np.sin(2 * np.pi * 4.7 * t))
    ph = np.cumsum(f) / SR
    p = ph % 1
    src = np.where(p < .35, np.sin(np.pi * p / .35) ** 2, 0.) - .22  # lip opening pulse
    src += rng.normal(0, .018, n)
    # bore: closed at the lips, open at the bell -> odd modes, with widening cone slight stretch
    T = int(SR / (2 * f0))
    bore = signal.lfilter([1], np.r_[1, np.zeros(T - 1), .94], src)
    # two moving vocal tract formants
    out = np.zeros(n)
    block = 480
    z1 = z2 = None
    wow = np.sin(2 * np.pi * np.cumsum(.31 + .22 * (smooth_noise(n, .6, rng) + 1)) / SR)
    for s in range(0, n, block):
        e = min(n, s + block); w = wow[s]
        f1 = 1300 + 620 * w; f2 = 2500 - 500 * w
        b1, a1 = signal.iirpeak(f1, 7, SR); b2, a2 = signal.iirpeak(f2, 9, SR)
        if z1 is None: z1 = signal.lfilter_zi(b1, a1) * 0; z2 = signal.lfilter_zi(b2, a2) * 0
        y1, z1 = signal.lfilter(b1, a1, bore[s:e], zi=z1)
        y2, z2 = signal.lfilter(b2, a2, bore[s:e], zi=z2)
        out[s:e] = y1 * 1.5 + y2 * .8
    x = (lp(bore, 900) * .8 + out * 2.6) * press
    return x.astype('f4')


# ---- noise makers and ambience ---------------------------------------------
def ocean_drum(dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    tilt = np.sin(np.clip(t / dur, 0, 1) * np.pi) ** 1.5
    rate = 2600 * tilt ** 1.6 + 2
    imp = (rng.random(n) < rate / SR) * rng.uniform(.2, 1, n)
    grain = rng.normal(0, 1, 90) * np.exp(-np.arange(90) / 16.)
    bead = signal.fftconvolve(imp, grain)[:n]
    bed = hp(lp(rng.normal(0, 1, n), 7000), 1300)
    x = lp(hp(bead, 1600), 6500, 4) * .55 + lp(bed, 5200) * .05 * tilt ** 1.2
    thump = lp(imp, 180, 2) * 3.5
    return (x + thump * .25).astype('f4')


def rainstick(dur, rng):
    n = int(dur * SR); t = np.arange(n) / SR
    rate = 900 * np.exp(-t / (dur * .34)) * (1 - np.exp(-t / .25))
    out = np.zeros(n)
    for f0, f1, g in ((1100, 2300, .9), (2300, 5200, 1.), (5200, 9000, .5)):
        imp = (rng.random(n) < rate / 3 / SR) * rng.uniform(.15, 1, n)
        out += bp(imp, f0, f1) * g * 7
    body = bp(out, 320, 900) * .8
    return (out + body).astype('f4')


def loop_xf(x, xf):
    """Make a seamless loop by crossfading the tail into the head."""
    k = int(xf * SR); w = np.sin(np.linspace(0, np.pi / 2, k)) ** 2
    y = x[:-k].copy(); y[:k] = x[:k] * w + x[-k:] * (1 - w) ** 1
    return y


def rain_on_glass(dur, rng):
    n = int((dur + 3) * SR)
    wn = rng.normal(0, 1, n)
    x = lp(hp(wn, 300), 5200) * .16 + lp(wn, 280, 1) * .25
    swell = 1 + .2 * smooth_noise(n, .12, rng)
    imp = (rng.random(n) < 420 / SR) * rng.uniform(.05, 1, n) ** 2
    tick = bp(imp, 1800, 6500) * 5 + bp(imp, 500, 1400) * 2.5
    return loop_xf((x * swell + tick).astype('f4'), 3)


def stream(dur, rng):
    n = int((dur + 3) * SR); wn = rng.normal(0, 1, n)
    x = bp(wn, 400, 1100) * (1 + .5 * smooth_noise(n, 3, rng)) * .4 + bp(wn, 1300, 3200) * (1 + .6 * smooth_noise(n, 7, rng)) * .22
    return loop_xf(x.astype('f4'), 3)


def room_tone(dur, rng):
    n = int((dur + 3) * SR); wn = rng.normal(0, 1, n)
    x = lp(wn, 120, 2) + hp(lp(wn, 900, 1), 100) * .05
    return loop_xf(x.astype('f4'), 3)


def wind_outside(dur, rng):
    n = int((dur + 3) * SR); wn = rng.normal(0, 1, n)
    out = np.zeros(n)
    for f0, f1, r in ((90, 300, .1), (250, 700, .17), (600, 1600, .24)):
        out += bp(wn, f0, f1) * (.6 + .4 * smooth_noise(n, r, rng))
    return loop_xf(out.astype('f4'), 3)


def footstep(kind, rng):
    """Heel then sole, on a floor of the given type, in soft socks or bare feet."""
    d = dict(wood=(95, 240, .1, .018), stone=(180, 900, .05, .010), tatami=(120, 500, .035, .006),
             concrete=(120, 620, .07, .010), rug=(70, 300, .02, .004))[kind]
    n = int(.34 * SR); x = np.zeros(n, 'f4'); t = np.arange(n) / SR
    for t0, g in ((0, 1), (rng.uniform(.06, .1), .55)):
        i = int(t0 * SR); m = n - i; tt = t[:m]
        y = np.sin(2 * np.pi * d[0] * rng.uniform(.9, 1.1) * tt) * np.exp(-tt / .022) * 1.0
        z = modal([d[1], d[1] * 1.7], [.3, .15], [.09, .05], m / SR, rng=rng)[:m]; y[:len(z)] += z
        x[i:] += (y * g).astype('f4')
    sc = hp(lp(rng.normal(0, 1, n), 5000), 800) * np.exp(-t / .05) * d[2]
    return (x * .6 + sc.astype('f4')).astype('f4')


def cicadas(dur, rng):
    """Tropical insects: a high band of noise that pulses, slowly rising and falling."""
    n = int((dur + 3) * SR); t = np.arange(n) / SR; wn = rng.normal(0, 1, n)
    a = bp(wn, 4300, 5600) * (.55 + .45 * np.sign(np.sin(2 * np.pi * 31 * t))) * (.6 + .4 * smooth_noise(n, .18, rng))
    b = bp(wn, 6800, 8200) * (.5 + .5 * np.sin(2 * np.pi * 47 * t)) ** 2 * (.5 + .5 * smooth_noise(n, .1, rng))
    return loop_xf((a + b * .7).astype('f4'), 3)
