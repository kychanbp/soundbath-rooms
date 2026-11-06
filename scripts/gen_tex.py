"""Generate instrument textures that no CC0 library has: hammered bronze, gong faces, drum skin, brass, frosted quartz."""
import os, numpy as np
from PIL import Image
from scipy import ndimage as ni
OUT = os.path.join(os.path.dirname(__file__), '..', 'data', 'gen'); os.makedirs(OUT, exist_ok=True)
r = np.random.default_rng(4)

def noise(h, w, s, wrap=True):
    return ni.gaussian_filter(r.normal(0, 1, (h, w)), s, mode='wrap' if wrap else 'reflect')

def nz(a): return (a - a.mean()) / (a.std() + 1e-9)

def fbm(h, w, s0, oct=5, wrap=True):
    o = 0; g = 1; s = s0
    for i in range(oct):
        o = o + nz(noise(h, w, max(s, .6), wrap)) * g; s /= 2; g *= .55
    return nz(o)

def dents(h, w, n, size):
    """Hammer marks: each blow is a shallow round cup."""
    y = r.uniform(0, h, n); x = r.uniform(0, w, n)
    tree = ni.distance_transform_edt
    m = np.ones((h, w), bool); m[y.astype(int), x.astype(int)] = 0
    d = tree(m)
    return -np.clip(1 - (d / size) ** 2, 0, 1) * 0 + np.clip(d / size, 0, 1.2) ** 2

def normal(hgt, k):
    gy, gx = np.gradient(hgt)
    n = np.dstack([-gx * k, gy * k, np.ones_like(hgt)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * .5 + .5

def save(name, c, n, ro):
    Image.fromarray((np.clip(c, 0, 1) ** (1 / 2.2) * 255).astype('u1')).save(f'{OUT}/{name}_c.jpg', quality=93)
    Image.fromarray((n * 255).astype('u1')).save(f'{OUT}/{name}_n.jpg', quality=94)
    a = np.clip(ro, .04, 1); Image.fromarray((a * 255).astype('u1')).convert('L').convert('RGB').save(f'{OUT}/{name}_r.jpg', quality=93)

# bronze bowl: V runs from outer base to rim then to the inner base
H, W = 1024, 2048
v = np.linspace(0, 1, H)[:, None] * np.ones((H, W)); 
d = dents(H, W, 2600, 26)
pat = fbm(H, W, 40); fine = fbm(H, W, 3, 3)
rim = np.exp(-((v - .5) / .03) ** 2)                  # rim band polished by use
inner = np.clip((v - .5) / .03, 0, 1)                 # the inside is kept bright
base = np.exp(-(v / .12) ** 2)                        # dark soot under the base
worn = np.clip(.16 + .10 * pat + .7 * rim + .62 * inner + .05 * fine, 0, 1) * (1 - .5 * base)
dark = np.array([.20, .125, .07]); bright = np.array([.82, .58, .31])
c = dark[None, None] * (1 - worn[..., None]) + bright[None, None] * worn[..., None]
c *= (1 + .06 * fine[..., None])
for vv in (.455, .47):
    ring = np.exp(-((v - vv) / .0016) ** 2); c *= (1 - .7 * ring[..., None])
ro = .30 + .20 * (1 - worn) + .03 * fine
hgt = d * 2.0 * (1 - rim * .85) * (1 - inner * .6) + fine * .03
save('bronze_bowl', c, normal(hgt, 1.5), ro)

# gong faces: planar UV, centre at .5,.5
S = 2048
yy, xx = np.mgrid[0:S, 0:S]; R = np.hypot(xx - S / 2, yy - S / 2) / (S / 2); A = np.arctan2(yy - S / 2, xx - S / 2)
def gong(name, boss, band, base, polish, sat):
    d = dents(S, S, 5200, 24); f = fbm(S, S, 50, wrap=False); fine = fbm(S, S, 3, 3, wrap=False)
    lath = np.sin(R * 420 + .4 * f) * .5 + .5
    a = np.exp(-((R - band) / .13) ** 2); b = np.clip((boss - R) / .02, 0, 1)
    edge = np.clip((R - .90) / .02, 0, 1)
    w = np.clip(a * (.82 + .16 * lath) + b * .7 + .18 * (f * .5 + .4), 0, 1) * (1 - edge * .9)
    c = np.array(base)[None, None] * (1 - w[..., None]) + np.array(polish)[None, None] * w[..., None]
    c *= 1 + .18 * f[..., None] * (1 - w[..., None]); c *= 1 + .06 * fine[..., None]
    ro = .30 + .36 * (1 - w) + .06 * lath * a
    hgt = d * 2.2 * (1 - a * .92) + lath * .05 * a
    save(name, c, normal(hgt, 3.0), ro)
gong('gong_a', .17, .46, (.13, .085, .05), (.86, .55, .26), 1)
gong('gong_b', .10, .62, (.09, .065, .045), (.78, .60, .36), 1)
gong('gong_c', .28, .60, (.2, .12, .06), (.90, .68, .34), 1)

# rawhide skin: translucent tan with darker hide fibres and a stain where the beater lands
S = 1024; yy, xx = np.mgrid[0:S, 0:S]; R = np.hypot(xx - S / 2, yy - S / 2) / (S / 2)
f = fbm(S, S, 30, wrap=False); fi = fbm(S, S, 2, 3, wrap=False); veins = np.abs(fbm(S, S, 12, 3, wrap=False))
base = np.array([.70, .52, .33])[None, None] * (1 + .12 * f[..., None] + .05 * fi[..., None])
base *= 1 - .22 * np.clip(.5 - veins, 0, 1)[..., None] * .5
stain = np.exp(-((R - .28) / .2) ** 2) * (.5 + .3 * f); base *= 1 - .35 * stain[..., None]
base *= 1 - .4 * np.clip((R - .86) / .1, 0, 1)[..., None]
save('skin', base, normal(fi * .3 + f * .8, 1.2), .52 + .06 * f)

# plain brass with fine wear
S = 1024; f = fbm(S, S, 28); fi = fbm(S, S, 2, 3)
save('brass', np.array([.80, .56, .24])[None, None] * (1 + .12 * f[..., None]), normal(fi * .35, 1), .3 + .06 * f + .03 * fi)

# frosted quartz: V runs from outer base to rim to inner base
H, W = 512, 1024; v = np.linspace(0, 1, H)[:, None] * np.ones((H, W)); f = fbm(H, W, 18); fi = fbm(H, W, 1.2, 2)
c = np.array([.86, .86, .84])[None, None] * (1 + .03 * f[..., None])
ro = .52 + .06 * fi - .25 * np.exp(-((v - .5) / .03) ** 2)
save('quartz', c, normal(fi * .35, .8), ro)
def solid(name, col, rough, grain=.04, bump=.2, S=512):
    f = fbm(S, S, 20); fi = fbm(S, S, 1.5, 3)
    save(name, np.array(col)[None, None] * (1 + grain * f[..., None]), normal(fi * bump, 1), rough + .03 * fi)
solid('wax', (.86, .80, .66), .42, .03, .05)
solid('steel', (.72, .72, .70), .28, .03, .05)
solid('lacquer', (.055, .018, .014), .22, .04, .03)
solid('water', (.015, .02, .024), .05, .0, .0)
solid('sand', (.42, .36, .29), .85, .2, .8)
solid('wick', (.05, .04, .03), .8)
S = 1024; fi = fbm(S, S, 1.4, 3); fib = np.abs(fbm(S, S, 5, 2))
save('shoji', np.array([.93, .90, .83])[None, None] * (1 + .035 * fi[..., None] - .05 * np.clip(.4 - fib, 0, 1)[..., None]), normal(fi * .2, 1), .85 + .02 * fi)
print('ok')
