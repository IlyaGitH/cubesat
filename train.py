import sys
from glob import glob
from pathlib import Path

import numpy as np
import rasterio
from sklearn.metrics import confusion_matrix, jaccard_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from tensorflow import keras

from mask import read, scenes_of

FEATS = ['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7', 'NDVI', 'NDMI']


def load(scene, mask):
    b, profile = read(scene)
    X = np.stack([b[f] for f in FEATS], -1).reshape(-1, len(FEATS))
    with rasterio.open(mask) as m:
        y = m.read(1).reshape(-1)
    ok = np.isfinite(X).all(1)
    return X, y, ok, profile


def dataset(keys):
    Xs, ys = [], []
    for key in keys:
        for s in scenes_of(key):
            X, y, ok, _ = load(s, f'masks/{key}.tif')
            Xs.append(X[ok])
            ys.append(y[ok])
    return np.concatenate(Xs), np.concatenate(ys)


def report(name, y, p):
    pred = (p > 0.5).astype(int)
    print(f'{name}: precision {precision_score(y, pred):.3f}  recall {recall_score(y, pred):.3f}  '
          f'IoU {jaccard_score(y, pred):.3f}')
    print(confusion_matrix(y, pred))


def main(test_key):
    keys = [Path(p).stem for p in glob('masks/*.tif') if Path(p).stem != test_key]
    X, y = dataset(keys)
    print(f'обучение: {keys}, {len(y)} пикселей, поля {y.mean():.1%}')
    xTrain, xTest, yTrain, yTest = train_test_split(X, y, test_size=0.4, random_state=42)

    model = keras.Sequential([
        keras.Input(shape=(len(FEATS),)),
        keras.layers.Dense(32, activation='relu'),
        keras.layers.Dense(14, activation='relu'),
        keras.layers.Dense(2, activation='softmax'),
    ])
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    model.fit(xTrain, yTrain, epochs=5, batch_size=4096)
    report('отложенные 40 % пикселей', yTest, model.predict(xTest, batch_size=65536, verbose=0)[:, 1])
    Path('models').mkdir(exist_ok=True)
    model.save('models/field_nn.keras')

    Path('out').mkdir(exist_ok=True)
    for s in scenes_of(test_key):
        Xt, yt, ok, profile = load(s, f'masks/{test_key}.tif')
        p = model.predict(Xt[ok], batch_size=65536, verbose=0)[:, 1]
        report(Path(s).stem, yt[ok], p)
        prob = np.full(len(Xt), np.nan, dtype='float32')
        prob[ok] = p
        profile.update(count=1, dtype='float32', nodata=np.nan)
        with rasterio.open(f'out/{Path(s).stem}_fields.tif', 'w', **profile) as dst:
            dst.write(prob.reshape(profile['height'], profile['width']), 1)


if __name__ == '__main__':
    main(sys.argv[1])
