"""Real Bali data: Copernicus GLO-30 elevation and Sentinel-2 true colour around Jatiluwih."""
import json, numpy as np, rasterio, os
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds, reproject, Resampling
from pyproj import Transformer
LON, LAT = 115.1350, -8.3700   # Jatiluwih
O = 'data/bali'
t = Transformer.from_crs('EPSG:4326', 'EPSG:32750', always_xy=True); cx, cy = t.transform(LON, LAT); print('site UTM', cx, cy)
R = 26000; S = 30
from rasterio.transform import from_origin
n = int(2 * R / S); dst = from_origin(cx - R, cy + R, S, S); Z = np.zeros((n, n), 'f4')
with rasterio.open('https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_S09_00_E115_00_DEM/Copernicus_DSM_COG_10_S09_00_E115_00_DEM.tif') as src:
    reproject(rasterio.band(src, 1), Z, dst_transform=dst, dst_crs='EPSG:32750', resampling=Resampling.cubic)
print('DEM', Z.shape, Z.min(), Z.max()); np.savez(f'{O}/dem.npz', Z=Z, x0=cx - R, y1=cy + R, s=S, cx=cx, cy=cy)
st = json.load(open(f'{O}/stac.json'))
pick = [f for f in st['features'] if f['id'] in ('S2A_50LKR_20260607_0_L2A', 'S2B_50LKR_20230619_0_L2A')]
Rs = 9000
for f in pick:
    u = f['assets']['visual']['href']; print(f['id'], u[-40:])
    with rasterio.open(u) as src:
        w = from_bounds(cx - Rs, cy - Rs, cx + Rs, cy + Rs, src.transform); a = src.read(window=w, boundless=True, fill_value=0); print(a.shape, src.crs, (a.sum(0) == 0).mean())
    np.save(f"{O}/tci_{f['id'][:3]}_{f['properties']['datetime'][:4]}.npy", a)
