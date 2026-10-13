// Район: квадрат 20×20 км вокруг точки (Орловская область)
var roi = ee.Geometry.Point([36.35, 52.67]).buffer(10000).bounds();

// 1. Самый безоблачный снимок Landsat 8 за период
var image = ee.ImageCollection('LANDSAT/LC08/C02/T1_RT')
  .filterDate('2025-06-01', '2025-06-30')
  .filterBounds(roi)
  .sort('CLOUD_COVER')
  .first();
print('A L8 scene:', image);

// 2. Цветное изображение: каналы B4, B3, B2
var trueColour = {bands: ['B4', 'B3', 'B2'], min: 5000, max: 12000};
Map.centerObject(roi, 11);
Map.addLayer(image.clip(roi), trueColour, 'true-colour image');

// 3. Экспорт на Google Диск: имя = ключ района + дата начала периода
Export.image.toDrive({
  image: image.int16(),
  description: 'orel_2025-2025-06-01',
  scale: 30,
  region: roi,
  maxPixels: 1e13
});
