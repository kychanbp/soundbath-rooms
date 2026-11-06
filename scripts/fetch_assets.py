"""Download CC0 textures, HDRIs and models from Poly Haven into data/."""
import json, os, urllib.request, concurrent.futures as cf
OUT = os.path.join(os.path.dirname(__file__), '..', 'data')
UA = {'User-Agent': 'soundbath-rooms-personal/0.1'}
TEX = """old_wood_floor wood_floor dark_wooden_planks hinoki_planks japanese_cedar_planks wood_planks brown_planks_05
black_painted_planks clay_plaster white_plaster_rough_01 grey_plaster white_rough_plaster plastered_wall_04 smooth_concrete_floor
concrete_wall_008 concrete_floor_02 rock_wall_10 rock_wall_13 tatami_mat wool_boucle velour_velvet rough_linen poly_wool_herringbone
terry_cloth fabric_pattern_05 quatrefoil_jacquard_fabric brown_leather bamboo_veneer""".split()
HDRI = """fouriesburg_mountain_lookout qwantani_noon qwantani_dusk_2 rainforest_trail ninomaru_teien autumn_forest_01 misty_pines""".split()
MODELS = """brass_candleholders brass_diya_lantern brass_pot_01 brass_vase_03 ceramic_vase_03 potted_plant_01 potted_plant_02 potted_plant_04
fern_02 throw_pillows_01 wooden_stool_01 chinese_tea_table wooden_lantern_01 wicker_basket_01 rock_moss_set_01 moss_01 wooden_bowl_01
tea_set_01 planter_pot_clay calathea_orbifolia_01 anthurium_botany_01 side_table_01""".split()

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
