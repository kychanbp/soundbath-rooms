"""Download Rocketbox people (MIT licence), shrink textures, and write them where the app loads them."""
import json, os, subprocess, urllib.request, sys
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BASE = 'https://github.com/microsoft/Microsoft-Rocketbox/raw/master/'
tree = json.load(open(sys.argv[1]))['tree']
WHO = [('Female_Adult_09',), ('Female_Adult_14',), ('Male_Adult_03',), ('Male_Adult_11',), ('Male_Adult_05',), ('Female_Adult_13',), ('Male_Adult_09',)]
def get(a):
    url, p = a
    if os.path.exists(p) and os.path.getsize(p) > 1000: return
    urllib.request.urlretrieve(url.replace(' ', '%20'), p)
for (w,) in WHO:
    d = f'{ROOT}/data/rb/{w}'; os.makedirs(d, exist_ok=True); o = f'{ROOT}/web/assets/teacher/{w}'; os.makedirs(o, exist_ok=True)
    fs = [x['path'] for x in tree if f'/Adults/{w}/' in x['path'] and (x['path'].endswith('_facial.fbx') or ('/Textures/' in x['path'] and '/Source/' not in x['path'] and x['path'].endswith('.tga')))]
    with ThreadPoolExecutor(6) as ex: list(ex.map(get, [(BASE + f, f'{d}/{os.path.basename(f)}') for f in fs]))
    n = {f.rsplit('_', 2)[-2] + '_' + f.rsplit('_', 2)[-1][:-4]: f'{d}/{os.path.basename(f)}' for f in fs if f.endswith('.tga')}
    print(w, sorted(n))
    for k, sz in (('body', 1536), ('head', 2048)):
        Image.open(n[f'{k}_color']).convert('RGB').resize((sz, sz), Image.LANCZOS).save(f'{o}/{k}_c.jpg', quality=90)
        Image.open(n[f'{k}_normal']).convert('RGB').resize((sz, sz), Image.LANCZOS).save(f'{o}/{k}_n.jpg', quality=90)
        s = np.asarray(Image.open(n[f'{k}_specular']).convert('L').resize((sz, sz), Image.LANCZOS), 'f4') / 255
        r = (np.clip(.82 - .55 * s, .25, .95) * 255).astype('u1'); Image.fromarray(np.dstack([r, r, r * 0])).save(f'{o}/{k}_r.jpg', quality=90)
    if 'opacity_color' in n: Image.open(n['opacity_color']).resize((1024, 1024), Image.LANCZOS).save(f'{o}/op.png', optimize=True)
