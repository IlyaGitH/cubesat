var region = 'rostov_2025';
var roi = ee.Geometry.Point([40.2, 47.3]).buffer(10000).bounds();
var crs = 'EPSG:32637';
var months = [['2025-05-01', '2025-05-31'], ['2025-06-01', '2025-06-30'], ['2025-07-01', '2025-08-31']];

function scene(start, end) {
  var img = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filterBounds(roi)
    .filterDate(start, end)
    .sort('CLOUD_COVER')
    .first();
  var clear = img.select('QA_PIXEL').bitwiseAnd(31).eq(0);
  var sr = img.select(['SR_B2', 'SR_B3', 'SR_B4', 'SR_B5', 'SR_B6', 'SR_B7'])
    .multiply(0.0000275).add(-0.2)
    .updateMask(clear);
  return sr.addBands([
    sr.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI'),
    sr.normalizedDifference(['SR_B5', 'SR_B6']).rename('NDMI'),
    sr.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')
  ]).toFloat().unmask(-9999);
}

Map.centerObject(roi, 11);
months.forEach(function (m) {
  var img = scene(m[0], m[1]);
  Map.addLayer(img.updateMask(img.select('SR_B4').neq(-9999)), {bands: ['SR_B4', 'SR_B3', 'SR_B2'], min: 0, max: 0.3}, m[0]);
  Export.image.toDrive({
    image: img,
    description: region + '-' + m[0],
    folder: 'cubesat_scenes',
    region: roi,
    scale: 30,
    crs: crs,
    maxPixels: 1e9
  });
});
