"""Cut each plant out of the model sheets into its own card."""
import json, numpy as np, os
from PIL import Image
from scipy import ndimage as ni
A = 'data/imp'; O = 'web/assets/land'; os.makedirs(O, exist_ok=True); meta = {**json.load(open(f'{A}/meta.json')), **json.load(open(f'{A}/meta2.json'))}; cards = {}
for name, tag, keep in (('island_tree_01', 'jtree', 1), ('island_tree_03', 'jsmall', 4), ('tree_small_02', 'itree', 1), ('pachira_aquatica_01', 'pachira', 1), ('shrub_01', 'shrubA', 3), ('shrub_03', 'shrubB', 3), ('fern_02', 'fern', 4), ('calathea_orbifolia_01', 'cal', 2), ('anthurium_botany_01', 'anth', 2), ('grass_medium_01', 'grass', 4)):
    im = Image.open(f'{A}/{name}_0.png').convert('RGBA'); a = np.asarray(im); al = a[..., 3] > 8; m = meta[name]; ppm = im.width / m['w']
    cols = ni.binary_dilation(al.any(0), iterations=(1 if name in ('fir_tree_01', 'pine_tree_01') else int(.012 * im.width))); lab, n = ni.label(cols); rows = []
    for k in range(1, n + 1):
        xs = np.where(lab == k)[0]; ys = np.where(al[:, xs[0]:xs[-1] + 1].any(1))[0]
        rows.append((xs[-1] - xs[0], xs[0], xs[-1] + 1, ys[0], ys[-1] + 1))
    rows = sorted(sorted(rows, reverse=True)[:keep], key=lambda r: r[1])
    for i, (_, x0, x1, y0, y1) in enumerate(rows):
        c = im.crop((x0, y0, x1, y1)); w, h = c.size; s = min(1, 1024 / max(w, h)); c2 = c.resize((max(8, round(w * s / 4) * 4), max(8, round(h * s / 4) * 4)), Image.LANCZOS)
        # bleed colour under clear pixels so that edges stay clean
        arr = np.asarray(c2).copy(); mask = arr[..., 3] > 16; idx = ni.distance_transform_edt(~mask, return_distances=False, return_indices=True); arr[..., :3] = arr[idx[0], idx[1], :3]
        c2 = Image.fromarray(arr, 'RGBA'); fn = f'{tag}{i}'; c2.save(f'{O}/{fn}.webp', quality=82, method=5); c2.save(f'{A}/{fn}.png')
        cards[fn] = dict(w=round(w / ppm, 3), h=round(h / ppm, 3))
json.dump(cards, open(f'{O}/cards.json', 'w')); print(cards)
