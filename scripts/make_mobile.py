"""Make the lighter image set for phones under web/assets/m."""
import glob, os
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..')); A = f'{ROOT}/web/assets'
def fit(src, dst, lim, q=80):
    os.makedirs(os.path.dirname(dst), exist_ok=True); im = Image.open(src).convert('RGB'); s = lim / max(im.size)
    if s < 1: im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    im.save(dst, quality=q)
for f in glob.glob(f'{A}/tex/*.jpg'):
    fit(f, f'{A}/m/tex/{os.path.basename(f)}', 1024 if any(k in f for k in ('old_wood_floor', 'wood_floor', 'tatami', 'gong_', 'bronze_bowl')) else 512)
for f in glob.glob(f'{A}/rooms/*/lm.jpg') + glob.glob(f'{A}/rooms/*/sky.jpg'):
    r = f.split('/')[-2]; fit(f, f'{A}/m/rooms/{r}/{os.path.basename(f)}', 1536 if f.endswith('lm.jpg') else 2048, 84)
for f in glob.glob(f'{A}/teacher/*/*.jpg'):
    p = f.split('/'); fit(f, f'{A}/m/teacher/{p[-2]}/{p[-1]}', 1024 if 'head_c' in f else 512)
