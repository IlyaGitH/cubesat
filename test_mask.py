import numpy as np

from mask import field_mask


def scene(ndvi, ndbi=-0.2):
    return {'NDVI': np.asarray(ndvi, 'float32'), 'NDBI': np.full(np.shape(ndvi), ndbi, 'float32')}


z = np.zeros((40, 40))
field = z.copy(); field[5:15, 5:15] = 1
forest = z.copy(); forest[25:35, 5:15] = 1
road = z.copy(); road[:, 30] = 1
speck = z.copy(); speck[25:28, 25:28] = 1

spring = scene(0.15 + 0.65 * forest)
summer = scene(0.15 + 0.65 * (field + forest + road + speck))
m = field_mask([spring, summer])
assert m[5:15, 5:15].all()
assert not m[25:35, 5:15].any()
assert not m[:, 30].any()
assert not m[25:28, 25:28].any()

assert not field_mask([scene(spring['NDVI'], 0.1), scene(summer['NDVI'], 0.1)]).any()

assert field_mask([summer])[25:35, 5:15].all()

nan = summer['NDVI'].copy(); nan[10, 10] = np.nan
assert field_mask([spring, scene(nan)])[5:15, 5:15].sum() == 99

print('ok')
