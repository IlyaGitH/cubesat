var roi = ee.Geometry.Point([36.35, 52.67]).buffer(10000).bounds();
Map.centerObject(roi, 11);

function exportScene(start, end) {
  var image = ee.ImageCollection('LANDSAT/LC08/C02/T1_RT')
    .filterDate(start, end)
    .filterBounds(roi)
    .sort('CLOUD_COVER')
    .first();
  print('A L8 scene ' + start, image);

  var clear = image.select('QA_PIXEL').bitwiseAnd(31).eq(0);
  var refl = image.select(['B2', 'B3', 'B4', 'B5', 'B6', 'B7'])
    .multiply(0.00002).add(-0.1)
    .updateMask(clear);
  var out = refl.addBands([
    refl.normalizedDifference(['B5', 'B4']).rename('NDVI'),
    refl.normalizedDifference(['B6', 'B5']).rename('NDBI'),
    refl.normalizedDifference(['B5', 'B6']).rename('NDMI')
  ]).toFloat().unmask(-9999);

  Map.addLayer(refl.clip(roi), {bands: ['B4', 'B3', 'B2'], min: 0, max: 0.15}, start);
  Export.image.toDrive({
    image: out,
    description: 'orel_2025-' + start,
    folder: 'cubesat_scenes',
    scale: 30,
    region: roi,
    crs: 'EPSG:32637',
    maxPixels: 1e13
  });
}

exportScene('2025-05-01', '2025-05-31');
exportScene('2025-06-01', '2025-06-30');
exportScene('2025-07-01', '2025-08-31');
