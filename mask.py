import sys
import warnings
from glob import glob

import numpy as np
import rasterio
from scipy import ndimage

# порядок каналов LANDSAT/LC08/C02/T1_RT
BANDS = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B9', 'B10', 'B11',
         'QA_PIXEL', 'QA_RADSAT', 'SAA', 'SZA', 'VAA', 'VZA']


def nd(a, b):
    return (a - b) / (a + b)


def read(path):
    with rasterio.open(path) as src:
        a = src.read().astype('float32')
        profile = src.profile
    a[a == 0] = np.nan
    b = dict(zip(BANDS, a))
    # ponytail: TOA-отражение без поправки на высоту Солнца (в индексах сокращается);
    # 2e-5 и -0.1 — REFLECTANCE_MULT/ADD_BAND_* из свойств снимка Collection 2
    for k in BANDS[:9]:
        b[k] = b[k] * 2e-5 - 0.1
    b['NDVI'] = nd(b['B5'], b['B4'])
    b['NDMI'] = nd(b['B5'], b['B6'])
    b['NDBI'] = nd(b['B6'], b['B5'])
    return b, profile


def scenes_of(key):
    return sorted(glob(f'scenes/{key}-*.tif'))


def field_mask(scenes, ndvi_max=0.5, ndvi_amp=0.25, min_px=20):
    ndvi = np.stack([s['NDVI'] for s in scenes])
    ndbi = np.stack([s['NDBI'] for s in scenes])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', RuntimeWarning)
        hi, lo, built = np.nanmax(ndvi, 0), np.nanmin(ndvi, 0), np.nanmin(ndbi, 0)
        if len(scenes) == 1:
            m = (hi > 0.4) & (built < 0)
        else:
            m = (hi > ndvi_max) & (hi - lo > ndvi_amp) & ~(built > 0)
    m = ndimage.binary_opening(m, np.ones((3, 3)))
    labels, _ = ndimage.label(m)
    keep = np.bincount(labels.ravel()) >= min_px
    keep[0] = False
    return keep[labels]


def build(key):
    paths = scenes_of(key)
    if not paths:
        sys.exit(f'нет снимков scenes/{key}-*.tif')
    scenes, profiles = zip(*map(read, paths))
    m = field_mask(scenes)
    profile = dict(profiles[0], count=1, dtype='uint8', nodata=None)
    with rasterio.open(f'masks/{key}.tif', 'w', **profile) as dst:
        dst.write(m.astype('uint8'), 1)
    print(f'{key}: {len(paths)} снимков, поля {m.mean():.1%} площади')


if __name__ == '__main__':
    for key in sys.argv[1:]:
        build(key)
