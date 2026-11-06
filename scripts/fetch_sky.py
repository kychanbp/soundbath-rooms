"""Download CC0 textures, HDRIs and models from Poly Haven into data/."""
import json, os, urllib.request, concurrent.futures as cf
OUT = os.path.join(os.path.dirname(__file__), '..', 'data')
UA = {'User-Agent': 'soundbath-rooms-personal/0.1'}
TEX = """""".split()
HDRI = """overcast_soil_puresky farmland_overcast""".split()
MODELS = """""".split()

def get(url, path):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as r, open(path + '.tmp', 'wb') as f: f.write(r.read())
    os.rename(path + '.tmp', path)

def info(a):
    return json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.polyhaven.com/files/{a}', headers=UA), timeout=30))

def tex(a):
    d = info(a); got = []
    for key, fn in (('Diffuse', 'c'), ('nor_gl', 'n'), ('Rough', 'r'), ('AO', 'a')):
        if key not in d: continue
        e = d[key].get('2k', {}); j = e.get('jpg') or e.get('png')
        if j: get(j['url'], f"{OUT}/tex/{a}_{fn}.jpg"); got.append(fn)
    return a, got

def hdri(a):
    d = info(a); j = d['hdri']['2k']['hdr']; get(j['url'], f'{OUT}/hdri/{a}.hdr')
    j4 = d['hdri']['4k']['hdr']; get(j4['url'], f'{OUT}/hdri/{a}_4k.hdr')
    return a, 'ok'

def model(a):
    d = info(a); e = d['gltf']['1k']['gltf']
    get(e['url'], f'{OUT}/models/{a}/{a}.gltf')
    for rel, v in e.get('include', {}).items(): get(v['url'], f'{OUT}/models/{a}/{rel}')
    return a, 'ok'

with cf.ThreadPoolExecutor(8) as ex:
    fs = [ex.submit(tex, a) for a in TEX] + [ex.submit(hdri, a) for a in HDRI] + [ex.submit(model, a) for a in MODELS]
    for f in cf.as_completed(fs):
        try: print(f.result(), flush=True)
        except Exception as e: print('FAIL', repr(e), flush=True)
