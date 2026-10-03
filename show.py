import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio

from mask import read

scene = sys.argv[1]
b, _ = read(scene)
rgb = np.clip(np.dstack([b['SR_B4'], b['SR_B3'], b['SR_B2']]) / 0.3, 0, 1)
panels = [('RGB (B4, B3, B2)', rgb, None, 0), ('NDVI', b['NDVI'], 'RdYlGn', -1), ('NDMI', b['NDMI'], 'BrBG', -1)]

key = Path(scene).stem.split('-')[0]
if Path(f'masks/{key}.tif').exists():
    with rasterio.open(f'masks/{key}.tif') as m:
        panels.append(('маска полей', m.read(1), 'gray', 0))

fig, axes = plt.subplots(1, len(panels), figsize=(5 * len(panels), 5))
for ax, (title, img, cmap, vmin) in zip(axes, panels):
    ax.imshow(img, cmap=cmap, vmin=vmin, vmax=1)
    ax.set_title(title)
    ax.axis('off')
plt.tight_layout()
plt.savefig(f'{Path(scene).stem}.png', dpi=120)
plt.show()
